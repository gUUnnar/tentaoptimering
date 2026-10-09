"""Versioned assumptions for the exploratory whole-term scenario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import tomllib

from .term_calendar import CalendarPass, CalendarPeriod, TermCalendar
from .staffing import StaffingPolicy, StaffingStep, WorkShift


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    value: str
    unit: str
    source: str
    rationale: str
    status: str


@dataclass(frozen=True)
class IntegratedTermScenario:
    scenario_id: str
    description: str
    calendar: TermCalendar
    room_cost_ore_per_seat: int
    staff_per_room_session: int
    annual_staff_cost_ore_per_staff: int
    digital_compatibility_mode: str
    conflict_policy: str
    program_conflict_data_status: str
    staffing_policy: StaffingPolicy
    travel_cost_ore_per_minute: int
    assumptions: tuple[Assumption, ...]


def load_integrated_term_scenario(path: Path) -> IntegratedTermScenario:
    """Load a scenario only when every configured assumption is traceable."""
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    calendar_data = _table(payload, "calendar")
    passes_data = calendar_data.get("passes")
    if not isinstance(passes_data, list) or not passes_data:
        raise ValueError("Terminscenario kräver minst ett kalenderpass.")
    calendar = TermCalendar(
        start_date=date.fromisoformat(_text(calendar_data, "start_date")),
        end_date=date.fromisoformat(_text(calendar_data, "end_date")),
        allowed_weekdays=tuple(_positive_ints(calendar_data, "allowed_weekdays")),
        passes=tuple(
            CalendarPass(_text(item, "pass_id"), _text(item, "start_time"), _text(item, "latest_end_time"))
            for item in passes_data
        ),
        turnaround_minutes=_non_negative_int(calendar_data, "turnaround_minutes"),
        periods=tuple(_calendar_period(item) for item in calendar_data.get("period", [])),
        allowed_dates=_dates(calendar_data, "allowed_dates"),
        blocked_dates=_dates(calendar_data, "blocked_dates") or (),
    )
    costs = _table(payload, "costs")
    staffing = _table(payload, "staffing")
    assumptions = tuple(
        Assumption(
            _text(item, "id"), _text(item, "value"), _text(item, "unit"),
            _text(item, "source"), _text(item, "rationale"), _text(item, "status"),
        )
        for item in payload.get("assumption", [])
    )
    if not assumptions:
        raise ValueError("Terminscenario kräver spårbara antaganden.")
    if len({item.assumption_id for item in assumptions}) != len(assumptions):
        raise ValueError("Antagandeidentifierare måste vara unika.")
    conflicts = payload.get("conflicts", {})
    if not isinstance(conflicts, dict):
        raise ValueError("Terminsscenariots [conflicts] måste vara en tabell.")
    return IntegratedTermScenario(
        scenario_id=_text(payload, "scenario_id"),
        description=_text(payload, "description"),
        calendar=calendar,
        room_cost_ore_per_seat=_non_negative_int(costs, "annual_room_cost_ore_per_seat"),
        staff_per_room_session=_positive_int(staffing, "staff_per_room_session"),
        annual_staff_cost_ore_per_staff=_non_negative_int(staffing, "annual_cost_ore_per_staff"),
        digital_compatibility_mode=_text(_table(payload, "compatibility"), "digital_compatibility_mode"),
        conflict_policy=_optional_text(conflicts, "policy", "not_configured"),
        program_conflict_data_status=_optional_text(conflicts, "program_relation_data_status", "not_configured"),
        staffing_policy=_staffing_policy(staffing),
        travel_cost_ore_per_minute=_non_negative_int(staffing, "travel_cost_ore_per_minute") if "travel_cost_ore_per_minute" in staffing else 0,
        assumptions=assumptions,
    )


def _calendar_period(payload: object) -> CalendarPeriod:
    if not isinstance(payload, dict):
        raise ValueError("Varje kalenderperiod måste vara en tabell.")
    weekdays = _positive_ints(payload, "allowed_weekdays") if "allowed_weekdays" in payload else None
    return CalendarPeriod(
        _text(payload, "period_id"), date.fromisoformat(_text(payload, "start_date")),
        date.fromisoformat(_text(payload, "end_date")), tuple(weekdays) if weekdays else None,
    )


def _dates(payload: dict[str, object], key: str) -> tuple[date, ...] | None:
    if key not in payload:
        return None
    values = payload[key]
    if not isinstance(values, list):
        raise ValueError(f"{key} måste vara en lista med ISO-datum.")
    dates = tuple(date.fromisoformat(str(value)) for value in values)
    if len(set(dates)) != len(dates):
        raise ValueError(f"{key} får inte innehålla dubbletter.")
    return dates


def _staffing_policy(payload: dict[str, object]) -> StaffingPolicy:
    """Support old exploratory files while making activated rules explicit."""
    raw_ladder = payload.get("ladder")
    ladder = (
        tuple(StaffingStep(_positive_int(item, "up_to_participants"), _positive_int(item, "staff_required")) for item in raw_ladder if isinstance(item, dict))
        if isinstance(raw_ladder, list) else (StaffingStep(10**9, _positive_int(payload, "staff_per_room_session")),)
    )
    if isinstance(raw_ladder, list) and len(ladder) != len(raw_ladder):
        raise ValueError("Bemanningstrappan måste innehålla tabeller.")
    raw_shifts = payload.get("shift")
    shifts = (
        tuple(WorkShift(_text(item, "shift_id"), _clock_minutes(_text(item, "start_time")), _clock_minutes(_text(item, "end_time"))) for item in raw_shifts if isinstance(item, dict))
        if isinstance(raw_shifts, list) else (WorkShift("legacy_day", 0, 24 * 60),)
    )
    if isinstance(raw_shifts, list) and len(shifts) != len(raw_shifts):
        raise ValueError("Arbetspassen måste innehålla tabeller.")
    return StaffingPolicy(
        ladder, shifts,
        _non_negative_int(payload, "preparation_minutes") if "preparation_minutes" in payload else 0,
        _non_negative_int(payload, "closing_minutes") if "closing_minutes" in payload else 0,
        _non_negative_int(payload, "minimum_break_minutes") if "minimum_break_minutes" in payload else 0,
        _positive_int(payload, "maximum_continuous_minutes") if "maximum_continuous_minutes" in payload else 24 * 60,
        _positive_int(payload, "maximum_daily_minutes") if "maximum_daily_minutes" in payload else 24 * 60,
        _non_negative_int(payload, "minimum_daily_rest_minutes") if "minimum_daily_rest_minutes" in payload else 0,
        _non_negative_int(payload, "travel_minutes_between_buildings") if "travel_minutes_between_buildings" in payload else 0,
    )


def _clock_minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"Klockslag måste anges som HH:MM: {value}") from error
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"Klockslag ligger utanför dygnet: {value}")
    return hour * 60 + minute


def _table(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Terminsscenario saknar tabellen [{key}].")
    return value


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Terminsscenario saknar ett ifyllt {key}.")
    return value


def _optional_text(payload: dict[str, object], key: str, default: str) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Terminsscenario har ogiltigt {key}.")
    return value


def _non_negative_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"Terminsscenario kräver ett icke-negativt heltal för {key}.")
    return value


def _positive_int(payload: dict[str, object], key: str) -> int:
    value = _non_negative_int(payload, key)
    if value == 0:
        raise ValueError(f"Terminsscenario kräver ett positivt heltal för {key}.")
    return value


def _positive_ints(payload: dict[str, object], key: str) -> list[int]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Terminsscenario kräver en icke-tom lista för {key}.")
    return [_positive_int({key: item}, key) for item in value]
