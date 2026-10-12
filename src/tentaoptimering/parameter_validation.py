"""Validation of parameter values that a user wants to change, against the parameter catalog.

`validate_overrides` checks a mapping `{parameter id: value}` and returns every problem as
`{"id": ..., "message": ...}` with a Swedish message (an empty list means the values are acceptable). Nothing is
raised for bad values and nothing is silently corrected: a value is either accepted as given or reported.

What is checked:

* the parameter exists in the catalog;
* the engine supports it (`contract_only` parameters cannot be changed: the value would be ignored);
* the value has the type that the catalog declares for the parameter (`value_type`), and, where the limits are
  obvious, a sensible range (counts are not negative, weekdays are 1-7, clock times are HH:MM, the staffing ladder
  rises, a choice is one of the catalog's `choices`).
"""

from __future__ import annotations

from datetime import date
import math
import re
from typing import Any, Callable

from .parameter_catalog import ParameterCatalog, ParameterDefinition

_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_INT = 2_147_483_647
MAX_ORE = 100_000_000_000  # keeps cost sums far from the solver's 64-bit limit

# (lowest, highest) for numeric parameters. A parameter that is not listed gets the default limits of its type.
_LIMITS: dict[str, tuple[float | None, float | None]] = {
    "demand.variation_pct": (-99, None),
    "rooms.max_rooms_per_exam": (1, 1000),
    "solver.workers": (1, 512),
    "solver.seed": (0, MAX_INT),
    "solver.time_limit_seconds": (1, None),
    "solver.relative_gap_limit": (0, 1),
}
_PERCENT_LIMITS = (0, 100)


