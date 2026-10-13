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
from .joint_validation import validate_run

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


def changed_parameter_ids(directory: Path) -> list[str]:
    """The ids of the frozen parameters of the run that differ from the catalog default."""
    items = (read_json(directory / "joint_input.json") or {}).get("parameters", ())
    return sorted(str(item["parameter_id"]) for item in items if isinstance(item, dict) and item.get("changed_from_default"))


_VALIDATION_CACHE: dict[tuple, dict[str, Any]] = {}


def validated_now(directory: Path) -> dict[str, Any]:
    """The independent validation of the saved run, run now. A stored verdict is never taken as evidence.

    The artifacts are hashed against the manifest by the validator itself, so a result that changed after its run
    does not count as verified. The answer is cached per state of the files, because a validation takes seconds
    for a whole term.
    """
    key = tuple((name, (directory / name).stat().st_mtime_ns, (directory / name).stat().st_size)
                for name in ("joint_input.json", "joint_result.json", "joint_manifest.json") if (directory / name).is_file())
    key = (str(directory.resolve()), *key)
    if key not in _VALIDATION_CACHE:
        _VALIDATION_CACHE[key] = validate_run(directory)["summary"]
    return _VALIDATION_CACHE[key]


def run_summary(storage: AppStorage, run_id: str, bundled_dir: Path | None = None) -> dict[str, Any]:
    """Cost, bound, gap, changes and the three verdicts of a saved run, read from its artifacts (nothing is re-run)."""
    directory = storage.run_directory(run_id)
    result = read_json(directory / "joint_result.json")
    if result is None:
        raise FileNotFoundError("Körningen har inget sparat gemensamt resultat.")
    solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
    coverage = result.get("coverage") if isinstance(result.get("coverage"), dict) else {}
    cost, bound = solver.get("objective_value_ore"), solver.get("best_objective_bound_ore")
    verdict = validated_now(directory)
    decision = read_json(directory / "joint_warm_start.json") or {}
    first, basis, source = _first_solution(decision, solver, directory)
    events_path = directory / EVENTS_FILE
    cancelled = any(event.get("type") == "finished" and event.get("cancelled") for event in read_events(events_path)) \
        if events_path.is_file() else str(solver.get("raw_status", "")).endswith("_cancelled")
    technical = verdict.get("technical_validation", "not_evaluated")
    verified = bool(solver.get("outcome") in ("optimal", "feasible_not_proven")
                    and coverage.get("technical_placement_complete") and technical == "pass"
                    and verdict.get("technically_validated", False))
    changed_ids = changed_parameter_ids(directory)
    return {
        "run_id": run_id,
        "problem_id": result.get("problem_id"),
        "scenario_id": scenario_id_for_problem(storage, result.get("problem_id"), bundled_dir),
        "created_at": created_at(run_id),
        "parameters_changed_from_default": changed_ids,
        "parameters_changed_count": len(changed_ids),
        "solver_outcome": solver.get("outcome"),
        # A run without a placement has nothing to validate wrongly, so its technical verdict can read `pass`;
        # only a complete placement that the independent validation accepts counts as a verified solution.
        "has_verified_solution": verified,
        # Without a verified solution no cost is reported at all: a number from a result that the independent
        # validation does not accept must not look like a result.
        "unverified_reason": None if verified else _unverified_reason(solver, coverage, technical, verdict),
        "cost_is_proven_optimum": verified and solver.get("outcome") == "optimal",
        "cost_ore": cost if verified else None,
        "lower_bound_ore": bound if verified else None,
        "gap_ore": cost - bound if verified and isinstance(cost, int) and isinstance(bound, int) else None,
        "gap_relative": solver.get("relative_gap") if verified else None,
        "changed_exams": result.get("changed_exam_demands") if verified else None,
        "exams_total": coverage.get("exam_demands_total"),
        "technical_placement_complete": coverage.get("technical_placement_complete"),
        "staff_pool_size": result.get("staff_pool_size") if verified else None,
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
            "source": "validated_now",
        },
    }


def _unverified_reason(solver: dict[str, Any], coverage: dict[str, Any], technical: str, verdict: dict[str, Any]) -> str:
    if solver.get("outcome") not in ("optimal", "feasible_not_proven") or not coverage.get("technical_placement_complete"):
        return "Körningen har ingen fullständig placering."
    if verdict.get("provenance") == "fail":
        return "Körningens filer stämmer inte med manifestet: de har ändrats efter körningen."
    return f"Den oberoende tekniska eftervalideringen godkänner inte körningen (status: {technical})."


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

