"""Joint optimisation runs through the local API: start, observe, cancel, replay and summarise.

The functions here hold the logic behind the `/api/joint-runs` and `/api/runs/{run_id}/events` routes, so that
they can be used (and tested) without an HTTP server. Observation never changes a run: the events come from a
`ProgressSink` that the solver only writes to, and the summary is read from the saved artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib
from typing import Any

from pydantic import BaseModel, Field

from .app_paths import bundled_joint_catalog_path, bundled_scenarios_dir
from .app_storage import AppStorage
from .job_manager import LocalJobManager
from .joint_inputs import run_real_subset
from .joint_progress import EVENTS_FILE, ProgressSink, read_events
from .joint_strategy.resources import CancelToken, ExecutionBudget

JOINT_SCENARIO_SCHEMA = "joint-real-subset-v1"
_SAFE_SCENARIO_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_FIRST_SOLUTION = re.compile(r"first_solution_(\d+)s")
RUNNING, COMPLETED, FAILED, CANCELLED = "running", "completed", "failed", "cancelled"


class JointRunRequest(BaseModel):
    scenario: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    warm_start: str = Field("auto", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")  # "auto", "none" or a run id
    threads: int = Field(0, ge=0, le=512)
    memory_mb: int | None = Field(None, ge=1)
    parallel_day_checks: bool = True


def list_scenarios(scenarios_dir: Path | None = None) -> list[dict[str, Any]]:
    """The bundled scenario files that the joint engine can run."""
    rows = []
    for path in sorted((scenarios_dir or bundled_scenarios_dir()).glob("*.toml")):
        try:
            content = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if content.get("schema_version") != JOINT_SCENARIO_SCHEMA or not _SAFE_SCENARIO_ID.fullmatch(path.stem):
            continue
        scenario = content.get("scenario") if isinstance(content.get("scenario"), dict) else {}
        rows.append({"id": path.stem, "name": scenario.get("id", path.stem), "description": scenario.get("description", ""),
                     "schema_version": JOINT_SCENARIO_SCHEMA})
    return rows


def scenario_path(scenario_id: str, scenarios_dir: Path | None = None) -> Path:
    """The file of a bundled joint scenario; only ids from `list_scenarios` are accepted."""
    if not _SAFE_SCENARIO_ID.fullmatch(scenario_id):
        raise ValueError("Scenarie-id har ogiltigt format.")
    directory = scenarios_dir or bundled_scenarios_dir()
    if scenario_id not in {row["id"] for row in list_scenarios(directory)}:
        raise FileNotFoundError("Scenariot finns inte bland de inbyggda gemensamma scenarierna.")
    return directory / f"{scenario_id}.toml"


def start_joint_run(
    jobs: LocalJobManager, storage: AppStorage, request: JointRunRequest,
    scenarios_dir: Path | None = None, catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Queue a joint run as a background job with its own cancel token and progress sink."""
    config = scenario_path(request.scenario, scenarios_dir)
    catalog = catalog_path or bundled_joint_catalog_path()
    cancel, progress = CancelToken(), ProgressSink()
    budget = ExecutionBudget(request.threads, request.memory_mb, request.parallel_day_checks)

    def action() -> dict[str, Any]:
        try:
            run = run_real_subset(config, storage.processed_dir, catalog, storage.runs_dir, warm_start=request.warm_start,
                                  budget=budget, cancel=cancel, progress=progress)
        except Exception as error:
            if not progress.has("finished"):
                progress.emit("finished", outcome="failed", cost_ore=None, bound_ore=None, cancelled=cancel.cancelled,
                              error=f"{type(error).__name__}: {error}")
            raise
        finally:
            progress.close()
        finished = [event for event in progress.events() if event["type"] == "finished"]
        return {"kind": "joint_run", "run_id": run["run_id"], "validation": run["validation"],
                "cancelled": bool(finished[-1]["cancelled"]) if finished else cancel.cancelled}

    job = jobs.start(action, cancel=cancel, progress=progress)
    return {**job, "run_id": None}


def job_events(jobs: LocalJobManager, job_id: str, after: int = 0) -> dict[str, Any]:
    """The events of a running or finished joint job after sequence number `after`."""
    job, _, progress = jobs.handle(job_id)
    if progress is None:
        raise ValueError("Jobbet är inte en gemensam optimeringskörning.")
    status = job["status"]
    result = job.get("result") or {}
    state = RUNNING if status in ("queued", "running") else FAILED if status == "failed" else (
        CANCELLED if result.get("cancelled") else COMPLETED)
    payload: dict[str, Any] = {"status": state, "events": progress.events(after), "last_seq": progress.last_seq,
                               "run_id": result.get("run_id") or progress.run_id}
    if state == FAILED:
        payload["error"] = job.get("error")
    return payload


