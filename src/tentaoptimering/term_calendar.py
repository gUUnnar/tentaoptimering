"""Scenario-driven term calendars for the integrated optimization model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class CalendarPass:
    pass_id: str
    start_time: str
    latest_end_time: str


@dataclass(frozen=True)
class TermCalendar:
    start_date: date
    end_date: date
    allowed_weekdays: tuple[int, ...]
    passes: tuple[CalendarPass, ...]
    turnaround_minutes: int


@dataclass(frozen=True)
class CalendarSlot:
    slot_id: str
    scheduled_date: date
    pass_id: str
    start_minute: int
    latest_end_minute: int


def clock_minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"Klockslag måste anges som HH:MM: {value}") from error
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"Klockslag ligger utanför dygnet: {value}")
    return hour * 60 + minute


def generate_calendar_slots(calendar: TermCalendar) -> tuple[CalendarSlot, ...]:
    """Generate only business-approved date/pass combinations."""
    _validate_calendar(calendar)
    slots: list[CalendarSlot] = []
    current = calendar.start_date
    while current <= calendar.end_date:
        if current.isoweekday() in calendar.allowed_weekdays:
            for exam_pass in calendar.passes:
                slots.append(
                    CalendarSlot(
                        slot_id=f"{current.isoformat()}-{exam_pass.pass_id}",
                        scheduled_date=current,
                        pass_id=exam_pass.pass_id,
                        start_minute=clock_minutes(exam_pass.start_time),
                        latest_end_minute=clock_minutes(exam_pass.latest_end_time),
                    )
                )
        current += timedelta(days=1)
    return tuple(slots)


def eligible_slots(
    calendar: TermCalendar, duration_minutes: int, allowed_pass_ids: set[str] | None = None
) -> tuple[CalendarSlot, ...]:
    """Return slots that can hold an exam duration without implicit time flexibility."""
    if duration_minutes <= 0:
        raise ValueError("Tentamenslängd måste vara positiv.")
    selected = []
    for slot in generate_calendar_slots(calendar):
        if allowed_pass_ids is not None and slot.pass_id not in allowed_pass_ids:
            continue
        if slot.start_minute + duration_minutes <= slot.latest_end_minute:
            selected.append(slot)
    return tuple(selected)


def _validate_calendar(calendar: TermCalendar) -> None:
    if calendar.end_date < calendar.start_date:
        raise ValueError("Terminskalenderns slutdatum ligger före startdatum.")
    if not calendar.allowed_weekdays or any(day not in range(1, 8) for day in calendar.allowed_weekdays):
        raise ValueError("allowed_weekdays måste innehålla ISO-veckodagar 1–7.")
    if calendar.turnaround_minutes < 0 or not calendar.passes:
        raise ValueError("Kalendern kräver pass och icke-negativ ställtid.")
    pass_ids = [item.pass_id for item in calendar.passes]
    if len(set(pass_ids)) != len(pass_ids) or any(not value.strip() for value in pass_ids):
        raise ValueError("Passidentifierare måste vara unika och ifyllda.")
    for item in calendar.passes:
        if clock_minutes(item.start_time) >= clock_minutes(item.latest_end_time):
            raise ValueError(f"Passet {item.pass_id} slutar före eller vid sin start.")