def validate_overrides(
    catalog: ParameterCatalog, overrides: dict[str, Any], base_values: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    """Every problem with the proposed values, as `{id, message}`. `base_values` completes cross-checks (dates, times)."""
    known = {item.parameter_id: item for item in catalog.parameters}
    errors: list[dict[str, str]] = []
    for parameter_id, value in overrides.items():
        definition = known.get(parameter_id)
        if definition is None:
            errors.append({"id": parameter_id, "message": "Okänd parameter."})
        elif definition.engine_support != "implemented":
            errors.append({"id": parameter_id, "message": "Stöds inte av motorn än, så värdet skulle ignoreras och kan därför inte ändras."})
        elif (message := check_value(definition, value)) is not None:
            errors.append({"id": parameter_id, "message": message})
    if not errors:
        errors.extend(_cross_checks(known, overrides, base_values or {}))
    return errors


def check_value(definition: ParameterDefinition, value: Any) -> str | None:
    """The problem with one value of this parameter, or None if it is acceptable."""
    checker = _CHECKERS.get(definition.value_type)
    if checker is None:
        return f"Parametertypen {definition.value_type} kan inte redigeras än."
    return checker(definition, value)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _range_message(low: float | None, high: float | None) -> str:
    if low is not None and high is not None:
        return f"mellan {low:g} och {high:g}"
    return f"minst {low:g}" if low is not None else f"högst {high:g}"


def _limits(definition: ParameterDefinition) -> tuple[float | None, float | None]:
    if definition.parameter_id in _LIMITS:
        return _LIMITS[definition.parameter_id]
    if definition.unit == "percent":
        return _PERCENT_LIMITS
    return (0, MAX_ORE) if definition.unit.startswith("ore") else (0, None)


def _in_limits(definition: ParameterDefinition, value: float) -> str | None:
    low, high = _limits(definition)
    if (low is not None and value < low) or (high is not None and value > high):
        return f"Värdet måste vara {_range_message(low, high)}."
    return None


def _integer(definition: ParameterDefinition, value: Any) -> str | None:
    if not _is_int(value):
        return "Värdet måste vara ett heltal."
    return _in_limits(definition, value)


def _number(definition: ParameterDefinition, value: Any) -> str | None:
    if not _is_number(value):
        return "Värdet måste vara ett tal."
    return _in_limits(definition, value)


def _boolean(_: ParameterDefinition, value: Any) -> str | None:
    return None if isinstance(value, bool) else "Värdet måste vara ja eller nej."


def _choice(definition: ParameterDefinition, value: Any) -> str | None:
    allowed = [choice for choice, _ in definition.choices]
    if not isinstance(value, str) or value not in allowed:
        return f"Värdet måste vara ett av: {', '.join(allowed)}."
    return None


def _iso_date(value: Any, empty_allowed: bool = False) -> str | None:
    if empty_allowed and value == "":
        return None
    if not isinstance(value, str):
        return "Datum anges som text i formen ÅÅÅÅ-MM-DD."
    try:
        date.fromisoformat(value)
    except ValueError:
        return "Datumet måste vara ett giltigt datum i formen ÅÅÅÅ-MM-DD."
    return None


def _date(_: ParameterDefinition, value: Any) -> str | None:
    return _iso_date(value, empty_allowed=True)


def _clock(value: Any) -> str | None:
    if not isinstance(value, str) or not _CLOCK.fullmatch(value):
        return "Klockslaget måste anges som HH:MM (00:00-23:59)."
    return None


def _time(_: ParameterDefinition, value: Any) -> str | None:
    return _clock(value)


def _list_of(value: Any, non_empty: bool = True) -> str | None:
    if not isinstance(value, list):
        return "Värdet måste vara en lista."
    return "Listan får inte vara tom." if non_empty and not value else None


def _time_list(_: ParameterDefinition, value: Any) -> str | None:
    problem = _list_of(value)
    if problem:
        return problem
    if any(_clock(item) for item in value):
        return "Varje starttid måste anges som HH:MM (00:00-23:59)."
    return "Samma klockslag får bara förekomma en gång." if len(set(value)) != len(value) else None


def _integer_list(definition: ParameterDefinition, value: Any) -> str | None:
    problem = _list_of(value)
    if problem:
        return problem
    if not all(_is_int(item) for item in value):
        return "Alla värden måste vara heltal."
    if definition.parameter_id == "calendar.weekdays" and any(item < 1 or item > 7 for item in value):
        return "Veckodagar anges som 1-7 (1 = måndag, 7 = söndag)."
    return "Samma värde får bara förekomma en gång." if len(set(value)) != len(value) else None


def _string_list(_: ParameterDefinition, value: Any) -> str | None:
    problem = _list_of(value, non_empty=False)
    if problem:
        return problem
    return None if all(isinstance(item, str) and item.strip() for item in value) else "Alla värden måste vara icke-tom text."


def _date_range_list(_: ParameterDefinition, value: Any) -> str | None:
    problem = _list_of(value, non_empty=False)
    if problem:
        return problem
    for item in value:
        if not isinstance(item, dict) or set(item) != {"start", "end"}:
            return "Varje period måste ha exakt start och end."
        if _iso_date(item["start"]) or _iso_date(item["end"]):
            return "Start och slut måste vara giltiga datum i formen ÅÅÅÅ-MM-DD."
        if item["start"] > item["end"]:
            return "En periods start får inte vara senare än dess slut."
    return None


def _time_range_list(_: ParameterDefinition, value: Any) -> str | None:
    problem = _list_of(value)
    if problem:
        return problem
    for item in value:
        if not isinstance(item, dict) or set(item) != {"start", "end"}:
            return "Varje intervall måste ha exakt start och end."
        if _clock(item["start"]) or _clock(item["end"]):
            return "Start och slut måste anges som HH:MM."
        if item["start"] >= item["end"]:
            return "Ett intervalls start måste vara före dess slut."
    return None


def _staffing_ladder(_: ParameterDefinition, value: Any) -> str | None:
    problem = _list_of(value)
    if problem:
        return problem
    previous_limit, previous_staff = 0, 0
    for step in value:
        if not isinstance(step, dict) or set(step) != {"max_participants", "required_staff"}:
            return "Varje steg måste ha exakt max_participants och required_staff."
        limit, staff = step["max_participants"], step["required_staff"]
        if not _is_int(limit) or not _is_int(staff) or limit < 1 or staff < 1:
            return "Gränser och antal vakter måste vara heltal på minst 1."
        if limit <= previous_limit:
            return "Bemanningstrappan måste stiga: varje deltagargräns ska vara högre än den förra."
        if staff < previous_staff:
            return "Bemanningstrappan får inte kräva färre vakter vid fler deltagare."
        previous_limit, previous_staff = limit, staff
    return None


def _room_integer_map(_: ParameterDefinition, value: Any) -> str | None:
    if not isinstance(value, dict):
        return "Värdet måste vara en tabell från sal till heltal."
    ok = all(isinstance(key, str) and key and _is_int(item) and item >= 1 for key, item in value.items())
    return None if ok else "Varje sal måste ha ett heltal på minst 1."


def _any_list(_: ParameterDefinition, value: Any) -> str | None:
    return _list_of(value, non_empty=False)


def _any_table(_: ParameterDefinition, value: Any) -> str | None:
    return None if isinstance(value, dict) else "Värdet måste vara en tabell."


_CHECKERS: dict[str, Callable[[ParameterDefinition, Any], str | None]] = {
    "integer": _integer, "number": _number, "boolean": _boolean, "choice": _choice, "date": _date, "time": _time,
    "time_list": _time_list, "integer_list": _integer_list, "string_list": _string_list, "room_id_list": _string_list,
    "date_range_list": _date_range_list, "time_range_list": _time_range_list, "staffing_ladder": _staffing_ladder,
    "room_integer_map": _room_integer_map, "room_list": _any_list, "rule_set": _any_list, "cost_component_set": _any_list,
    "matrix": _any_table, "weight_map": _any_table,
}

_PAIRS = (
    ("calendar.start_date", "calendar.end_date", "Första tillåtna datum får inte vara senare än sista tillåtna datum.", True),
    ("calendar.earliest_start_time", "calendar.latest_end_time", "Tidigaste starttid måste vara före senaste sluttid.", False),
)


def _cross_checks(known: dict[str, ParameterDefinition], overrides: dict[str, Any], base_values: dict[str, Any]) -> list[dict[str, str]]:
    """Pairs of parameters that must agree; both sides are the proposed value or else the scenario's or the default."""
    errors = []
    for low_id, high_id, message, skip_empty in _PAIRS:
        if low_id not in overrides and high_id not in overrides:
            continue
        values = [overrides.get(key, base_values.get(key, known[key].default if key in known else None)) for key in (low_id, high_id)]
        if skip_empty and (not values[0] or not values[1]):
            continue
        if isinstance(values[0], str) and isinstance(values[1], str) and (values[0] > values[1] if skip_empty else values[0] >= values[1]):
            errors.append({"id": low_id if low_id in overrides else high_id, "message": message})
    return errors
