"""Aggregate-first strategy: price the term with a relaxation, verify it day by day with the exact model.

1. The aggregate relaxation (aggregate.py) chooses dates, room portfolio and staff pool. Its optimum,
   or its proven bound, is a lower bound on the joint cost.
2. Each day of the master's schedule is solved exactly with the joint model, restricted to the
   master's portfolio and pool (subproblems.py). Failed days are re-solved together with their
   neighbours, so exams may move across the day boundary within their own candidates.
3. If every day passes, the verified cost equals the master cost and is proven optimal. Otherwise a
   fallback places the failing days with more staff or rooms (an upper bound) and a cut tells the
   master that the failed combination is impossible or needs more staff; the master is re-solved
   while time and the gap allow.

The economic value is decided by the dimensioning days: once the portfolio and pool are fixed, any
feasible placement of the other days costs the same, so those days are only checked for
feasibility, never optimised.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import logging
import time

from ..joint_contract import (
    RESULT_SCHEMA_VERSION, CostBreakdown, CoverageSummary, JointOptimizationInput, JointOptimizationResult, SolverSummary,
)
from ..joint_optimizer import _is_changed, _limitations, _verification
from .aggregate import Cut, Plan, solve_master
from .subproblems import Part, infeasible_core, restrict, solve_part

LOG = logging.getLogger(__name__)

MASTER_SHARE = 0.4      # of the time limit for the first master solve
DAY_SECONDS = 10.0      # per day check
BLOCK_SECONDS = 20.0    # per repair of failed days with their neighbours
CORE_SECONDS = 10.0     # to shrink a failed day to the exams that cause it
MAX_ROUNDS = 25


def solve_decomposed(problem: JointOptimizationInput) -> JointOptimizationResult:
    started = time.perf_counter()
    settings = problem.solver
    deadline = started + settings.time_limit_seconds
    cuts: list[Cut] = []
    cache: dict[tuple, tuple[str, Part | None, int | None]] = {}
    hint: dict[str, str] | None = None
    best: tuple[int, int, list[Part]] | None = None  # cost, changed exams, parts
    lower = 0
    proven = False
    rounds = 0
    for rounds in range(1, MAX_ROUNDS + 1):
        remaining = deadline - time.perf_counter()
        if remaining <= 0.5:
            break
        budget = remaining * (MASTER_SHARE if rounds == 1 else 0.25)
        master = solve_master(problem, budget, settings, tuple(cuts), hint,
                              prefer_history_seconds=min(10.0, 0.1 * remaining))
        LOG.debug("master %s: %s cost %s bound %s plans %d (%.1f s)", rounds, master.status, master.objective,
                  master.bound, len(master.plans), master.wall_seconds)
        if master.status == "infeasible":
            # The relaxation (with valid cuts) has no solution, so neither has the joint model.
            return _no_solution(problem, "infeasible", "aggregate_infeasible", started, rounds,
                                "Den aggregerade relaxationen saknar lösning: kapacitet, byggnad eller kalender räcker inte.")
        if master.status == "unknown":
            break
        lower = max(lower, master.bound or 0)
        hint = master.plans[0].choice
        new_cuts: list[Cut] = []
        # The history-preferring plan first; the plain economic plan only if the first is not already optimal.
        for plan in master.plans:
            parts, plan_cuts = _verify(problem, plan, deadline, cache)
            new_cuts += plan_cuts
            if parts is not None:
                cost, changed = _cost(problem, parts)[-1], _changed(problem, parts)
                if best is None or (cost, changed) < best[:2]:
                    best = (cost, changed, parts)
            if best is not None and best[0] <= lower:
                break
        cuts += new_cuts
        LOG.debug("round %s: best %s lower %s new cuts %d", rounds, best[0] if best else None, lower, len(new_cuts))
        if best is not None and master.status == "optimal" and best[0] <= lower:
            proven = True
            break
        if best is not None and (best[0] - lower) <= settings.relative_gap_limit * best[0]:
            break
        if not new_cuts:
            break
    if best is None:
        return _no_solution(problem, "no_feasibility_conclusion", "decomposed_no_verified_solution", started, rounds,
                            "Ingen dag-för-dag-verifierad lösning hittades inom tidsgränsen.")
    return _result(problem, best[2], lower, proven, started, rounds, len(cuts))


def _verify(
    problem: JointOptimizationInput, plan: Plan, deadline: float, cache: dict[tuple, tuple[str, Part | None, int | None]],
) -> tuple[list[Part] | None, list[Cut]]:
    """Check each day exactly; learn cuts from proven failures; repair; fall back to more staff or rooms."""
    settings = problem.solver
    slots = {slot.slot_id: slot for slot in problem.slots}
    days = sorted({slot.scheduled_date for slot in problem.slots})
    by_day: dict[date, set[str]] = defaultdict(set)
    for exam, slot_id in plan.choice.items():
        by_day[slots[slot_id].scheduled_date].add(exam)
    portfolio = tuple(room for room in problem.rooms if room.room_id in plan.owned)
    pool_cap = plan.pool if problem.staffing.annual_cost_ore_per_staff > 0 else None

    def check(block: frozenset[date], cap: int | None, rooms: tuple, extra: frozenset[str] = frozenset(), seconds=DAY_SECONDS):
        exams = frozenset().union(*(by_day.get(day, set()) for day in block))
        key = (block, exams, frozenset(room.room_id for room in rooms), cap, extra)
        if key not in cache and time.perf_counter() >= deadline:
            return "unknown", None, None  # the time limit is a hard limit, also within a round
        if key not in cache:
            status, part, bound = solve_part(restrict(problem, block, set(exams), rooms), block, cap, extra,
                                             _budget(seconds, deadline), settings)
            cache[key] = (status, part, bound)
        return cache[key]

    parts: dict[frozenset[date], Part] = {}
    failed: list[date] = []
    for day in sorted(by_day):
        status, part, _ = check(frozenset({day}), pool_cap, portfolio)
        if part is None:
            LOG.debug("day %s failed: %s (%d exams)", day, status, len(by_day[day]))
            failed.append(day)
        else:
            parts[frozenset({day})] = part
    cuts: list[Cut] = []
    fallback: dict[date, Part | None] = {}
    for day in list(failed):
        # Diagnose the day alone; only proven infeasibility becomes a cut, never a timeout.
        block, exams = frozenset({day}), by_day[day]
        capped_status = check(block, pool_cap, portfolio)[0]
        status, part, pool_bound = check(block, None, portfolio)
        LOG.debug("day %s with any pool: %s, pool bound %s", day, status, pool_bound)
        if part is not None and (pool_cap is None or peak_staff(problem, list(part.sessions)) <= pool_cap):
            parts[block] = part  # the capped check only timed out; this placement fits the master's pool
            failed.remove(day)
            continue
        if time.perf_counter() >= deadline:
            fallback[day] = part
            continue
        if status == "infeasible":
            core = infeasible_core(problem, block, exams, portfolio, None, _budget(CORE_SECONDS, deadline), settings)
            cuts.append(("rooms", block, core, plan.owned, 0))
        elif pool_cap is not None:
            if pool_bound is not None and pool_bound > pool_cap:
                cuts.append(("pool", block, frozenset(exams), plan.owned, pool_bound))
            if capped_status == "infeasible":
                core = infeasible_core(problem, block, exams, portfolio, pool_cap, _budget(CORE_SECONDS, deadline), settings)
                cuts.append(("pool", block, core, plan.owned, pool_cap + 1))
        fallback[day] = part
    for block in _blocks(failed, days):
        # Repair with the master's portfolio and pool: exams may move between the failed day and its neighbours.
        status, part, _ = check(block, pool_cap, portfolio, seconds=BLOCK_SECONDS)
        LOG.debug("repair %s..%s: %s", min(block), max(block), status)
        if part is not None:
            for key in [key for key in parts if key <= block]:
                del parts[key]
            parts[block] = part
            continue
        for day in sorted(block & set(failed)):
            # Upper bound: the failed day alone with more staff, or also with rooms outside the portfolio.
            part = fallback[day]
            if part is None:
                extra = frozenset(room.room_id for room in problem.rooms) - plan.owned
                part = check(frozenset({day}), None, problem.rooms, extra)[1]
            if part is None:
                return None, cuts
            parts[frozenset({day})] = part
    return list(parts.values()), cuts


def _blocks(failed: list[date], days: list[date], radius: int = 1) -> list[frozenset[date]]:
    blocks: list[set[date]] = []
    for day in failed:
        index = days.index(day)
        block = set(days[max(0, index - radius): index + radius + 1])
        if blocks and blocks[-1] & block:
            blocks[-1] |= block
        else:
            blocks.append(block)
    return [frozenset(block) for block in blocks]


def _budget(seconds: float, deadline: float) -> float:
    return max(0.1, min(seconds, deadline - time.perf_counter()))


def peak_staff(problem: JointOptimizationInput, sessions: list[dict]) -> int:
    """Concurrent required staff at every slot start minus preparation, as in the joint model."""
    slots = {slot.slot_id: slot for slot in problem.slots}
    prep, closing = problem.staffing.preparation_minutes, problem.staffing.closing_minutes
    peak = 0
    for checkpoint_slot in problem.slots:
        checkpoint = checkpoint_slot.start_minute - prep
        active = 0
        for row in sessions:
            slot = slots[row["slot_id"]]
            end = row["available_again_minute"] - problem.turnaround_minutes
            if slot.scheduled_date == checkpoint_slot.scheduled_date and slot.start_minute - prep <= checkpoint < end + closing:
                active += row["required_staff"]
        peak = max(peak, active)
    return peak


def _changed(problem: JointOptimizationInput, parts: list[Part]) -> int:
    slots = {slot.slot_id: slot for slot in problem.slots}
    demands = {item.exam_demand_id: item for item in problem.demands}
    return sum(1 for part in parts for row in part.schedule if _is_changed(demands[row["exam_demand_id"]], row["slot_id"], slots))


def _cost(problem: JointOptimizationInput, parts: list[Part]) -> tuple[int, int, int, int, int, int]:
    sessions = [row for part in parts for row in part.sessions]
    used = {row["room_id"] for row in sessions}
    rooms = {room.room_id: room for room in problem.rooms}
    pool = peak_staff(problem, sessions)
    room_cost = sum(rooms[room].annual_fixed_cost_ore for room in used)
    external = sum(rooms[row["room_id"]].external_session_cost_ore for row in sessions)
    pool_cost = problem.staffing.annual_cost_ore_per_staff * pool
    session_cost = problem.staffing.cost_ore_per_staff_session * sum(row["required_staff"] for row in sessions)
    return pool, room_cost, external, pool_cost, session_cost, room_cost + external + pool_cost + session_cost


def _result(problem, parts, lower, proven, started, rounds, cut_count) -> JointOptimizationResult:
    order = lambda row: tuple(str(row[name]) for name in sorted(row))  # noqa: E731
    assignments = tuple(sorted((row for part in parts for row in part.assignments), key=order))
    sessions = tuple(sorted((row for part in parts for row in part.sessions), key=order))
    schedule = tuple(sorted((row for part in parts for row in part.schedule), key=order))
    pool, room_cost, external, pool_cost, session_cost, total = _cost(problem, parts)
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
            raw_status=f"decomposed_rounds_{rounds}_cuts_{cut_count}",
            objective_value_ore=total,
            best_objective_bound_ore=bound,
            relative_gap=0.0 if bound == total else (total - bound) / max(1, total),
            wall_time_seconds=time.perf_counter() - started,
            change_preference_status="heuristic_master_then_day",
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
