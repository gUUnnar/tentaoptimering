"""Whole-facility hires (a `HireWindow`): one cost for a period, incurred if any of the facility's rooms is used in it.

Fyrishov must be hired in full, so using one hall fewer does not lower the price, while avoiding the whole hire period does.
The window's cost is booked with the external hire cost (`external_room_session_cost_kr`) so that every cost component,
comparison and explanation keeps its meaning; the per-window detail is available through `active_windows`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING, Any, Iterable

from .joint_contract import HireWindow, JointOptimizationInput
from .money import ksum, to_units

if TYPE_CHECKING:
    from ortools.sat.python import cp_model


def add_hire_windows(model: cp_model.CpModel, problem: JointOptimizationInput, sessions: dict[tuple[str, str], Any]) -> Any:
    """Add one `hired` variable per window, force it on when a window room has a session or a fixed booking in the window,
    and return the cost (in solver units)."""
    terms: list[Any] = []
    reserved = reserved_room_days(problem)
    for window in problem.hire_windows:
        hired = model.NewBoolVar(f"hired_{window.window_id}")
        if active_windows([window], reserved):
            model.Add(hired == 1)  # a fixed booking in a hall means the facility is in use, whatever the optimised exams do
        for room_id in window.room_ids:
            for slot in problem.slots:
                if window.start <= slot.scheduled_date <= window.end and (room_id, slot.slot_id) in sessions:
                    model.Add(sessions[room_id, slot.slot_id] <= hired)
        terms.append(to_units(window.cost_kr) * hired)
    return sum(terms) if terms else 0


def hire_owner_id(window: HireWindow) -> str:
    """The id under which the decomposed strategy keeps a hire window in its portfolio, next to the room ids (a window is owned or not)."""
    return f"hire:{window.window_id}"


def portfolio_rooms(problem: JointOptimizationInput, owned: Iterable[str]) -> tuple[Any, ...]:
    """The rooms of a portfolio (room ids and hired windows in `owned`) as the day checks use them.

    A hall of a hire window that the portfolio does not hire is not available on the days of that window; the same hall in a
    window that is hired stays available. Rooms outside any window are untouched.
    """
    owned = set(owned)
    unhired = [window for window in problem.hire_windows if hire_owner_id(window) not in owned]
    slots = {slot.slot_id: slot.scheduled_date for slot in problem.slots}
    result = []
    for room in problem.rooms:
        if room.room_id not in owned:
            continue
        closed = [window for window in unhired if room.room_id in window.room_ids]
        if closed:
            available = room.available_slot_ids if room.available_slot_ids is not None else tuple(slots)  # None means every slot
            allowed = tuple(slot_id for slot_id in available if not any(window.start <= slots[slot_id] <= window.end for window in closed))
            room = replace(room, available_slot_ids=allowed)
        result.append(room)
    return tuple(result)


def reserved_room_days(problem: JointOptimizationInput) -> list[tuple[str, date]]:
    """The room-days that fixed bookings (reservations) use; a hired facility is in use through them too."""
    return [(item.room_id, item.scheduled_date) for item in problem.reservations]


def active_windows(windows: Iterable[HireWindow], used: Iterable[tuple[str, date]]) -> list[HireWindow]:
    """The windows in which at least one of the room-days is used."""
    room_days = set(used)
    return [
        window for window in windows
        if any(room_id in window.room_ids and window.start <= day <= window.end for room_id, day in room_days)
    ]


def hire_cost(windows: Iterable[HireWindow], used: Iterable[tuple[str, date]]) -> float:
    return ksum(window.cost_kr for window in active_windows(windows, used))
