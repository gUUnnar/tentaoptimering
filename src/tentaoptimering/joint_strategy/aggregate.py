"""Aggregate relaxation of the joint model: dates, room portfolio and staff pool without room assignment.

Every feasible joint solution maps to a feasible aggregate solution with the same portfolio and a
pool that is at least as large, so the aggregate optimum (or its proven bound) is a valid lower
bound on the joint cost. The relaxation drops which exam sits in which room; it keeps:

- per day and slot start: the participants of exams still occupying rooms (duration plus
  turnaround) fit in the owned, available rooms (all rooms and digitally capable rooms);
- an exam that may not be split across buildings needs one owned building that holds it;
- sessions starting at a slot sit in distinct owned rooms, each needing staff by the ladder
  (linear hull with a use indicator); sessions started earlier and still staffed are bounded by
  the lower hull of the ladder;
- course and explicit conflict groups exactly as in the joint model.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import logging
import time
from typing import Any

from ortools.sat.python import cp_model

from ..joint_contract import ExamDemand, JointOptimizationInput, Room, SolverSettings, StaffingStep
from ..joint_optimizer import _conflicts, _overlap, staffing_cut_edges
from .resources import CancelToken, solve_cancellable

# A cut excludes, or prices, master solutions where every listed exam lies on the listed days and no
# room outside `rooms` is owned. kind "rooms": that combination is infeasible; kind "pool": it needs
# at least `value` concurrent staff.
Cut = tuple[str, frozenset[date], frozenset[str], frozenset[str], int]

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Plan:
    """Dates, portfolio and pool proposed by the relaxation."""

    choice: dict[str, str]
    owned: frozenset[str]
    pool: int


@dataclass(frozen=True)
class MasterSolution:
    status: str
    objective: int | None
    bound: int | None
    plans: tuple[Plan, ...]  # the economic plan, then a history-preferring plan with the same portfolio if it differs
    wall_seconds: float


def solve_master(
    problem: JointOptimizationInput,
    time_limit: float,
    settings: SolverSettings,
    cuts: tuple[Cut, ...] = (),
    hint: dict[str, str] | None = None,
    prefer_history_seconds: float = 0.0,
    cancel: CancelToken | None = None,
) -> MasterSolution:
    """Minimise the relaxed cost; optionally then keep historical slots with the same portfolio and pool.

    The model build counts against `time_limit`.
    """
    started = time.perf_counter()
    model, x, owned, pool, cost = _build(problem, cuts, hint)
    built = time.perf_counter()
    solver = cp_solver(max(0.1, time_limit - (built - started)), settings)
    status = solve_cancellable(solver, model, cancel)
    LOG.debug("master build %.2f s, solve %.2f s of %.2f s", built - started, solver.WallTime(), time_limit - (built - started))
    wall = time.perf_counter() - started
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        name = "infeasible" if status == cp_model.INFEASIBLE else "unknown"
        return MasterSolution(name, None, None, (), wall)
    objective, bound = int(solver.ObjectiveValue()), int(round(solver.BestObjectiveBound()))
    economic = _plan(solver, x, owned, pool)
    plans = (economic,)
    if status == cp_model.OPTIMAL and prefer_history_seconds > 0:
        kept = _history_terms(problem, x)
        if kept:
            # Same cost, same portfolio, no larger pool: only the dates may change, towards history.
            model.Add(cost <= objective)
            for room, var in owned.items():
                model.Add(var == int(room in economic.owned))
            model.Add(pool <= economic.pool)
            model.Maximize(sum(kept))
            # Start from the complete first-phase solution so the search begins feasible.
            model.ClearHints()
            for index in range(len(model.Proto().variables)):
                var = model.GetIntVarFromProtoIndex(index)
                model.AddHint(var, solver.Value(var))
            second = cp_solver(prefer_history_seconds, settings)
            if solve_cancellable(second, model, cancel) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                history = _plan(second, x, owned, pool)
                if history != economic:
                    plans = (economic, history)
            wall = time.perf_counter() - started
    return MasterSolution(
        "optimal" if status == cp_model.OPTIMAL else "feasible",
        objective,
        objective if status == cp_model.OPTIMAL else bound,
        plans,
        wall,
    )


def _plan(solver: cp_model.CpSolver, x, owned, pool) -> Plan:
    return Plan(
        {demand: slot for (demand, slot), var in x.items() if solver.Value(var)},
        frozenset(room for room, var in owned.items() if solver.Value(var)),
        int(solver.Value(pool)),
    )


def cp_solver(time_limit: float, settings: SolverSettings) -> cp_model.CpSolver:
    """A CP-SAT solver honouring the run's workers, seed and reproducibility setting."""
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.1, time_limit)
    solver.parameters.num_search_workers = settings.num_workers
    solver.parameters.random_seed = settings.random_seed
    if settings.deterministic and settings.num_workers > 1:
        solver.parameters.interleave_search = True
    return solver


