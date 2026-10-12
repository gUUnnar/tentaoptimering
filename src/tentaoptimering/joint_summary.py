"""The summary of a saved joint run, read from its artifacts (nothing is re-run)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .app_storage import AppStorage
from .joint_progress import EVENTS_FILE, read_events
from .joint_scenarios import scenario_id_for_problem

_FIRST_SOLUTION = re.compile(r"first_solution_(\d+)s")
_RUN_ID = re.compile(r"^(\d{8}T\d{6})Z-(.+)$")


def created_at(run_id: str) -> str | None:
    """The start time of a run in UTC (ISO 8601), from its id; None if the id has no time stamp."""
    match = _RUN_ID.match(run_id)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def changed_parameter_count(directory: Path) -> int:
    """How many frozen parameters of the run differ from the catalog default."""
    items = (read_json(directory / "joint_input.json") or {}).get("parameters", ())
    return sum(1 for item in items if isinstance(item, dict) and item.get("changed_from_default"))


def run_summary(storage: AppStorage, run_id: str, bundled_dir: Path | None = None) -> dict[str, Any]:
    """Cost, bound, gap, changes and the three verdicts of a saved run, read from its artifacts (nothing is re-run)."""
    directory = storage.run_directory(run_id)
    result = read_json(directory / "joint_result.json")
    if result is None:
        raise FileNotFoundError("Körningen har inget sparat gemensamt resultat.")
    solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
    coverage = result.get("coverage") if isinstance(result.get("coverage"), dict) else {}
    cost, bound = solver.get("objective_value_ore"), solver.get("best_objective_bound_ore")
    validation = read_json(directory / "joint_validation.json")
    verdict = validation.get("summary") if isinstance(validation, dict) and isinstance(validation.get("summary"), dict) else {}
    decision = read_json(directory / "joint_warm_start.json") or {}
    first, basis, source = _first_solution(decision, solver, directory)
    events_path = directory / EVENTS_FILE
    cancelled = any(event.get("type") == "finished" and event.get("cancelled") for event in read_events(events_path)) \
        if events_path.is_file() else str(solver.get("raw_status", "")).endswith("_cancelled")
    technical = verdict.get("technical_validation", "not_evaluated")
    return {
        "run_id": run_id,
        "problem_id": result.get("problem_id"),
        "scenario_id": scenario_id_for_problem(storage, result.get("problem_id"), bundled_dir),
        "created_at": created_at(run_id),
        "parameters_changed_from_default": changed_parameter_count(directory),
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

