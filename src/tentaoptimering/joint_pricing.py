"""Price any placement – an optimised plan or the actual booking – with the rules of a saved problem.

The comparison of two alternatives needs both costed by *one* rule set. A run is priced by the optimiser; the actual
booking (A) is not an optimisation result, so it is priced here by the same rules: rent of the rooms in use (a room with a
fixed booking is in use), external charges per session, paid staff time per staff position, and the pool and per-session
staff charges. The rules come from the problem's own saved `joint_input.json`.

A *priced session* is one room at one start and end on one day with its participants and staff. A run's room sessions are
converted from the result (the slot gives the start); the actual booking's from the booked rooms and times.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from .joint_contract import JointOptimizationInput

COMPONENTS = ("annual_room_cost_ore", "external_room_session_cost_ore", "staff_paid_time_cost_ore", "annual_staff_pool_cost_ore", "staff_session_cost_ore")


@dataclass(frozen=True)
class PricedSession:
    room_id: str
    day: date
    start_minute: int
    end_minute: int
    participants: int
    staff: int
    exam_ids: tuple[str, ...] = ()

    @property
    def key(self) -> tuple[str, str, int]:
        return self.room_id, self.day.isoformat(), self.start_minute


def staff_for(problem: JointOptimizationInput, participants: int) -> int:
    """Staff required by the ladder; the top step covers anything above it, no participants need none."""
    if participants <= 0:
        return 0
    ladder = problem.staffing.ladder
    return next((step.required_staff for step in ladder if participants <= step.max_participants), ladder[-1].required_staff)


def sessions_from_result(problem: JointOptimizationInput, result: dict[str, Any]) -> list[PricedSession]:
    """The room sessions of a saved result as priced sessions (start from the slot, end from the recorded availability)."""
    slots = {slot.slot_id: slot for slot in problem.slots}
    rows = []
    for row in result.get("room_sessions", ()):
        slot = slots[row["slot_id"]]
        rows.append(PricedSession(row["room_id"], slot.scheduled_date, slot.start_minute, int(row["available_again_minute"]) - problem.turnaround_minutes,
                                  int(row["participants"]), int(row["required_staff"]), tuple(row.get("exam_demand_ids", ()))))
    return sorted(rows, key=lambda item: (item.day, item.start_minute, item.room_id))


def reprice_staff(problem: JointOptimizationInput, sessions: list[PricedSession]) -> list[PricedSession]:
    """The same sessions with the staff that this problem's ladder requires (for pricing another plan by these rules)."""
    return [PricedSession(s.room_id, s.day, s.start_minute, s.end_minute, s.participants, staff_for(problem, s.participants), s.exam_ids) for s in sessions]


def passes(problem: JointOptimizationInput, sessions: list[PricedSession]) -> list[dict[str, Any]]:
    """One paid pass per staff position: worked time, shortest-pass top-up, the room's travel minutes and the paid total."""
    rooms = {room.room_id: room for room in problem.rooms}
    prep, closing, minimum = problem.staffing.preparation_minutes, problem.staffing.closing_minutes, problem.staffing.min_paid_minutes
    rows = []
    for session in sessions:
        travel = rooms[session.room_id].travel_paid_minutes
        worked = session.end_minute - session.start_minute + prep + closing
        core = max(worked, minimum)
        for position in range(1, session.staff + 1):
            rows.append({"date": session.day.isoformat(), "room_id": session.room_id, "start_minute": session.start_minute, "position": position,
                         "worked_minutes": worked, "minimum_top_up_minutes": core - worked, "travel_minutes": travel, "paid_minutes": core + travel})
    return rows


def peak_staff(problem: JointOptimizationInput, sessions: list[PricedSession]) -> int:
    """The most staff at work at once; a session is staffed from `start - preparation` until `end + closing`."""
    prep, closing = problem.staffing.preparation_minutes, problem.staffing.closing_minutes
    by_day: dict[date, list[tuple[int, int]]] = defaultdict(list)
    for session in sessions:
        if session.staff:
            by_day[session.day] += [(session.start_minute - prep, session.staff), (session.end_minute + closing, -session.staff)]
    peak = 0
    for events in by_day.values():
        running = 0
        for _time, delta in sorted(events):  # at equal times the ends (negative) come first
            running += delta
            peak = max(peak, running)
    return peak


def reserved_rooms(problem: JointOptimizationInput) -> set[str]:
    known = {room.room_id for room in problem.rooms}
    return {item.room_id for item in problem.reservations if item.room_id in known}


def price(problem: JointOptimizationInput, sessions: list[PricedSession]) -> dict[str, int]:
    """The cost components of a placement by the problem's rules, in öre, and their total."""
    rooms = {room.room_id: room for room in problem.rooms}
    used = {s.room_id for s in sessions} | reserved_rooms(problem)
    paid = problem.staffing.paid_minute_cost_ore * sum(row["paid_minutes"] for row in passes(problem, sessions))
    parts = {
        "annual_room_cost_ore": sum(rooms[room_id].annual_fixed_cost_ore for room_id in used),
        "external_room_session_cost_ore": sum(rooms[s.room_id].external_session_cost_ore for s in sessions),
        "staff_paid_time_cost_ore": paid,
        "annual_staff_pool_cost_ore": problem.staffing.annual_cost_ore_per_staff * peak_staff(problem, sessions),
        "staff_session_cost_ore": problem.staffing.cost_ore_per_staff_session * sum(s.staff for s in sessions),
    }
    return {**parts, "comparable_total_cost_ore": sum(parts.values())}


def staffing_totals(problem: JointOptimizationInput, sessions: list[PricedSession]) -> dict[str, Any]:
    rows = passes(problem, sessions)
    per_day: dict[str, dict[str, int]] = defaultdict(lambda: {"passes": 0, "paid_minutes": 0})
    for row in rows:
        per_day[row["date"]]["passes"] += 1
        per_day[row["date"]]["paid_minutes"] += row["paid_minutes"]
    return {"passes": len(rows), "paid_minutes": sum(r["paid_minutes"] for r in rows), "worked_minutes": sum(r["worked_minutes"] for r in rows),
            "minimum_top_up_minutes": sum(r["minimum_top_up_minutes"] for r in rows), "travel_minutes": sum(r["travel_minutes"] for r in rows),
            "pool": peak_staff(problem, sessions), "per_day": dict(sorted(per_day.items()))}


def pricing_signature(problem: JointOptimizationInput) -> dict[str, Any]:
    """Everything that sets a price or a staffing rule; two problems with the same signature price a plan identically."""
    return {
        "rooms": {room.room_id: (room.annual_fixed_cost_ore, room.external_session_cost_ore, room.travel_paid_minutes) for room in problem.rooms},
        "staff": (problem.staffing.paid_minute_cost_ore, problem.staffing.min_paid_minutes, problem.staffing.annual_cost_ore_per_staff,
                  problem.staffing.cost_ore_per_staff_session, problem.staffing.preparation_minutes, problem.staffing.closing_minutes,
                  tuple((step.max_participants, step.required_staff) for step in problem.staffing.ladder)),
        "reservations": tuple(sorted(reserved_rooms(problem))),
    }
