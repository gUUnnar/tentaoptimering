"""A quick check of a run before it is started: can the chosen settings possibly place every exam?

Nothing is saved and no cost is reported. The check builds the problem exactly as a run would, counts what the
settings make impossible by themselves (exams without any allowed occasion, exams that must move) and gives the
solver a short time to prove that the exams do not fit. A proof is final; the lack of one is not an answer.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .app_paths import bundled_joint_catalog_path
from .app_storage import AppStorage
from .joint_inputs import build_real_subset_problem
from .joint_optimizer import solve_joint_optimization
from .joint_strategy.resources import CancelToken, ExecutionBudget

PRECHECK_SECONDS = 20.0
IMPOSSIBLE, BLOCKED, UNCLEAR, POSSIBLE = "impossible", "blocked", "unclear", "possible"


def _days(count: int) -> str:
    return f"{count} {'dag' if count == 1 else 'dagar'}"


def precheck(storage: AppStorage, config: Path, snapshot: Path | None, cancel: CancelToken, catalog_path: Path | None = None) -> dict[str, Any]:
    """Verdict (`impossible`, `blocked`, `possible` or `unclear`), the facts behind it and the reasons in plain Swedish.

    `config` and `snapshot` come from `joint_api.run_config`; the snapshot is removed once the problem is built.
    """
    catalog_file = catalog_path or bundled_joint_catalog_path()
    try:
        problem = build_real_subset_problem(config, storage.processed_dir, catalog_file)
    finally:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)
    values = {item.parameter_id: item.value for item in problem.parameters}
    total = len(problem.demands)
    blocked = [item for item in problem.demands if not item.candidate_slot_ids]
    must_move = [item for item in problem.demands if item.candidate_slot_ids and item.original_slot_id not in item.candidate_slot_ids]
    reasons: list[str] = []
    if blocked:
        codes = sorted({str(item.course_code or item.exam_demand_id) for item in blocked})[:5]
        reasons.append(f"{len(blocked)} av {total} tentor har inget tillåtet tillfälle alls (till exempel {', '.join(codes)}). De går inte att placera med de här inställningarna.")
        verdict, seconds, outcome = BLOCKED, 0.0, "blocked"
    else:
        short = replace(problem, solver=replace(problem.solver, time_limit_seconds=min(PRECHECK_SECONDS, problem.solver.time_limit_seconds)))
        result = solve_joint_optimization(short, None, ExecutionBudget(), cancel, None, None)
        outcome, seconds = result.solver.outcome, round(result.solver.wall_time_seconds, 1)
        if must_move:
            earlier, later = int(values.get("window.earlier_days", 0)), int(values.get("window.later_days", 0))
            reasons.append(f"{len(must_move)} av {total} tentor ligger på ett datum eller en tid som inte är tillåten och måste flyttas. Varje tenta får flyttas högst {_days(earlier)} tidigare och {_days(later)} senare.")
        if outcome == "infeasible":
            verdict = IMPOSSIBLE
            reasons.append("Solvern har bevisat att tentorna inte ryms: salarna, kalendern och reglerna räcker inte.")
        elif outcome in ("optimal", "feasible_not_proven"):
            verdict = POSSIBLE
            reasons.append(f"En lösning hittades på {seconds} sekunder: tentorna går att placera med de här inställningarna.")
        else:
            verdict = UNCLEAR
            reasons.append(f"Ingen omöjlighet kunde bevisas på {PRECHECK_SECONDS:.0f} sekunder. Det är inget bevis för att det går; en körning kan ändå ta lång tid.")
    return {"kind": "joint_precheck", "verdict": verdict, "exams_total": total, "blocked_exams": len(blocked), "must_move_exams": len(must_move),
            "solver_outcome": outcome, "seconds": seconds, "reasons": reasons}
