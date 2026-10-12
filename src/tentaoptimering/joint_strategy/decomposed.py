"""Aggregate-first strategy: price the term with a relaxation, verify it day by day with the exact model.

1. The aggregate relaxation (aggregate.py) chooses dates, room portfolio and staff pool. Its optimum,
   or its proven bound, is a lower bound on the joint cost.
2. The relaxation's economic plan is checked day by day with the joint model, restricted to the
   plan's portfolio and pool (verification.py). Failed days are re-solved together with their
   neighbours, so exams may move across the day boundary within their own candidates.
3. If every day passes, the verified cost equals the relaxation's cost and is proven optimal.
   Otherwise a fallback places the failing days with more staff or rooms (an upper bound) and a
   cut tells the relaxation that the failed combination is impossible or needs more staff.
4. Once a plan is verified, a history-preferring plan with the same portfolio and pool is swapped in
   wherever its days verify, so exams stay on their historical slot when that costs nothing.

An earlier saved placement can seed the search (`start`, see warm_start.py): it is never trusted, only
re-checked day by day in the current instance. If it passes, it becomes the first upper bound; if not, the
earlier slots that are still allowed are given to the relaxation as a hint. What happened is recorded in
a `StartReport`.

The exact day checks run in parallel within one thread and memory budget (resources.py, verification.py);
`cancel` stops the run, which then returns the best complete verified solution it has, if any.

The economic value is decided by the dimensioning days: once the portfolio and pool are fixed, any
feasible placement of the other days costs the same, so those days are only checked for
feasibility, never optimised.
"""

from __future__ import annotations

import logging
import time

from ..joint_contract import (
    RESULT_SCHEMA_VERSION, CostBreakdown, CoverageSummary, JointOptimizationInput, JointOptimizationResult, SolverSummary,
)
from ..joint_optimizer import _is_changed, _limitations, _verification
from ..joint_progress import ProgressSink, emit, finished_event, phase, resources_event
from .aggregate import Cut, solve_master
from .resources import CancelToken, ExecutionBudget
from .subproblems import Part
from .verification import Checker, Parts, cost, prefer_history, verify
from .warm_start import ACCEPTED, StartReport, warm_start

LOG = logging.getLogger(__name__)

MASTER_SHARE = 0.4      # of the remaining time for the first relaxation solve
MAX_ROUNDS = 25


def solve_decomposed(
    problem: JointOptimizationInput, start: tuple[dict[str, str], set[str]] | None = None,
    budget: ExecutionBudget | None = None, cancel: CancelToken | None = None, report: StartReport | None = None,
    progress: ProgressSink | None = None,
) -> JointOptimizationResult:
    """`start` is an earlier saved placement: exam -> slot, and the rooms it used. It is re-checked, not trusted.

    `progress` only observes the run (phases, day checks, solutions, bounds); it never changes a decision.
    """
    started = time.perf_counter()
    report = report if report is not None else StartReport()
    deadline = started + problem.solver.time_limit_seconds
    checker = Checker(problem, deadline, budget, cancel, progress)
    settings = checker.budget.settings(problem.solver)  # one thread budget for the relaxation and the day checks
    resources_event(progress, checker.budget)
    cuts: list[Cut] = []
    best: tuple[int, int, Parts] | None = None  # cost, changed exams, parts
    best_source = ""
    first_at: float | None = None
    lower = 0
    proven = False
    rounds = 0

    def consider(parts: Parts | None, source: str) -> int | None:
        nonlocal best, best_source, first_at
        if parts is None:
            return None
        total, changed = cost(problem, list(parts.values()))[-1], _changed(problem, list(parts.values()))
        if best is None or (total, changed) < best[:2]:
            best, best_source = (total, changed, parts), source
            emit(progress, "incumbent", cost_ore=total, source=source, changed_exams=changed)
        if first_at is None:
            first_at = time.perf_counter() - started
            report.first_solution_seconds, report.first_solution_source = first_at, source
            LOG.debug("first complete solution after %.1f s (%s): %s öre", first_at, source, total)
        return total

    hint = None
    if start is not None:
        with phase(progress, "warm_start_check"):
            parts, hint = warm_start(checker, *start, report)
            report.verified_cost_ore = consider(parts, "warm start")
        if parts is not None:
            report.status = ACCEPTED
    for rounds in range(1, MAX_ROUNDS + 1):
        remaining = deadline - time.perf_counter()
        if remaining <= 1.0 or checker.cancel.cancelled:
            break
        # The first relaxation keeps its planned share of the whole limit; a warm start must not shorten it.
        with phase(progress, "relaxation"):
            master = solve_master(problem, min(remaining, MASTER_SHARE * problem.solver.time_limit_seconds) if rounds == 1 else remaining * 0.25,
                                  settings, tuple(cuts), hint,
                                  prefer_history_seconds=min(10.0, 0.1 * remaining), cancel=checker.cancel)
        LOG.debug("master %s: %s cost %s bound %s plans %d (%.1f s)", rounds, master.status, master.objective,
                  master.bound, len(master.plans), master.wall_seconds)
        if master.status == "infeasible":
            # The relaxation (with valid cuts) has no solution, so neither has the joint model.
            return finished_event(progress, _no_solution(
                problem, "infeasible", "aggregate_infeasible", started, rounds,
                "Den aggregerade relaxationen saknar lösning: kapacitet, byggnad eller kalender räcker inte."), checker.cancel.cancelled)
        if master.status == "unknown":
            break
        lower = max(lower, master.bound or 0)
        if master.bound is not None:
            emit(progress, "bound", lower_ore=lower, round=rounds)
        economic = master.plans[0]
        hint = economic.choice
        parts, new_cuts = verify(checker, economic)
        consider(parts, f"round {rounds}")
        if parts is not None and len(master.plans) > 1:
            with phase(progress, "history"):
                consider(prefer_history(checker, parts, economic, master.plans[1]), f"round {rounds} history")
        cuts += new_cuts
        LOG.debug("round %s: best %s lower %s new cuts %d", rounds, best[0] if best else None, lower, len(new_cuts))
        if best is not None and master.status == "optimal" and best[0] <= lower:
            proven = True
            break
        if best is not None and (best[0] - lower) <= settings.relative_gap_limit * best[0]:
            break
        if not new_cuts:
            break
    LOG.debug("time by step: %s", {kind: f"{seconds:.1f} s / {checker.calls[kind]}" for kind, seconds in checker.seconds.items()})
    report.interrupted = checker.cancel.cancelled
    if best is None:
        return finished_event(progress, _no_solution(
            problem, "no_feasibility_conclusion", "decomposed_cancelled" if report.interrupted else "decomposed_no_verified_solution",
            started, rounds, "Körningen avbröts innan någon dag-för-dag-verifierad lösning fanns." if report.interrupted
            else "Ingen dag-för-dag-verifierad lösning hittades inom tidsgränsen."), report.interrupted)
    report.final_cost_ore, report.final_source = best[0], best_source
    return finished_event(progress, _result(problem, list(best[2].values()), lower, proven, started, rounds, len(cuts), first_at,
                                            report.interrupted), report.interrupted)