def _history_terms(problem: JointOptimizationInput, x: dict[tuple[str, str], Any]) -> list[Any]:
    return [
        x[item.exam_demand_id, item.original_slot_id] for item in problem.demands
        if item.original_slot_id is not None and item.original_slot_id in item.candidate_slot_ids
    ]


def _room_capacity(problem: JointOptimizationInput) -> dict[str, int]:
    ladder_max = problem.staffing.ladder[-1].max_participants
    return {room.room_id: min(room.capacity, ladder_max) for room in problem.rooms}


def _fits(demand: ExamDemand, room: Room) -> bool:
    return room.plan_area == demand.plan_area and (
        demand.digital_requirement in {"none", "unknown"} or demand.digital_requirement in room.digital_capabilities
    )


def _build(problem: JointOptimizationInput, cuts: tuple[Cut, ...], hint: dict[str, str] | None):
    model = cp_model.CpModel()
    slots = {slot.slot_id: slot for slot in problem.slots}
    cap = _room_capacity(problem)
    owned = {room.room_id: model.NewBoolVar(f"own_{room.room_id}") for room in problem.rooms}
    x: dict[tuple[str, str], Any] = {}
    for demand in problem.demands:
        for slot_id in demand.candidate_slot_ids:
            x[demand.exam_demand_id, slot_id] = model.NewBoolVar(f"x_{demand.exam_demand_id}_{slot_id}")
        model.AddExactlyOne(x[demand.exam_demand_id, slot_id] for slot_id in demand.candidate_slot_ids)
    _room_time_capacity(model, problem, slots, x, owned, cap)
    _building_integrity(model, problem, owned, cap)
    pool = model.NewIntVar(0, len(problem.rooms) * problem.staffing.ladder[-1].required_staff * len(problem.slots), "pool")
    session_staff, external = _staffing_bound(model, problem, slots, x, owned, cap, pool)
    _conflict_pairs(model, problem, slots, x)
    cost = (
        sum(room.annual_fixed_cost_ore * owned[room.room_id] for room in problem.rooms)
        + problem.staffing.annual_cost_ore_per_staff * pool
        + problem.staffing.cost_ore_per_staff_session * session_staff
        + external
    )
    model.Minimize(cost)
    _add_cuts(model, problem, slots, x, owned, pool, cuts)
    if hint:
        for (demand, slot_id), var in x.items():
            if demand in hint:  # an exam without an earlier placement gets no hint, not a hint of "nowhere"
                model.AddHint(var, int(hint[demand] == slot_id))
    return model, x, owned, pool, cost


