"""Whole-facility hires (a `HireWindow`): one cost for a period, incurred if any of the facility's rooms is used in it.

Fyrishov must be hired in full, so using one hall fewer does not lower the price, while avoiding the whole hire period does.
The window's cost is booked with the external hire cost (`external_room_session_cost_kr`) so that every cost component,
comparison and explanation keeps its meaning; the per-window detail is available through `active_windows`.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Iterable

from .joint_contract import HireWindow, JointOptimizationInput
from .money import ksum, to_units

if TYPE_CHECKING:
    from ortools.sat.python import cp_model


def add_hire_windows(model: cp_model.CpModel, problem: JointOptimizationInput, sessions: dict[tuple[str, str], Any]) -> Any:
    """Add one `hired` variable per window, force it on when a window room has a session in the window, and return the cost."""
    terms: list[Any] = []
    for window in problem.hire_windows:
        hired = model.NewBoolVar(f"hired_{window.window_id}")
        for room_id in window.room_ids:
            for slot in problem.slots:
                if window.start <= slot.scheduled_date <= window.end and (room_id, slot.slot_id) in sessions:
                    model.Add(sessions[room_id, slot.slot_id] <= hired)
        terms.append(to_units(window.cost_kr) * hired)
    return sum(terms) if terms else 0


def active_windows(windows: Iterable[HireWindow], used: Iterable[tuple[str, date]]) -> list[HireWindow]:
    """The windows in which at least one of the room-days is used."""
    room_days = set(used)
    return [
        window for window in windows
        if any(room_id in window.room_ids and window.start <= day <= window.end for room_id, day in room_days)
    ]


def hire_cost(windows: Iterable[HireWindow], used: Iterable[tuple[str, date]]) -> float:
    return ksum(window.cost_kr for window in active_windows(windows, used))
