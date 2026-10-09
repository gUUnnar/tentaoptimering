"""Keep editable integrated-scenario controls and reported assumptions coherent."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def synchronize_integrated_scenario(content: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Derive traceability text from the values that actually drive the term engine."""
    if "calendar" not in content:
        return deepcopy(content)
    result = deepcopy(content)
    calendar = _table(result, "calendar")
    staffing = _table(result, "staffing")
    costs = _table(result, "costs")
    compatibility = _table(result, "compatibility")
    conflicts = result.get("conflicts", {})
    if not isinstance(conflicts, dict):
        raise ValueError("[conflicts] måste vara en tabell.")
    _synchronize_period_bounds(calendar, previous.get("calendar") if previous else None)
    passes = calendar.get("passes", [])
    pass_text = ", ".join(
        f"{item.get('pass_id')} {item.get('start_time')}-{item.get('latest_end_time')}"
        for item in passes if isinstance(item, dict)
    )
    values = {
        "term_calendar_window": (
            f"{calendar.get('start_date')} through {calendar.get('end_date')}; "
            f"ISO weekdays {calendar.get('allowed_weekdays')}; {pass_text}"
        ),
        "room_turnaround": str(calendar.get("turnaround_minutes")),
        "aggregate_staffing": str(staffing.get("staff_per_room_session")),
        "individual_staffing_rules": _staffing_text(staffing),
        "annual_staff_cost": str(staffing.get("annual_cost_ore_per_staff")),
        "annual_room_cost": str(costs.get("annual_room_cost_ore_per_seat")),
        "digital_compatibility": str(compatibility.get("digital_compatibility_mode")),
        "course_program_conflicts": (
            f"{conflicts.get('policy', 'not_configured')}; "
            f"program relations {conflicts.get('program_relation_data_status', 'not_configured')}"
        ),
    }
    for assumption in result.get("assumption", []):
        if isinstance(assumption, dict) and assumption.get("id") in values:
            assumption["value"] = values[str(assumption["id"])]
    return result


def _synchronize_period_bounds(calendar: dict[str, Any], previous: object) -> None:
    periods = calendar.get("period", [])
    if not isinstance(periods, list):
        return
    old = previous if isinstance(previous, dict) else {}
    old_start, old_end = old.get("start_date"), old.get("end_date")
    term_start, term_end = calendar.get("start_date"), calendar.get("end_date")
    for period in periods:
        if not isinstance(period, dict):
            continue
        if old_start and period.get("start_date") == old_start:
            period["start_date"] = term_start
        if old_end and period.get("end_date") == old_end:
            period["end_date"] = term_end
        # A period cannot silently remain outside the term when an editor has
        # shortened the enclosing window.  Preserve an explicitly narrower
        # period where possible, but constrain it to the new term boundaries.
        if term_start and period.get("start_date") and period["start_date"] < term_start:
            period["start_date"] = term_start
        if term_end and period.get("end_date") and period["end_date"] > term_end:
            period["end_date"] = term_end
        if period.get("start_date") and period.get("end_date") and period["start_date"] > period["end_date"]:
            raise ValueError("En kalenderperiod kan inte sluta före den börjar.")


def _staffing_text(staffing: dict[str, Any]) -> str:
    ladder = staffing.get("ladder", [])
    steps = "/".join(
        f"{item.get('staff_required')} at {item.get('up_to_participants')}"
        for item in ladder if isinstance(item, dict)
    )
    shifts = ", ".join(
        f"{item.get('shift_id')} {item.get('start_time')}-{item.get('end_time')}"
        for item in staffing.get("shift", []) if isinstance(item, dict)
    )
    return (
        f"ladder {steps}; shifts {shifts}; preparation {staffing.get('preparation_minutes')} min; "
        f"closing {staffing.get('closing_minutes')} min; break {staffing.get('minimum_break_minutes')} min; "
        f"continuous {staffing.get('maximum_continuous_minutes')} min; daily {staffing.get('maximum_daily_minutes')} min; "
        f"rest {staffing.get('minimum_daily_rest_minutes')} min; travel {staffing.get('travel_minutes_between_buildings')} min"
    )


def _table(content: dict[str, Any], key: str) -> dict[str, Any]:
    value = content.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Scenariot saknar [{key}].")
    return value
