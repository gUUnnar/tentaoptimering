"""Exact checks of a master solution, day by day, with the unchanged joint model.

Given the days the master chose, the joint model separates by day: room bookings, turnaround,
the staffing timeline and course conflicts only couple exams on the same date. A day (or a block
of neighbouring days) is therefore solved on its own with the joint constraints, restricted to the
master's room portfolio and staff pool. Only the portfolio and the pool couple the days, and both
are recomputed from the assembled solution.

Every step gets its own budget, but never beyond the run's deadline, and the model build counts
against the step's budget: CP-SAT only gets the time that is left after the build.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import logging
import time
from typing import Any

from ortools.sat.python import cp_model

from ..joint_contract import JointOptimizationInput, Room, SolverSettings
from ..joint_optimizer import _build_variables_and_constraints, _extract
from ..joint_paid_time import add_paid_time, paid_time_active
from ..joint_preference import max_penalty, penalty_weights
from .aggregate import cp_solver
from .resources import CancelToken, solve_cancellable, wall_time

LOG = logging.getLogger(__name__)
MIN_STEP = 0.5  # seconds; a step that cannot get this much time before the deadline is not started


@dataclass(frozen=True)
class Part:
    """A verified placement of the exams of some days."""

    days: frozenset[date]
    assignments: tuple[dict[str, Any], ...]
    sessions: tuple[dict[str, Any], ...]
    schedule: tuple[dict[str, Any], ...]


def restrict(
    problem: JointOptimizationInput, days: frozenset[date], exam_ids: set[str], rooms: tuple[Room, ...],
    fixed: dict[str, str] | None = None,
) -> JointOptimizationInput:
    """The exams placed on `days`, allowed any of their own candidates on those days, in `rooms`.

    With `fixed`, each exam keeps only its listed slot (used to re-check a known placement).
    """
    slots = tuple(slot for slot in problem.slots if slot.scheduled_date in days)
    slot_ids = {slot.slot_id for slot in slots}
    demands = tuple(
        replace(item, candidate_slot_ids=tuple(
            slot for slot in item.candidate_slot_ids
            if slot in slot_ids and (fixed is None or slot == fixed.get(item.exam_demand_id))))
        for item in problem.demands if item.exam_demand_id in exam_ids
    )
    sub_rooms = tuple(
        replace(room, available_slot_ids=None if room.available_slot_ids is None
                else tuple(slot for slot in room.available_slot_ids if slot in slot_ids))
        for room in rooms
    )
    return replace(problem, slots=slots, demands=demands, rooms=sub_rooms)


def solve_part(
    sub: JointOptimizationInput, days: frozenset[date], pool_cap: int | None, extra_rooms: frozenset[str],
    step_seconds: float, deadline: float, settings: SolverSettings, cancel: CancelToken | None = None,
) -> tuple[str, Part | None, int | None]:
    """Place the exams of `sub` with the joint constraints.

    With `pool_cap`, the pool may not exceed it and the fewest changes are preferred: the master
    already priced the portfolio and pool, and a day pool below the cap has no economic value.
    Without it, the extra cost over the master's portfolio is minimised: rooms in `extra_rooms` cost
    their fixed cost, and the pool costs as usual. Every per-session charge (staff and external
    hire) counts in both modes, as in the joint objective. Returns the status, the part and a proven
    lower bound on the part's pool (for cuts).
    """
    if not sub.demands:
        return "optimal", Part(days, (), (), ()), 0
    if any(not item.candidate_slot_ids for item in sub.demands):
        return "infeasible", None, None
    started = time.perf_counter()
    budget_end = started + min(step_seconds, deadline - started)
    if budget_end - started < MIN_STEP:
        return "unknown", None, None
    model = cp_model.CpModel()
    slots = {slot.slot_id: slot for slot in sub.slots}
    variables = _build_variables_and_constraints(model, sub, slots)
    weights = penalty_weights(sub)  # the second goal: booked occasions, or the business's wishes in order
    changes = [weight * variables.selected[key] for key, weight in weights.items()]
    scale = max_penalty(weights) + 1  # cost first, then the preference
    session_cost = sub.staffing.cost_ore_per_staff_session * sum(variables.staff.values()) + sum(
        room.external_session_cost_ore * variables.sessions[room.room_id, slot.slot_id]
        for room in sub.rooms for slot in sub.slots if room.external_session_cost_ore
    ) + add_paid_time(model, sub, variables)
    if pool_cap is not None:
        model.Add(variables.staff_pool <= pool_cap)
        cost = session_cost
    else:
        cost = (
            sum(room.annual_fixed_cost_ore * variables.owned[room.room_id] for room in sub.rooms if room.room_id in extra_rooms)
            + sub.staffing.annual_cost_ore_per_staff * variables.staff_pool + session_cost
        )
    model.Minimize(scale * cost + sum(changes))
    built = time.perf_counter()
    if budget_end - built < 0.1:
        LOG.debug("part %s..%s: no time left after a %.2f s build", min(days), max(days), built - started)
        return "unknown", None, None
    solver = cp_solver(budget_end - built, settings)
    status = solve_cancellable(solver, model, cancel)
    log_step("part", days, len(sub.demands), started, built, solver, budget_end - built)
    if status == cp_model.INFEASIBLE:
        return "infeasible", None, None
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "unknown", None, None
    assignments, sessions, schedule = _extract(sub, solver, variables, slots)
    pool_bound = None
    only_pool = (sub.staffing.cost_ore_per_staff_session == 0 and not any(room.external_session_cost_ore for room in sub.rooms)
                 and not paid_time_active(sub))
    if pool_cap is None and sub.staffing.annual_cost_ore_per_staff > 0 and not extra_rooms and only_pool:
        # objective = scale * staff_cost * pool + changes, with changes < scale
        pool_bound = int(solver.BestObjectiveBound() // (scale * sub.staffing.annual_cost_ore_per_staff))
    return ("optimal" if status == cp_model.OPTIMAL else "feasible"), Part(days, assignments, sessions, schedule), pool_bound


def log_step(kind: str, days, size: int, started: float, built: float, solver: cp_model.CpSolver, limit: float) -> None:
    """Record build and solve time separately; flag a solve that ran past its limit."""
    done = time.perf_counter()
    first, last = (min(days), max(days)) if days else ("-", "-")
    solved = wall_time(solver)
    LOG.debug("%s %s..%s (%d): build %.2f s, solve %.2f s of %.2f s, total %.2f s",
              kind, first, last, size, built - started, solved, limit, done - started)
    if solved > limit + 1.0:
        LOG.warning("%s %s..%s: CP-SAT used %.1f s with a %.1f s limit", kind, first, last, solved, limit)


def is_infeasible(
    problem: JointOptimizationInput, days: frozenset[date], exam_ids: set[str], rooms: tuple[Room, ...],
    pool_cap: int | None, step_seconds: float, deadline: float, settings: SolverSettings, cancel: CancelToken | None = None,
) -> bool:
    """True only when the joint model proves the exams cannot be placed on `days` in `rooms` within the pool."""
    started = time.perf_counter()
    budget_end = started + min(step_seconds, deadline - started)
    sub = restrict(problem, days, exam_ids, rooms)
    if not sub.demands or budget_end - started < 0.1:
        return False
    model = cp_model.CpModel()
    variables = _build_variables_and_constraints(model, sub, {slot.slot_id: slot for slot in sub.slots})
    if pool_cap is not None:
        model.Add(variables.staff_pool <= pool_cap)
    built = time.perf_counter()
    if budget_end - built < 0.1:
        return False
    solver = cp_solver(budget_end - built, settings)
    status = solve_cancellable(solver, model, cancel)
    log_step("core-check", days, len(sub.demands), started, built, solver, budget_end - built)
    return status == cp_model.INFEASIBLE


def infeasible_core(
    problem: JointOptimizationInput, days: frozenset[date], exam_ids: set[str], rooms: tuple[Room, ...],
    pool_cap: int | None, step_seconds: float, deadline: float, settings: SolverSettings, cancel: CancelToken | None = None,
) -> frozenset[str]:
    """Shrink an infeasible exam set by deletion; an exam is dropped only when infeasibility is proven
    without it, so the returned set is always infeasible (a valid, stronger cut)."""
    stop = min(time.perf_counter() + step_seconds, deadline)
    sizes = {item.exam_demand_id: item.participant_count for item in problem.demands}
    core = sorted(exam_ids, key=lambda exam: sizes[exam])
    chunk = max(1, len(core) // 2)
    while chunk >= 1 and time.perf_counter() < stop and not (cancel and cancel.cancelled):
        index, changed = 0, False
        while index < len(core) and time.perf_counter() < stop and not (cancel and cancel.cancelled):
            trial = core[:index] + core[index + chunk:]
            if trial and is_infeasible(problem, days, set(trial), rooms, pool_cap, 2.0, stop, settings, cancel):
                core, changed = trial, True
            else:
                index += chunk
        chunk = chunk // 2 if not changed or chunk > 1 else 0
    return frozenset(core)