def _room_time_capacity(model, problem, slots, x, owned, cap) -> None:
    by_day = defaultdict(list)
    for slot in problem.slots:
        by_day[slot.scheduled_date].append(slot)
    terms: dict[tuple[str, date, int, str], list[Any]] = defaultdict(list)
    for demand in problem.demands:
        if not demand.requires_room:
            continue
        for slot_id in demand.candidate_slot_ids:
            slot = slots[slot_id]
            busy_until = slot.start_minute + demand.duration_minutes + problem.turnaround_minutes
            for other in by_day[slot.scheduled_date]:
                if slot.start_minute <= other.start_minute < busy_until:
                    term = demand.participant_count * x[demand.exam_demand_id, slot_id]
                    terms[demand.plan_area, slot.scheduled_date, other.start_minute, "all"].append(term)
                    if demand.digital_requirement not in {"none", "unknown", "paper"}:
                        terms[demand.plan_area, slot.scheduled_date, other.start_minute, demand.digital_requirement].append(term)
    for (area, day, _start, kind), load in terms.items():
        rooms = [
            room for room in problem.rooms
            if room.plan_area == area and (kind == "all" or kind in room.digital_capabilities)
            and (room.available_slot_ids is None or any(slots[item].scheduled_date == day for item in room.available_slot_ids))
        ]
        model.Add(sum(load) <= sum(cap[room.room_id] * owned[room.room_id] for room in rooms))


def _building_integrity(model, problem, owned, cap) -> None:
    buildings: dict[tuple[str, str], list[Room]] = defaultdict(list)
    for room in problem.rooms:
        buildings[room.plan_area, room.building_id].append(room)
    for demand in problem.demands:
        if not demand.requires_room or demand.allow_split_across_buildings:
            continue
        options = []
        for (area, building), rooms in sorted(buildings.items()):
            usable = [room for room in rooms if _fits(demand, room)]
            largest = sorted((cap[room.room_id] for room in usable), reverse=True)[: demand.max_rooms]
            if area != demand.plan_area or sum(largest) < demand.participant_count:
                continue
            choice = model.NewBoolVar(f"building_{demand.exam_demand_id}_{building}")
            model.Add(sum(cap[room.room_id] * owned[room.room_id] for room in usable) >= demand.participant_count * choice)
            options.append(choice)
        model.AddBoolOr(options or [model.NewConstant(0)])  # no building can hold it: the relaxation is infeasible


def _ladder_table(problem: JointOptimizationInput, capacity: int) -> list[int]:
    ladder = problem.staffing.ladder
    return [0] + [
        next((step.required_staff for step in ladder if occupancy <= step.max_participants), ladder[-1].required_staff)
        for occupancy in range(1, capacity + 1)
    ]


