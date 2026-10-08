"""Adapter from generated canonical scope data to term-model entities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .integrated_config import IntegratedTermScenario
from .integrated_term import IntegratedDemand, IntegratedRoom
from .optimizer_time import duration_minutes


READY_STATUS = "ready_provisional_ladok_demand"


@dataclass(frozen=True)
class TermModelInputs:
    demands: tuple[IntegratedDemand, ...]
    rooms: tuple[IntegratedRoom, ...]
    demand_traceability: tuple[dict[str, object], ...]
    scope_metrics: dict[str, int]


def load_term_model_inputs(processed_dir: Path, scenario: IntegratedTermScenario) -> TermModelInputs:
    """Load only included, ready demand while retaining total-population scope metrics."""
    demands_frame = pd.read_csv(processed_dir / "optimization_demands.csv", encoding="utf-8-sig")
    rooms_frame = pd.read_csv(processed_dir / "optimization_rooms.csv", encoding="utf-8-sig")
    scope_frame = pd.read_csv(processed_dir / "demand_scope.csv", encoding="utf-8-sig")
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
            )
            for row in rooms.itertuples(index=False)
        ),
        demand_traceability=tuple(traceability),
        scope_metrics={
            "source_activities_total": int(len(scope_frame)),
            "included_source_activities": int((scope_frame["scope_status"] == "included").sum()),
            "unresolved_source_activities": int((scope_frame["scope_status"] == "unresolved").sum()),
            "excluded_source_activities": int((scope_frame["scope_status"] == "excluded").sum()),
            "model_ready_exam_demands": int(len(demands)),
        },
    )
