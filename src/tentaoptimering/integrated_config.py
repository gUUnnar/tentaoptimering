"""Versioned assumptions for the exploratory whole-term scenario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import tomllib

from .term_calendar import CalendarPass, CalendarPeriod, TermCalendar


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
    return IntegratedTermScenario(
        scenario_id=_text(payload, "scenario_id"),
        description=_text(payload, "description"),
        calendar=calendar,
        room_cost_ore_per_seat=_non_negative_int(costs, "annual_room_cost_ore_per_seat"),
        staff_per_room_session=_positive_int(staffing, "staff_per_room_session"),
        annual_staff_cost_ore_per_staff=_non_negative_int(staffing, "annual_cost_ore_per_staff"),
        digital_compatibility_mode=_text(_table(payload, "compatibility"), "digital_compatibility_mode"),
        conflict_policy=_text(_table(payload, "conflicts"), "policy"),
        program_conflict_data_status=_text(_table(payload, "conflicts"), "program_relation_data_status"),
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
