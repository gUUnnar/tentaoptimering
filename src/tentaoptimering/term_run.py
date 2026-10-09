"""Reproducible constructive first run for a whole exploratory term."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import combinations
from time import perf_counter
from typing import Any

from .integrated_config import IntegratedTermScenario
from .integrated_inputs import TermModelInputs
from .integrated_term import AggregateStaffing, IntegratedDemand, IntegratedRoom
from .term_calendar import CalendarSlot, eligible_slots
from .term_rules import demands_conflict, room_is_compatible, slots_overlap
from .staffing import StaffingPlan, StaffingTask, plan_staffing, required_staff


@dataclass(frozen=True)
class TermRunResult:
    status: str
    method: str
    elapsed_seconds: float
    objective_ore: int | None
    annual_room_cost_ore: int | None
    annual_staff_cost_ore: int | None
    annual_travel_cost_ore: int | None
    staff_pool_size: int | None
    staff_work_minutes: int | None
    staff_travel_minutes: int | None
    staff_idle_minutes: int | None
    optimality_gap: str
    assignments: tuple[dict[str, Any], ...]
    room_sessions: tuple[dict[str, Any], ...]
    staff_assignments: tuple[dict[str, Any], ...]
    model_completeness: dict[str, object]


def run_first_term_schedule(inputs: TermModelInputs, scenario: IntegratedTermScenario) -> TermRunResult:
    """Find the cheapest complete schedule among deterministic greedy portfolio trials.

    This is intentionally a constructive scale run, not an optimal CP-SAT proof.  It
    evaluates room and aggregate staffing cost together and makes every placement
    traceable, while avoiding the unbounded demand×room×date CP-SAT cross product.
    """
    started = perf_counter()
    staffing = AggregateStaffing(
        scenario.staff_per_room_session, scenario.annual_staff_cost_ore_per_staff
    )
    slots_by_demand = {
        item.exam_demand_id: eligible_slots(
            scenario.calendar, item.duration_minutes, item.allowed_pass_ids
        )
        for item in inputs.demands
    }
    relevant_rooms = tuple(
        room for room in inputs.rooms if room.plan_area in {item.plan_area for item in inputs.demands}
    )
    best: tuple[int, tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[IntegratedRoom, ...], StaffingPlan] | None = None
    for portfolio in _portfolios(relevant_rooms, inputs.demands):
        scheduled = _schedule_portfolio(inputs.demands, portfolio, scenario, slots_by_demand)
        if scheduled is None:
            continue
        assignments, sessions, staff_plan = scheduled
        used_rooms = {row["room_id"] for row in assignments}
        room_cost = sum(room.annual_cost_ore for room in portfolio if room.room_id in used_rooms)
        travel_cost = staff_plan.travel_minutes * scenario.travel_cost_ore_per_minute
        objective = room_cost + staffing.annual_cost_ore_per_staff * staff_plan.worker_count + travel_cost
        candidate = (objective, assignments, sessions, portfolio, staff_plan)
        if best is None or _candidate_key(candidate) < _candidate_key(best):
            best = candidate
    elapsed = perf_counter() - started
    completeness = _completeness(inputs, 0 if best is None else len({row["exam_demand_id"] for row in best[1]}))
    if best is None:
        return TermRunResult(
            "no_constructive_full_solution", "portfolio_enumeration_balanced_greedy", elapsed,
            None, None, None, None, None, None, None, None, "not_available_constructive_method", (), (), (), completeness,
        )
    objective, assignments, sessions, portfolio, staff_plan = best
    used_rooms = {row["room_id"] for row in assignments}
    room_cost = sum(room.annual_cost_ore for room in portfolio if room.room_id in used_rooms)
    staff_cost = staffing.annual_cost_ore_per_staff * staff_plan.worker_count
    travel_cost = staff_plan.travel_minutes * scenario.travel_cost_ore_per_minute
    return TermRunResult(
        "constructive_feasible", "portfolio_enumeration_balanced_greedy_with_staffing", elapsed,
        objective, room_cost, staff_cost, travel_cost, staff_plan.worker_count,
        staff_plan.work_minutes, staff_plan.travel_minutes, staff_plan.idle_minutes,
        "not_available_constructive_method", assignments, sessions, staff_plan.assignments, completeness,
    )


def _portfolios(rooms: tuple[IntegratedRoom, ...], demands: tuple[IntegratedDemand, ...]):
    required_areas = {item.plan_area for item in demands}
    for size in range(1, len(rooms) + 1):
        for portfolio in combinations(rooms, size):
            if required_areas.issubset({item.plan_area for item in portfolio}):
                yield portfolio


def _schedule_portfolio(
    demands: tuple[IntegratedDemand, ...], portfolio: tuple[IntegratedRoom, ...], scenario: IntegratedTermScenario,
    slots_by_demand: dict[str, tuple[CalendarSlot, ...]],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], StaffingPlan] | None:
    remaining = {
        (slot.slot_id, room.room_id): room.capacity
        for values in slots_by_demand.values() for slot in values for room in portfolio
    }
    loads = {slot_id: 0 for slot_id, _room_id in remaining}
    chosen: list[dict[str, Any]] = []
    by_id = {item.exam_demand_id: item for item in demands}
    placed_slots: dict[str, CalendarSlot] = {}
    for demand in sorted(demands, key=lambda item: (-item.participants, item.exam_demand_id)):
        compatible = [room for room in portfolio if room.plan_area == demand.plan_area]
        allocation = None
        for slot in sorted(slots_by_demand[demand.exam_demand_id], key=lambda item: (loads[item.slot_id], item.slot_id)):
            if any(
                demands_conflict(demand, other)
                and slots_overlap(slot, demand.duration_minutes, placed_slots[other.exam_demand_id], other.duration_minutes)
                for other in demands if other.exam_demand_id in placed_slots
            ):
                continue
            compatible_at_slot = [room for room in compatible if room_is_compatible(demand, room, slot)]
            free = sum(remaining.get((slot.slot_id, room.room_id), 0) for room in compatible_at_slot)
            if free < demand.participants:
                continue
            left = demand.participants
            rows: list[dict[str, Any]] = []
            for room in sorted(compatible_at_slot, key=lambda item: (-remaining[(slot.slot_id, item.room_id)], item.room_id)):
                seats = min(left, remaining[(slot.slot_id, room.room_id)])
                if seats:
                    rows.append({
                        "exam_demand_id": demand.exam_demand_id, "slot_id": slot.slot_id,
                        "scheduled_date": slot.scheduled_date.isoformat(), "pass_id": slot.pass_id,
                        "room_id": room.room_id, "participants": seats,
                    })
                    left -= seats
                if left == 0:
                    break
            allocation = slot, rows
            break
        if allocation is None:
            return None
        slot, rows = allocation
        for row in rows:
            remaining[slot.slot_id, row["room_id"]] -= int(row["participants"])
        loads[slot.slot_id] += demand.participants
        placed_slots[demand.exam_demand_id] = slot
        chosen.extend(rows)
    sessions = _sessions(chosen, by_id, scenario, slots_by_demand)
    plan = plan_staffing(_staffing_tasks(sessions, chosen, portfolio, by_id, scenario), scenario.staffing_policy)
    return (tuple(chosen), sessions, plan) if plan.feasible else None


def _sessions(
    rows: list[dict[str, Any]], demands: dict[str, IntegratedDemand], scenario: IntegratedTermScenario,
    slots_by_demand: dict[str, tuple[CalendarSlot, ...]],
) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["room_id"]), str(row["slot_id"])), []).append(row)
    result = []
    for (room_id, slot_id), members in sorted(grouped.items()):
        first = members[0]
        durations = [demands[str(row["exam_demand_id"])].duration_minutes for row in members]
        slot = next(
            item for item in slots_by_demand[str(first["exam_demand_id"])]
            if item.slot_id == slot_id
        )
        result.append({
            "room_id": room_id, "slot_id": slot_id, "scheduled_date": first["scheduled_date"],
            "pass_id": first["pass_id"], "start_minute": slot.start_minute,
            "exam_demand_ids": tuple(sorted({str(row["exam_demand_id"]) for row in members})),
            "available_again_minute": slot.start_minute + max(durations) + scenario.calendar.turnaround_minutes,
        })
    return tuple(result)


def _peak_sessions(sessions: tuple[dict[str, Any], ...], scenario: IntegratedTermScenario) -> int:
    # A session is active from the configured pass start until its last exam ends plus turnaround.
    intervals = []
    for session in sessions:
        intervals.append((
            str(session["scheduled_date"]), int(session["start_minute"]),
            int(session["available_again_minute"]),
        ))
    return max(
        sum(day == other_day and begin < other_end and other_begin < end for other_day, other_begin, other_end in intervals)
        for day, begin, end in intervals
    ) if intervals else 0


def _staffing_tasks(
    sessions: tuple[dict[str, Any], ...], assignments: list[dict[str, Any]],
    rooms: tuple[IntegratedRoom, ...], demands: dict[str, IntegratedDemand], scenario: IntegratedTermScenario,
) -> tuple[StaffingTask, ...]:
    room_by_id = {item.room_id: item for item in rooms}
    counts: dict[tuple[str, str], int] = {}
    for row in assignments:
        key = str(row["room_id"]), str(row["slot_id"])
        counts[key] = counts.get(key, 0) + int(row["participants"])
    result = []
    for session in sessions:
        room_id, slot_id = str(session["room_id"]), str(session["slot_id"])
        participants = counts[room_id, slot_id]
        room = room_by_id[room_id]
        result.append(StaffingTask(
            f"{room_id}|{slot_id}", date.fromisoformat(str(session["scheduled_date"])),
            int(session["start_minute"]), max(
                int(session["available_again_minute"]),
                int(session["start_minute"]) + max(
                    demands[str(item)].duration_minutes for item in session["exam_demand_ids"]
                ) + scenario.staffing_policy.closing_minutes,
            ),
            room.building_id or room.room_id, participants, required_staff(participants, scenario.staffing_policy),
        ))
    return tuple(result)


def _completeness(inputs: TermModelInputs, placed_demands: int) -> dict[str, object]:
    metrics = inputs.scope_metrics
    included = metrics["included_source_activities"]
    total = metrics["source_activities_total"]
    return {
        "included_demand_coverage": placed_demands / included if included else 0.0,
        "placed_exam_demands": placed_demands,
        "included_source_activities": included,
        "source_activities_total": total,
        "source_population_coverage": placed_demands / total if total else 0.0,
        "unresolved_source_activities": metrics["unresolved_source_activities"],
        "interpretation": "Full placeringsgrad avser endast preliminärt inkluderad efterfrågan, inte hela källpopulationen.",
    }


def _candidate_key(candidate: tuple[Any, ...]) -> tuple[int, int, tuple[str, ...]]:
    objective, _assignments, _sessions, portfolio, staff_plan = candidate
    return int(objective), int(staff_plan.worker_count), tuple(item.room_id for item in portfolio)