def cancel_job(jobs: LocalJobManager, job_id: str) -> dict[str, Any]:
    """Ask a running joint job to stop; the best verified solution found so far is saved, if there is one."""
    requested = jobs.cancel(job_id)
    return {"job_id": job_id, "cancel_requested": requested, "status": jobs.public(job_id)["status"]}


def run_events(storage: AppStorage, run_id: str) -> dict[str, Any]:
    """The whole saved event log of a finished run, for replay."""
    path = storage.run_directory(run_id) / EVENTS_FILE
    if not path.is_file():
        raise FileNotFoundError("Körningen har ingen sparad händelselogg.")
    events = read_events(path)
    return {"run_id": run_id, "events": events, "last_seq": events[-1]["seq"] if events else 0}


def run_summary(storage: AppStorage, run_id: str) -> dict[str, Any]:
    """Cost, bound, gap, changes and the three verdicts of a saved run, read from its artifacts (nothing is re-run)."""
    directory = storage.run_directory(run_id)
    result = _read_json(directory / "joint_result.json")
    if result is None:
        raise FileNotFoundError("Körningen har inget sparat gemensamt resultat.")
    solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
    coverage = result.get("coverage") if isinstance(result.get("coverage"), dict) else {}
    cost, bound = solver.get("objective_value_ore"), solver.get("best_objective_bound_ore")
    validation = _read_json(directory / "joint_validation.json")
    verdict = validation.get("summary") if isinstance(validation, dict) and isinstance(validation.get("summary"), dict) else {}
    decision = _read_json(directory / "joint_warm_start.json") or {}
    first, basis, source = _first_solution(decision, solver, directory)
    events_path = directory / EVENTS_FILE
    cancelled = any(event.get("type") == "finished" and event.get("cancelled") for event in read_events(events_path)) \
        if events_path.is_file() else str(solver.get("raw_status", "")).endswith("_cancelled")
    technical = verdict.get("technical_validation", "not_evaluated")
    return {
        "run_id": run_id,
        "problem_id": result.get("problem_id"),
        "solver_outcome": solver.get("outcome"),
        # A run without a placement has nothing to validate wrongly, so its technical verdict can read `pass`;
        # only a complete placement that the independent validation accepts counts as a verified solution.
        "has_verified_solution": bool(solver.get("outcome") in ("optimal", "feasible_not_proven")
                                      and coverage.get("technical_placement_complete") and technical == "pass"),
        "cost_is_proven_optimum": solver.get("outcome") == "optimal",
        "cost_ore": cost,
        "lower_bound_ore": bound,
        "gap_ore": cost - bound if isinstance(cost, int) and isinstance(bound, int) else None,
        "gap_relative": solver.get("relative_gap"),
        "changed_exams": result.get("changed_exam_demands"),
        "exams_total": coverage.get("exam_demands_total"),
        "technical_placement_complete": coverage.get("technical_placement_complete"),
        "staff_pool_size": result.get("staff_pool_size"),
        "wall_time_seconds": solver.get("wall_time_seconds"),
        "first_solution_seconds": first,
        "first_solution_basis": basis,
        "first_solution_source": source,
        "cancelled": cancelled,
        "warm_start_decision": decision.get("decision", "not_recorded"),
        # The three verdicts are kept apart; a missing validation is never a pass.
        "verdicts": {
            "technical_validation": technical,
            "business_verification": verdict.get("business_verification", "not_evaluated"),
            "provenance": verdict.get("provenance", "not_evaluated"),
            "technically_validated": bool(verdict.get("technically_validated", False)),
            "source": "joint_validation.json" if verdict else "not_available",
        },
    }


def _first_solution(decision: dict[str, Any], solver: dict[str, Any], directory: Path) -> tuple[float | None, str | None, str | None]:
    """Time to the first complete verified solution: from the saved re-check, the solver status, or the event log."""
    recheck = decision.get("recheck") if isinstance(decision.get("recheck"), dict) else {}
    if recheck.get("first_solution_seconds") is not None:
        return recheck["first_solution_seconds"], "solver_start", recheck.get("first_solution_source")
    match = _FIRST_SOLUTION.search(str(solver.get("raw_status", "")))
    if match:
        return float(match.group(1)), "solver_start", None
    path = directory / EVENTS_FILE
    for event in read_events(path) if path.is_file() else ():
        if event.get("type") == "incumbent":
            return event.get("t"), "run_start", event.get("source")
    return None, None, None


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None
