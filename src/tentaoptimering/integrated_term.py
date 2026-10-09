"""First whole-term CP-SAT model with hard demand coverage and aggregate staffing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model

from .term_calendar import CalendarSlot, TermCalendar, eligible_slots
from .term_rules import demands_conflict, room_is_compatible, slots_overlap


@dataclass(frozen=True)
class IntegratedDemand:
    exam_demand_id: str
    participants: int
    duration_minutes: int
    plan_area: str
    allowed_pass_ids: frozenset[str] | None = None
    course_code: str | None = None
    program_ids: frozenset[str] = frozenset()
    digital_requirement: str = "unknown"


@dataclass(frozen=True)
class IntegratedRoom:
    room_id: str
    capacity: int
    plan_area: str
    annual_cost_ore: int
    building_id: str | None = None
    digital_capabilities: frozenset[str] = frozenset({"unknown"})
    available_slot_ids: frozenset[str] | None = None


@dataclass(frozen=True)
class AggregateStaffing:
    staff_per_room_session: int
    annual_cost_ore_per_staff: int


@dataclass(frozen=True)
class IntegratedTermResult:
    status: str
    objective_ore: int | None
    annual_room_cost_ore: int | None
    annual_staff_cost_ore: int | None
    staff_pool_size: int | None
    assignments: tuple[dict[str, Any], ...]
    room_sessions: tuple[dict[str, Any], ...]


def solve_integrated_term(
    demands: tuple[IntegratedDemand, ...],
    rooms: tuple[IntegratedRoom, ...],
    calendar: TermCalendar,
    staffing: AggregateStaffing,
    max_time_seconds: float = 60.0,
    max_calendar_slots_per_demand: int | None = None,
) -> IntegratedTermResult:
    """Find a complete term schedule or return an explicit infeasible status.

    The staffing pool is an anonymous concurrent capacity. Individual assignments,
    travel and rest rules are deliberately a later layer; the pool is nevertheless
    chosen jointly with rooms, dates and sessions in this model.
    """
    _validate(demands, rooms, staffing, max_time_seconds)
    candidates = {
        demand.exam_demand_id: _reduce_slots(
            eligible_slots(calendar, demand.duration_minutes, demand.allowed_pass_ids),
            max_calendar_slots_per_demand,
        )
        for demand in demands
    }
    if any(not values for values in candidates.values()):
        return IntegratedTermResult("infeasible_no_eligible_calendar_slot", None, None, None, None, (), ())
    model = cp_model.CpModel()
    start: dict[tuple[str, str], cp_model.IntVar] = {}
    seats: dict[tuple[str, str, str], cp_model.IntVar] = {}
    use: dict[tuple[str, str, str], cp_model.IntVar] = {}
    sessions: dict[tuple[str, str], cp_model.IntVar] = {}
    owned = {room.room_id: model.NewBoolVar(f"portfolio_{room.room_id}") for room in rooms}
    slots = {slot.slot_id: slot for values in candidates.values() for slot in values}
    for room in rooms:
        for slot_id in slots:
            sessions[room.room_id, slot_id] = model.NewBoolVar(f"session_{room.room_id}_{slot_id}")
    for demand in demands:
        choices: list[cp_model.IntVar] = []
        compatible_rooms = [room for room in rooms if room.plan_area == demand.plan_area]
        if not compatible_rooms:
            return IntegratedTermResult("infeasible_no_room_in_plan_area", None, None, None, None, (), ())
        for slot in candidates[demand.exam_demand_id]:
            selected = model.NewBoolVar(f"start_{demand.exam_demand_id}_{slot.slot_id}")
            start[demand.exam_demand_id, slot.slot_id] = selected
            choices.append(selected)
            allocations: list[cp_model.IntVar] = []
            slot_rooms = [room for room in compatible_rooms if room_is_compatible(demand, room, slot)]
            if not slot_rooms:
                model.Add(selected == 0)
            for room in slot_rooms:
                used = model.NewBoolVar(f"use_{demand.exam_demand_id}_{slot.slot_id}_{room.room_id}")
                allocated = model.NewIntVar(0, min(demand.participants, room.capacity), f"seats_{demand.exam_demand_id}_{slot.slot_id}_{room.room_id}")
                use[demand.exam_demand_id, slot.slot_id, room.room_id] = used
                seats[demand.exam_demand_id, slot.slot_id, room.room_id] = allocated
                model.Add(allocated >= used)
                model.Add(allocated <= room.capacity * used)
                model.Add(used <= selected)
                model.Add(used <= sessions[room.room_id, slot.slot_id])
                allocations.append(allocated)
            model.Add(sum(allocations) == demand.participants * selected)
        model.Add(sum(choices) == 1)
    for index, left_demand in enumerate(demands):
        for right_demand in demands[index + 1:]:
            if not demands_conflict(left_demand, right_demand):
                continue
            for left_slot in candidates[left_demand.exam_demand_id]:
                for right_slot in candidates[right_demand.exam_demand_id]:
                    if slots_overlap(left_slot, left_demand.duration_minutes, right_slot, right_demand.duration_minutes):
                        model.Add(
                            start[left_demand.exam_demand_id, left_slot.slot_id]
                            + start[right_demand.exam_demand_id, right_slot.slot_id]
                            <= 1
                        )
    for room in rooms:
        room_sessions = [sessions[room.room_id, slot_id] for slot_id in slots]
        model.Add(owned[room.room_id] <= sum(room_sessions))
        for slot_id in slots:
            members = [key for key in use if key[1] == slot_id and key[2] == room.room_id]
            if not members:
                model.Add(sessions[room.room_id, slot_id] == 0)
                continue
            model.Add(sum(use[key] for key in members) <= len(members) * sessions[room.room_id, slot_id])
            model.Add(sessions[room.room_id, slot_id] <= sum(use[key] for key in members))
            model.Add(sum(seats[key] for key in members) <= room.capacity)
            model.Add(sessions[room.room_id, slot_id] <= owned[room.room_id])
        for left_id, left in slots.items():
            for right_id, right in slots.items():
                if left_id >= right_id or left.scheduled_date != right.scheduled_date:
                    continue
                left_end = left.latest_end_minute + calendar.turnaround_minutes
                right_end = right.latest_end_minute + calendar.turnaround_minutes
                if left.start_minute < right_end and right.start_minute < left_end:
                    model.Add(sessions[room.room_id, left_id] + sessions[room.room_id, right_id] <= 1)
    staff_pool = model.NewIntVar(0, len(rooms) * staffing.staff_per_room_session, "staff_pool")
    for left in slots.values():
        overlapping = [
            slot for slot in slots.values()
            if slot.scheduled_date == left.scheduled_date
            and slot.start_minute < left.latest_end_minute + calendar.turnaround_minutes
            and left.start_minute < slot.latest_end_minute + calendar.turnaround_minutes
        ]
        model.Add(
            sum(sessions[room.room_id, slot.slot_id] for room in rooms for slot in overlapping)
            * staffing.staff_per_room_session <= staff_pool
        )
    room_cost = sum(room.annual_cost_ore * owned[room.room_id] for room in rooms)
    staff_cost = staffing.annual_cost_ore_per_staff * staff_pool
    model.Minimize(room_cost + staff_cost)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return IntegratedTermResult(solver.StatusName(status).lower(), None, None, None, None, (), ())
    assignments, room_sessions = _extract_solution(solver, demands, rooms, calendar, candidates, start, seats)
    return IntegratedTermResult(
        solver.StatusName(status).lower(), int(solver.ObjectiveValue()), int(solver.Value(room_cost)),
        int(solver.Value(staff_cost)), int(solver.Value(staff_pool)), assignments, room_sessions,
    )


def _extract_solution(
    solver: cp_model.CpSolver, demands: tuple[IntegratedDemand, ...], rooms: tuple[IntegratedRoom, ...],
    calendar: TermCalendar, candidates: dict[str, tuple[CalendarSlot, ...]],
    start: dict[tuple[str, str], cp_model.IntVar], seats: dict[tuple[str, str, str], cp_model.IntVar],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[IntegratedDemand]] = {}
    for demand in demands:
        slot = next(slot for slot in candidates[demand.exam_demand_id] if solver.Value(start[demand.exam_demand_id, slot.slot_id]))
        for room in rooms:
            key = demand.exam_demand_id, slot.slot_id, room.room_id
            if key not in seats or not solver.Value(seats[key]):
                continue
            rows.append({"exam_demand_id": demand.exam_demand_id, "slot_id": slot.slot_id, "room_id": room.room_id, "participants": solver.Value(seats[key])})
            grouped.setdefault((room.room_id, slot.slot_id), []).append(demand)
    sessions = []
    for (room_id, slot_id), members in grouped.items():
        slot = next(slot for values in candidates.values() for slot in values if slot.slot_id == slot_id)
        sessions.append({"room_id": room_id, "slot_id": slot_id, "exam_demand_ids": tuple(item.exam_demand_id for item in members), "available_again_minute": slot.start_minute + max(item.duration_minutes for item in members) + calendar.turnaround_minutes})
    return tuple(rows), tuple(sessions)


def _validate(demands: tuple[IntegratedDemand, ...], rooms: tuple[IntegratedRoom, ...], staffing: AggregateStaffing, max_time_seconds: float) -> None:
    if not demands or not rooms or staffing.staff_per_room_session <= 0 or staffing.annual_cost_ore_per_staff < 0 or max_time_seconds <= 0:
        raise ValueError("Terminsmodellen kräver behov, rum, giltig bemanning och positiv tidsgräns.")
    if len({item.exam_demand_id for item in demands}) != len(demands) or len({item.room_id for item in rooms}) != len(rooms):
        raise ValueError("Tentamens- och rumsidentifierare måste vara unika.")
    if any(item.participants <= 0 or item.duration_minutes <= 0 for item in demands):
        raise ValueError("Varje tentamensbehov måste ha positiv deltagarvolym och längd.")
    if any(item.capacity <= 0 or item.annual_cost_ore < 0 for item in rooms):
        raise ValueError("Varje sal måste ha positiv kapacitet och icke-negativ årskostnad.")


def _reduce_slots(slots: tuple[CalendarSlot, ...], maximum: int | None) -> tuple[CalendarSlot, ...]:
    """Choose evenly spread reproducible candidates when the full cross-product is too large."""
    if maximum is None or len(slots) <= maximum:
        return slots
    if maximum <= 0:
        raise ValueError("max_calendar_slots_per_demand måste vara positivt när det anges.")
    if maximum == 1:
        return (slots[0],)
    indexes = {round(index * (len(slots) - 1) / (maximum - 1)) for index in range(maximum)}
    return tuple(slot for index, slot in enumerate(slots) if index in indexes)
