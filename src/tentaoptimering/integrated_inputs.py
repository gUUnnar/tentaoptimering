"""Adapter from generated canonical scope data to term-model entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from .integrated_config import IntegratedTermScenario
from .integrated_term import IntegratedDemand, IntegratedRoom
from .optimizer_time import duration_minutes
from .term_calendar import generate_calendar_slots


READY_STATUS = "ready_provisional_ladok_demand"


@dataclass(frozen=True)
class TermModelInputs:
    demands: tuple[IntegratedDemand, ...]
    rooms: tuple[IntegratedRoom, ...]
    demand_traceability: tuple[dict[str, object], ...]
    scope_metrics: dict[str, int]
    scope_decisions: tuple[dict[str, object], ...] = ()


def load_term_model_inputs(processed_dir: Path, scenario: IntegratedTermScenario) -> TermModelInputs:
    """Load only included, ready demand while retaining total-population scope metrics."""
    demands_frame = pd.read_csv(processed_dir / "optimization_demands.csv", encoding="utf-8-sig")
    rooms_frame = pd.read_csv(processed_dir / "optimization_rooms.csv", encoding="utf-8-sig")
    scope_frame = pd.read_csv(processed_dir / "demand_scope.csv", encoding="utf-8-sig")
    if "scope_reason_code" not in scope_frame:
        scope_frame["scope_reason_code"] = "not_supplied"
    included = scope_frame.loc[scope_frame["scope_status"] == "included", "activity_id"]
    ready = demands_frame[
        (demands_frame["demand_input_status"] == READY_STATUS)
        & demands_frame["activity_id"].isin(set(included))
    ].copy()
    if ready["activity_id"].duplicated().any():
        raise ValueError("Adapter kräver högst en körbar efterfrågerad per källaktivitet.")
    if len(ready) != len(included):
        raise ValueError("Inkluderade scope-aktiviteter saknar körbar efterfrågerad.")
    rooms = rooms_frame[rooms_frame["eligible_for_exploratory_capacity_poc"]].copy()
    if rooms.empty:
        raise ValueError("Inga scenariorum är tillåtna för explorativ terminskörning.")
    demands: list[IntegratedDemand] = []
    traceability: list[dict[str, object]] = []
    for row in ready.itertuples(index=False):
        plan_area = str(row.observed_cities)
        demands.append(
            IntegratedDemand(
                exam_demand_id=str(row.demand_id), participants=int(row.demand_value),
                duration_minutes=duration_minutes(str(row.scheduled_time)), plan_area=plan_area,
                course_code=_optional_text(row, "course_code"),
            )
        )
        traceability.append({
            "exam_demand_id": str(row.demand_id), "source_activity_id": str(row.activity_id),
            "source_exam_event_id": str(row.exam_event_id), "course_code": str(row.course_code),
            "demand_measure": str(row.demand_measure_source_field),
            "demand_value": int(row.demand_value), "scope_status": "included",
        })
    return TermModelInputs(
        demands=tuple(demands),
        rooms=tuple(
            IntegratedRoom(
                room_id=str(row.room_id), capacity=int(row.capacity_seats),
                plan_area=str(row.reference_city),
                annual_cost_ore=int(row.capacity_seats) * scenario.room_cost_ore_per_seat,
                building_id=_optional_text(row, "building_id") or str(row.room_id),
                digital_capabilities=frozenset({"all"}) if scenario.digital_compatibility_mode.startswith("all_") else frozenset({"unknown"}),
                available_slot_ids=_available_slot_ids(row, scenario),
            )
            for row in rooms.itertuples(index=False)
            if _available_slot_ids(row, scenario)
        ),
        demand_traceability=tuple(traceability),
        scope_metrics={
            "source_activities_total": int(len(scope_frame)),
            "included_source_activities": int((scope_frame["scope_status"] == "included").sum()),
            "unresolved_source_activities": int((scope_frame["scope_status"] == "unresolved").sum()),
            "excluded_source_activities": int((scope_frame["scope_status"] == "excluded").sum()),
            "model_ready_exam_demands": int(len(demands)),
        },
        scope_decisions=tuple(
            {
                "activity_id": str(row.activity_id),
                "scope_status": str(row.scope_status),
                "scope_reason_code": str(row.scope_reason_code),
            }
            for row in scope_frame.loc[:, ["activity_id", "scope_status", "scope_reason_code"]].itertuples(index=False)
        ),
    )


def _optional_text(row: object, name: str) -> str | None:
    value = getattr(row, name, None)
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _available_slot_ids(row: object, scenario: IntegratedTermScenario) -> frozenset[str]:
    """Apply explicit room start/end dates before a room reaches the term engine."""
    available_from = _optional_date(row, "available_from")
    available_to = _optional_date(row, "available_to")
    return frozenset(
        slot.slot_id
        for slot in generate_calendar_slots(scenario.calendar)
        if (available_from is None or slot.scheduled_date >= available_from)
        and (available_to is None or slot.scheduled_date <= available_to)
    )


def _optional_date(row: object, name: str) -> date | None:
    value = _optional_text(row, name)
    return date.fromisoformat(value) if value else None
