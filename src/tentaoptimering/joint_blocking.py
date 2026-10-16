"""Fixed bookings (reservations) as constraints of the joint model: a reserved room is busy, and in use, for the booking.

A reservation occupies its room from the booked start to the booked end; a room session must end at least the turnaround
before it starts, or start at least the turnaround after it ends, exactly as two sessions in a room. A room that has a
reservation is in use whatever the optimised exams do, so it is owned (and costs) even if no optimised session sits there.
"""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from .joint_contract import JointOptimizationInput


def reserved_rooms(problem: JointOptimizationInput) -> frozenset[str]:
    """Rooms of the problem that some reservation uses (a reservation of a room the problem does not have is ignored)."""
    known = {room.room_id for room in problem.rooms}
    return frozenset(item.room_id for item in problem.reservations if item.room_id in known)


def apply_reservations(model: cp_model.CpModel, problem: JointOptimizationInput, sessions: dict[Any, Any], session_end: dict[Any, Any], owned: dict[str, Any]) -> None:
    known = {room.room_id for room in problem.rooms}
    turnaround = problem.turnaround_minutes
    for item in problem.reservations:
        if item.room_id not in known:
            continue
        for slot in problem.slots:
            if slot.scheduled_date != item.scheduled_date:
                continue
            key = item.room_id, slot.slot_id
            if slot.start_minute >= item.end_minute + turnaround:
                continue  # the session starts after the booking has ended and the room is turned around
            if slot.start_minute < item.start_minute:
                model.Add(session_end[key] + turnaround <= item.start_minute).OnlyEnforceIf(sessions[key])
            else:
                model.Add(sessions[key] == 0)  # the session would start while the room is booked
    for room_id in reserved_rooms(problem):
        model.Add(owned[room_id] == 1)
