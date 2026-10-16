"""The parameter catalog as the interface shows it: a fixed, understandable order in six groups.

The catalog (`config/joint_parameter_catalog.toml`) is the single source of what a parameter is. This module only
decides how the interface lists them: which group each belongs to, in what order, and which are too technical to
show by default. A parameter that is not placed here still appears, last in the group `ovrigt`; a test makes sure
that every catalog parameter is placed on purpose.
"""

from __future__ import annotations

from typing import Any

from .parameter_catalog import ParameterCatalog, ParameterDefinition

GROUPS: tuple[tuple[str, str], ...] = (
    ("tid", "Tid och kalender"),
    ("rum", "Lokaler och digitalt"),
    ("bemanning", "Bemanning"),
    ("kostnad", "Kostnader"),
    ("korning", "Körning"),
    ("ovrigt", "Efterfrågan och övrigt"),
)

LAYOUT: dict[str, tuple[str, ...]] = {
    "tid": (
        "wish.candidate_policy", "wish.time_policy", "window.earlier_days", "window.later_days", "calendar.start_date", "calendar.end_date", "calendar.weekdays",
        "calendar.start_times", "calendar.earliest_start_time", "calendar.latest_end_time", "calendar.turnaround_minutes",
        "calendar.blocked_ranges", "calendar.exam_periods", "flex.movable_types", "rules.keep_course_order",
        "rules.student_conflicts",
    ),
    "rum": (
        "rooms.selection", "rooms.exclude", "rooms.include_observed_unregistered", "reservations.policy", "reservations.action_no_count", "reservations.action_outside_selection", "reservations.action_not_in_ladok", "rooms.allow_split", "rooms.max_rooms_per_exam", "rooms.allow_split_across_buildings",
        "rooms.availability_mode", "rooms.capacity_override", "rooms.custom_rooms", "rooms.co_location_rules",
        "digital.partial_support_policy", "digital.unknown_demand_policy", "digital.exam_share_pct",
        "digital.compatibility_matrix",
    ),
    "bemanning": (
        "staffing.ladder", "staffing.preparation_minutes", "staffing.closing_minutes", "staffing.shifts",
        "staffing.min_break_minutes", "staffing.max_continuous_minutes", "staffing.max_daily_minutes",
        "staffing.min_daily_rest_minutes", "staffing.travel_minutes", "staffing.min_paid_shift_minutes",
    ),
    "kostnad": (
        "resources.pack", "cost.room_annual_per_seat_ore", "cost.staff_paid_minute_ore", "cost.staff_annual_ore", "cost.staff_session_ore", "cost.external_room_session_ore",
        "cost.annualization_factor", "cost.avoidable_cost_definition",
    ),
    "korning": (
        "wish.tiebreak", "solver.time_limit_seconds", "solver.relative_gap_limit", "solver.strategy", "solver.workers",
        "solver.deterministic", "solver.seed", "objective.weights",
    ),
    "ovrigt": (
        "demand.variation_pct", "demand.rounding", "demand.measure", "demand.capacity_safety_margin_pct",
        "exam.max_duration_hours", "special_support.rules",
    ),
}

# Not meaningful for an analyst to change case by case: they affect how the search runs, not what is being asked.
ADVANCED = frozenset({"solver.seed", "solver.deterministic", "solver.workers", "solver.strategy", "solver.relative_gap_limit"})


def group_labels() -> dict[str, str]:
    return dict(GROUPS)


def layout(catalog: ParameterCatalog) -> list[tuple[ParameterDefinition, str, int]]:
    """(definition, group id, order) for every catalog parameter. `order` runs over all groups in display order."""
    by_id = {item.parameter_id: item for item in catalog.parameters}
    placed: dict[str, str] = {parameter_id: group for group, ids in LAYOUT.items() for parameter_id in ids}
    rows: list[tuple[ParameterDefinition, str]] = []
    for group, _ in GROUPS:
        listed = [by_id[parameter_id] for parameter_id in LAYOUT[group] if parameter_id in by_id]
        extra = [item for item in catalog.parameters if item.parameter_id not in placed] if group == "ovrigt" else []
        rows.extend((item, group) for item in listed + extra)
    return [(item, group, index) for index, (item, group) in enumerate(rows)]


def group_of(catalog: ParameterCatalog) -> dict[str, str]:
    return {item.parameter_id: group for item, group, _ in layout(catalog)}


def describe_parameters(catalog: ParameterCatalog, scenario_id: str, scenario_values: dict[str, Any]) -> dict[str, Any]:
    """The payload of `GET /api/joint-runs/parameters`: every parameter with default, scenario value and effective value."""
    rows = []
    for item, group, order in layout(catalog):
        has_scenario_value = item.parameter_id in scenario_values
        scenario_value = scenario_values.get(item.parameter_id)
        value = scenario_value if has_scenario_value else item.default
        differs = value != item.default
        rows.append({
            "id": item.parameter_id, "label": item.label, "group": group, "value_type": item.value_type, "unit": item.unit,
            "help_text": item.help_text, "default": item.default, "scenario_value": scenario_value, "value": value,
            "differs_from_default": differs,
            "basis": "experiment" if differs and item.default_basis in {"verified", "source_data"} else item.default_basis,
            "engine_support": item.engine_support, "editable": item.engine_support == "implemented",
            "advanced": item.parameter_id in ADVANCED,
            "choices": [{"value": choice, "label": label} for choice, label in item.choices] if item.choices else None,
            "order": order,
        })
    return {
        "catalog_version": catalog.version, "scenario_id": scenario_id, "parameters": rows,
        "group_order": [group for group, _ in GROUPS], "group_labels": group_labels(),
    }
