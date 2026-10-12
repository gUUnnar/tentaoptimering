"""Exact checks of a master solution, day by day, with the unchanged joint model.

Given the days the master chose, the joint model separates by day: room bookings, turnaround,
the staffing timeline and course conflicts only couple exams on the same date. A day (or a block
of neighbouring days) is therefore solved on its own with the joint constraints, restricted to the
master's room portfolio and staff pool. Only the portfolio and the pool couple the days, and both
are recomputed from the assembled solution.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import time
from typing import Any

from ortools.sat.python import cp_model

from ..joint_contract import JointOptimizationInput, Room, SolverSettings
from ..joint_optimizer import _build_variables_and_constraints, _extract
from .aggregate import cp_solver


@dataclass(frozen=True)
class Part:
    """A verified placement of the exams of some days."""

    days: frozenset[date]
    assignments: tuple[dict[str, Any], ...]
    sessions: tuple[dict[str, Any], ...]
    schedule: tuple[dict[str, Any], ...]


def restrict(
    problem: JointOptimizationInput, days: frozenset[date], exam_ids: set[str], rooms: tuple[Room, ...],
) -> JointOptimizationInput:
    """The exams placed on `days`, allowed any of their own candidates on those days, in `rooms`."""
    slots = tuple(slot for slot in problem.slots if slot.scheduled_date in days)
    slot_ids = {slot.slot_id for slot in slots}
    demands = tuple(
        replace(item, candidate_slot_ids=tuple(slot for slot in item.candidate_slot_ids if slot in slot_ids))
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
    time_limit: float, settings: SolverSettings,
) -> tuple[str, Part | None, int | None]:
    """Place the exams of `sub` with the joint constraints.

    With `pool_cap`, the pool may not exceed it and the fewest changes are preferred: the master
    already priced the portfolio and pool, and a day pool below the cap has no economic value.
    Without it, the extra cost over the master's portfolio is minimised: rooms in `extra_rooms` cost
    their fixed cost, and the pool costs as usual. Returns the status, the part and a proven lower
    bound on the part's pool (for cuts).
    """
    if not sub.demands:
        return "optimal", Part(days, (), (), ()), 0
    model = cp_model.CpModel()
    slots = {slot.slot_id: slot for slot in sub.slots}
    variables = _build_variables_and_constraints(model, sub, slots)
    changes = [
        1 - variables.selected[item.exam_demand_id, item.original_slot_id] for item in sub.demands
        if item.original_slot_id is not None and item.original_slot_id in item.candidate_slot_ids
    ]
    scale = len(changes) + 1  # cost first, then the fewest changes
    session_cost = sub.staffing.cost_ore_per_staff_session * sum(variables.staff.values())
    if pool_cap is not None:
        # Below the master's pool a smaller day pool saves nothing; only per-session cost and changes count.
        model.Add(variables.staff_pool <= pool_cap)
        cost = session_cost
    else:
        cost = (
            sum(room.annual_fixed_cost_ore * variables.owned[room.room_id] for room in sub.rooms if room.room_id in extra_rooms)
            + sub.staffing.annual_cost_ore_per_staff * variables.staff_pool + session_cost
        )
    model.Minimize(scale * cost + sum(changes))
    solver = cp_solver(time_limit, settings)
    status = solver.Solve(model)
    if status == cp_model.INFEASIBLE:
        return "infeasible", None, None
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "unknown", None, None
    assignments, sessions, schedule = _extract(sub, solver, variables, slots)
    pool_bound = None
    if pool_cap is None and sub.staffing.annual_cost_ore_per_staff > 0 and not extra_rooms and sub.staffing.cost_ore_per_staff_session == 0:
        # objective = scale * staff_cost * pool + changes, with changes < scale
        pool_bound = int(solver.BestObjectiveBound() // (scale * sub.staffing.annual_cost_ore_per_staff))
    return ("optimal" if status == cp_model.OPTIMAL else "feasible"), Part(days, assignments, sessions, schedule), pool_bound


def is_infeasible(
    problem: JointOptimizationInput, days: frozenset[date], exam_ids: set[str], rooms: tuple[Room, ...],
    pool_cap: int | None, time_limit: float, settings: SolverSettings,
) -> bool:
    """True only when the joint model proves the exams cannot be placed on `days` in `rooms` within the pool."""
    sub = restrict(problem, days, exam_ids, rooms)
    if not sub.demands:
        return False
    model = cp_model.CpModel()
    variables = _build_variables_and_constraints(model, sub, {slot.slot_id: slot for slot in sub.slots})
    if pool_cap is not None:
        model.Add(variables.staff_pool <= pool_cap)
    return cp_solver(time_limit, settings).Solve(model) == cp_model.INFEASIBLE


def infeasible_core(
    problem: JointOptimizationInput, days: frozenset[date], exam_ids: set[str], rooms: tuple[Room, ...],
    pool_cap: int | None, time_limit: float, settings: SolverSettings,
) -> frozenset[str]:
    """Shrink an infeasible exam set by deletion; an exam is dropped only when infeasibility is proven
    without it, so the returned set is always infeasible (a valid, stronger cut)."""
    deadline = time.perf_counter() + time_limit
    core = sorted(exam_ids, key=lambda exam: participants(problem, exam))
    chunk = max(1, len(core) // 2)
    while chunk >= 1 and time.perf_counter() < deadline:
        index, changed = 0, False
        while index < len(core) and time.perf_counter() < deadline:
            trial = core[:index] + core[index + chunk:]
            budget = min(2.0, deadline - time.perf_counter())
            if trial and budget > 0.1 and is_infeasible(problem, days, set(trial), rooms, pool_cap, budget, settings):
                core, changed = trial, True
            else:
                index += chunk
        chunk = chunk // 2 if not changed or chunk > 1 else 0
    return frozenset(core)


def participants(problem: JointOptimizationInput, exam_id: str) -> int:
    return next(item.participant_count for item in problem.demands if item.exam_demand_id == exam_id)