def _hull_from_one(table: list[int]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Lower convex hull of (occupancy, staff) for occupancy >= 1; valid whenever a room is in use."""
    hull: list[tuple[int, int]] = []
    for point in [(occupancy, table[occupancy]) for occupancy in range(1, len(table))]:
        while len(hull) >= 2 and (
            (hull[-1][0] - hull[-2][0]) * (point[1] - hull[-2][1]) - (hull[-1][1] - hull[-2][1]) * (point[0] - hull[-2][0])
        ) <= 0:
            hull.pop()
        hull.append(point)
    return [(left, right) for left, right in zip(hull, hull[1:]) if left[0] != right[0]]


def _staffing_bound(model, problem, slots, x, owned, cap, pool) -> tuple[Any, Any]:
    """Bound the pool; return lower bounds on the staff summed over all room sessions and on the
    external session charges (every room used at a slot is at least one session there)."""
    prep, closing = problem.staffing.preparation_minutes, problem.staffing.closing_minutes
    max_staff = problem.staffing.ladder[-1].required_staff
    starting: dict[str, int | Any] = {}
    external: list[Any] = []
    for slot in problem.slots:
        rooms = [room for room in problem.rooms if room.available_slot_ids is None or slot.slot_id in room.available_slot_ids]
        load_by_area: dict[str, list[Any]] = defaultdict(list)
        for demand in problem.demands:
            if demand.requires_room and slot.slot_id in demand.candidate_slot_ids:
                load_by_area[demand.plan_area].append(demand.participant_count * x[demand.exam_demand_id, slot.slot_id])
        if not load_by_area:
            continue
        staff_terms = []
        for room in rooms:
            if room.plan_area not in load_by_area:
                continue
            occupancy = model.NewIntVar(0, cap[room.room_id], f"occ_{room.room_id}_{slot.slot_id}")
            used = model.NewBoolVar(f"used_{room.room_id}_{slot.slot_id}")
            staff = model.NewIntVar(0, max_staff, f"staff_{room.room_id}_{slot.slot_id}")
            model.Add(occupancy <= cap[room.room_id] * used)
            model.Add(occupancy >= used)
            model.Add(used <= owned[room.room_id])
            model.Add(staff >= used)
            for (x0, y0), (x1, y1) in _hull_from_one(_ladder_table(problem, cap[room.room_id])):
                rise, run = y1 - y0, x1 - x0
                model.Add(run * staff >= rise * occupancy + (run * y0 - rise * x0) * used)
            staff_terms.append((room.plan_area, occupancy, staff))
            if room.external_session_cost_ore:
                external.append(room.external_session_cost_ore * used)
        for area, load in load_by_area.items():
            model.Add(sum(occ for room_area, occ, _ in staff_terms if room_area == area) == sum(load))
        starting[slot.slot_id] = sum(staff for _, _, staff in staff_terms)
    for slot in problem.slots:
        checkpoint = slot.start_minute - prep
        for area in {demand.plan_area for demand in problem.demands}:
            capmax = max((cap[room.room_id] for room in problem.rooms if room.plan_area == area), default=0)
            if capmax == 0:
                continue
            earlier = [
                demand.participant_count * x[demand.exam_demand_id, slot_id]
                for demand in problem.demands if demand.requires_room and demand.plan_area == area
                for slot_id in demand.candidate_slot_ids
                if slots[slot_id].scheduled_date == slot.scheduled_date
                and slots[slot_id].start_minute - prep < checkpoint < slots[slot_id].start_minute + demand.duration_minutes + closing
            ]
            if not earlier and slot.slot_id not in starting:
                continue
            sessions = model.NewIntVar(0, len(problem.demands), f"sessions_{area}_{slot.slot_id}")
            hull = model.NewIntVar(0, len(problem.demands) * max_staff, f"hull_{area}_{slot.slot_id}")
            model.Add(sessions * capmax >= sum(earlier))
            model.Add(hull >= sessions)
            capped = _capped_ladder(problem.staffing.ladder, capmax)
            for (x0, y0), (x1, y1) in staffing_cut_edges(capped):
                rise, run = y1 - y0, x1 - x0
                if run * y0 - rise * x0 >= 0:
                    model.Add(run * hull >= rise * sum(earlier) + (run * y0 - rise * x0) * sessions)
            model.Add(pool >= starting.get(slot.slot_id, 0) + hull)
    return sum(starting.values()), sum(external)


def _capped_ladder(ladder: tuple[StaffingStep, ...], capacity: int) -> tuple[StaffingStep, ...]:
    steps = []
    for step in ladder:
        steps.append(StaffingStep(min(step.max_participants, capacity), step.required_staff))
        if step.max_participants >= capacity:
            break
    return tuple(steps)


def _conflict_pairs(model, problem, slots, x) -> None:
    for index, left in enumerate(problem.demands):
        for right in problem.demands[index + 1:]:
            if not _conflicts(left, right):
                continue
            for left_id in left.candidate_slot_ids:
                for right_id in right.candidate_slot_ids:
                    if _overlap(slots[left_id], left.duration_minutes, slots[right_id], right.duration_minutes):
                        model.Add(x[left.exam_demand_id, left_id] + x[right.exam_demand_id, right_id] <= 1)


def _add_cuts(model, problem, slots, x, owned, pool, cuts: tuple[Cut, ...]) -> None:
    candidates = {demand.exam_demand_id: demand.candidate_slot_ids for demand in problem.demands}
    for kind, days, exams, rooms, value in cuts:
        outside = [
            1 - sum(x[exam, slot_id] for slot_id in candidates[exam] if slots[slot_id].scheduled_date in days)
            for exam in sorted(exams)
        ]
        extra = [owned[room.room_id] for room in problem.rooms if room.room_id not in rooms]
        if kind == "rooms":
            model.Add(sum(outside) + sum(extra) >= 1)
        else:
            model.Add(pool >= value - value * (sum(outside) + sum(extra)))
