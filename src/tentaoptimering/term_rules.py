"""Shared hard-rule predicates for both term schedulers and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .term_calendar import CalendarSlot

if TYPE_CHECKING:
    from .integrated_term import IntegratedDemand, IntegratedRoom


def room_is_compatible(
    demand: IntegratedDemand, room: IntegratedRoom, slot: CalendarSlot,
) -> bool:
    """Return whether a room may receive a demand in a specific calendar slot."""
    if demand.plan_area != room.plan_area:
        return False
    if room.available_slot_ids is not None and slot.slot_id not in room.available_slot_ids:
        return False
    requirement = demand.digital_requirement
    capabilities = room.digital_capabilities
    return requirement in {"", "unknown", "none"} or "all" in capabilities or requirement in capabilities


def demands_conflict(left: IntegratedDemand, right: IntegratedDemand) -> bool:
    """Use only explicit course/program relations; missing data creates no fiction."""
    same_course = bool(left.course_code and right.course_code and left.course_code == right.course_code)
    shared_program = bool(left.program_ids.intersection(right.program_ids))
    return same_course or shared_program


def slots_overlap(left: CalendarSlot, left_duration: int, right: CalendarSlot, right_duration: int) -> bool:
    """Exams collide when their actual writing intervals overlap on one date."""
    return (
        left.scheduled_date == right.scheduled_date
        and left.start_minute < right.start_minute + right_duration
        and right.start_minute < left.start_minute + left_duration
    )