def _changed(problem: JointOptimizationInput, parts: list[Part]) -> int:
    slots = {slot.slot_id: slot for slot in problem.slots}
    demands = {item.exam_demand_id: item for item in problem.demands}
    return sum(1 for part in parts for row in part.schedule if _is_changed(demands[row["exam_demand_id"]], row["slot_id"], slots))


def _result(problem, parts, lower, proven, started, rounds, cut_count, first_at, interrupted=False) -> JointOptimizationResult:
    order = lambda row: tuple(str(row[name]) for name in sorted(row))  # noqa: E731
    assignments = tuple(sorted((row for part in parts for row in part.assignments), key=order))
    sessions = tuple(sorted((row for part in parts for row in part.sessions), key=order))
    schedule = tuple(sorted((row for part in parts for row in part.schedule), key=order))
    pool, room_cost, external, pool_cost, session_cost, total = cost(problem, parts)
    bound = min(lower, total)
    slots = {slot.slot_id: slot for slot in problem.slots}
    demands = {item.exam_demand_id: item for item in problem.demands}
    physical = sum(row["participants"] for row in assignments)
    non_room = sum(item.participant_count for item in problem.demands if not item.requires_room)
    participants = sum(item.participant_count for item in problem.demands)
    return JointOptimizationResult(
        schema_version=RESULT_SCHEMA_VERSION,
        problem_id=problem.problem_id,
        solver=SolverSummary(
            outcome="optimal" if proven and bound == total else "feasible_not_proven",
            raw_status=f"decomposed_rounds_{rounds}_cuts_{cut_count}_first_solution_{first_at:.0f}s" + ("_cancelled" if interrupted else ""),
            objective_value_ore=total,
            best_objective_bound_ore=bound,
            relative_gap=0.0 if bound == total else (total - bound) / max(1, total),
            wall_time_seconds=time.perf_counter() - started,
            change_preference_status="heuristic_history_plan_swapped_where_verified",
            strategy="decomposed",
        ),
        costs=CostBreakdown(room_cost, external, pool_cost, session_cost, total),
        coverage=CoverageSummary(
            len(problem.demands), len(schedule), participants, physical, non_room,
            len(schedule) == len(problem.demands) and physical + non_room == participants,
        ),
        staff_pool_size=pool,
        changed_exam_demands=sum(1 for row in schedule if _is_changed(demands[row["exam_demand_id"]], row["slot_id"], slots)),
        assignments=assignments,
        room_sessions=sessions,
        schedule=schedule,
        limitations=_limitations(problem) + (
            "Strategi: aggregerad relaxation för datum, lokalportfölj och bemanningspool, därefter exakt kontroll dag för dag "
            "med den gemensamma modellen. Undre gränsen kommer från relaxationen.",
        ),
        verification=_verification(problem, proven and bound == total, assignments),
    )


def _no_solution(problem, outcome, raw, started, rounds, reason) -> JointOptimizationResult:
    participants = sum(item.participant_count for item in problem.demands)
    return JointOptimizationResult(
        RESULT_SCHEMA_VERSION, problem.problem_id,
        SolverSummary(outcome, raw, None, None, None, time.perf_counter() - started, "not_run", "decomposed"),
        None, CoverageSummary(len(problem.demands), 0, participants, 0, 0, False), None, None, (), (), (),
        (reason, *_limitations(problem)),
        {"solver": outcome, "independent_validation": "not_performed", "student_overlap": "not_evaluated"},
    )
