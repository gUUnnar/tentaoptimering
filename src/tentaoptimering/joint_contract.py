"""Versioned data contract for the joint scheduling and cost optimizer."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
import json
from pathlib import Path
from typing import Any


INPUT_SCHEMA_VERSION = "joint-optimization-input-v2"
RESULT_SCHEMA_VERSION = "joint-optimization-result-v2"


@dataclass(frozen=True)
class ParameterValue:
    parameter_id: str
    value: Any
    basis: str
    rationale: str
    engine_support: str
    changed_from_default: bool = False


@dataclass(frozen=True)
class ParticipantGroup:
    group_id: str
    participant_count: int
    source_activity_ids: tuple[str, ...]
    count_basis: str


@dataclass(frozen=True)
class CandidateSlot:
    slot_id: str
    scheduled_date: date
    pass_id: str
    start_minute: int
    latest_end_minute: int
    reference_only: bool = False


@dataclass(frozen=True)
class ExamDemand:
    exam_demand_id: str
    participant_groups: tuple[ParticipantGroup, ...]
    duration_minutes: int
    plan_area: str
    candidate_slot_ids: tuple[str, ...]
    original_slot_id: str | None
    requires_room: bool = True
    course_code: str | None = None
    conflict_group_ids: tuple[str, ...] = ()
    digital_requirement: str = "none"
    max_rooms: int = 8
    allow_split_across_buildings: bool = False
    original_date: date | None = None
    original_start_minute: int | None = None
    movable: bool = True
    participant_group_basis: str = "single_activity"
    digital_requirement_basis: str = "observed"

    @property
    def participant_count(self) -> int:
        """Count each explicit subgroup once, regardless of source-activity count."""
        return sum(group.participant_count for group in self.participant_groups)


@dataclass(frozen=True)
class Room:
    room_id: str
    building_id: str
    plan_area: str
    capacity: int
    annual_fixed_cost_ore: int
    external_session_cost_ore: int = 0
    digital_capabilities: tuple[str, ...] = ("paper",)
    available_slot_ids: tuple[str, ...] | None = None
    digital_support_basis: str = "not_stated"


@dataclass(frozen=True)
class StaffingStep:
    max_participants: int
    required_staff: int


@dataclass(frozen=True)
class StaffingCostPolicy:
    ladder: tuple[StaffingStep, ...]
    annual_cost_ore_per_staff: int
    cost_ore_per_staff_session: int = 0
    preparation_minutes: int = 0
    closing_minutes: int = 0


@dataclass(frozen=True)
class SolverSettings:
    time_limit_seconds: float = 60.0
    random_seed: int = 20261009
    num_workers: int = 1
    deterministic: bool = False


@dataclass(frozen=True)
class ScopeSummary:
    source_activities_total: int
    included_source_activities: int
    unresolved_source_activities: int
    excluded_source_activities: int
    modeled_exam_demands: int
    modeled_participants: int


@dataclass(frozen=True)
class JointOptimizationInput:
    schema_version: str
    problem_id: str
    dataset_hash: str
    slots: tuple[CandidateSlot, ...]
    demands: tuple[ExamDemand, ...]
    rooms: tuple[Room, ...]
    staffing: StaffingCostPolicy
    solver: SolverSettings
    parameters: tuple[ParameterValue, ...]
    scope: ScopeSummary
    turnaround_minutes: int = 0


@dataclass(frozen=True)
class SolverSummary:
    outcome: str
    raw_status: str
    objective_value_ore: int | None
    best_objective_bound_ore: int | None
    relative_gap: float | None
    wall_time_seconds: float
    change_preference_status: str


@dataclass(frozen=True)
class CostBreakdown:
    annual_room_cost_ore: int
    external_room_session_cost_ore: int
    annual_staff_pool_cost_ore: int
    staff_session_cost_ore: int
    comparable_total_cost_ore: int


@dataclass(frozen=True)
class CoverageSummary:
    exam_demands_total: int
    exam_demands_scheduled: int
    participants_total: int
    participants_assigned_to_rooms: int
    non_room_participants_scheduled: int
    technical_placement_complete: bool


@dataclass(frozen=True)
class JointOptimizationResult:
    schema_version: str
    problem_id: str
    solver: SolverSummary
    costs: CostBreakdown | None
    coverage: CoverageSummary
    staff_pool_size: int | None
    changed_exam_demands: int | None
    assignments: tuple[dict[str, Any], ...]
    room_sessions: tuple[dict[str, Any], ...]
    schedule: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]
    verification: dict[str, str] | None = None


def write_problem(problem: JointOptimizationInput, path: Path) -> None:
    path.write_text(json.dumps(_jsonable(problem), ensure_ascii=False, indent=2), encoding="utf-8")


def read_problem(path: Path) -> JointOptimizationInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError(f"Okänd indatakontraktsversion: {payload.get('schema_version')}")
    demands = tuple(
        ExamDemand(
            **{
                **item,
                "participant_groups": tuple(
                    ParticipantGroup(
                        **{**group, "source_activity_ids": tuple(group["source_activity_ids"])}
                    )
                    for group in item["participant_groups"]
                ),
                "candidate_slot_ids": tuple(item["candidate_slot_ids"]),
                "conflict_group_ids": tuple(item.get("conflict_group_ids", ())),
                "original_date": (
                    date.fromisoformat(item["original_date"]) if item.get("original_date") else None
                ),
            }
        )
        for item in payload["demands"]
    )
    rooms = tuple(
        Room(
            **{
                **item,
                "digital_capabilities": tuple(item.get("digital_capabilities", ("paper",))),
                "available_slot_ids": (
                    tuple(item["available_slot_ids"])
                    if item.get("available_slot_ids") is not None
                    else None
                ),
            }
        )
        for item in payload["rooms"]
    )
    return JointOptimizationInput(
        schema_version=payload["schema_version"],
        problem_id=payload["problem_id"],
        dataset_hash=payload["dataset_hash"],
        slots=tuple(
            CandidateSlot(**{**item, "scheduled_date": date.fromisoformat(item["scheduled_date"])})
            for item in payload["slots"]
        ),
        demands=demands,
        rooms=rooms,
        staffing=StaffingCostPolicy(
            **{
                **payload["staffing"],
                "ladder": tuple(StaffingStep(**item) for item in payload["staffing"]["ladder"]),
            }
        ),
        solver=SolverSettings(**payload["solver"]),
        parameters=tuple(ParameterValue(**item) for item in payload["parameters"]),
        scope=ScopeSummary(**payload["scope"]),
        turnaround_minutes=int(payload.get("turnaround_minutes", 0)),
    )


def write_result(result: JointOptimizationResult, path: Path) -> None:
    path.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")


def validate_problem(problem: JointOptimizationInput) -> None:
    """Reject malformed or silently incomplete optimization contracts."""
    if problem.schema_version != INPUT_SCHEMA_VERSION:
        raise ValueError(f"Okänd indatakontraktsversion: {problem.schema_version}")
    if not problem.demands or not problem.slots or not problem.rooms:
        raise ValueError("Gemensam optimering kräver behov, kandidatpass och salar.")
    if (
        problem.turnaround_minutes < 0
        or problem.solver.time_limit_seconds <= 0
        or problem.solver.num_workers <= 0
    ):
        raise ValueError("Ställtid måste vara icke-negativ och solvertidsgränsen positiv.")
    slot_ids = [item.slot_id for item in problem.slots]
    slots = {item.slot_id: item for item in problem.slots}
    if len(slot_ids) != len(set(slot_ids)):
        raise ValueError("Kandidatpassens identifierare måste vara unika.")
    slot_keys = [(item.scheduled_date, item.start_minute) for item in problem.slots]
    if len(slot_keys) != len(set(slot_keys)):
        raise ValueError("Ett datum och startklockslag får bara motsvara ett kandidatpass.")
    if any(item.start_minute >= item.latest_end_minute for item in problem.slots):
        raise ValueError("Varje kandidatpass måste sluta efter sin start.")
    room_ids = [item.room_id for item in problem.rooms]
    demand_ids = [item.exam_demand_id for item in problem.demands]
    if len(room_ids) != len(set(room_ids)) or len(demand_ids) != len(set(demand_ids)):
        raise ValueError("Sal- och tentamensidentifierare måste vara unika.")
    known_slots = set(slot_ids)
    source_activities: set[str] = set()
    for demand in problem.demands:
        if demand.duration_minutes <= 0 or demand.max_rooms <= 0 or not demand.participant_groups:
            raise ValueError(f"Ogiltigt tentamensbehov: {demand.exam_demand_id}")
        if not set(demand.candidate_slot_ids) <= known_slots:
            raise ValueError(f"Okända kandidatpass för {demand.exam_demand_id}.")
        if demand.original_slot_id is not None and demand.original_slot_id not in known_slots:
            raise ValueError(f"Okänt originalpass för {demand.exam_demand_id}.")
        group_ids = [group.group_id for group in demand.participant_groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError(f"Dubblerad delgrupp i {demand.exam_demand_id}.")
        for group in demand.participant_groups:
            if group.participant_count <= 0 or not group.source_activity_ids:
                raise ValueError(f"Ogiltig delgrupp i {demand.exam_demand_id}.")
            overlap = source_activities.intersection(group.source_activity_ids)
            if overlap:
                raise ValueError(f"Källaktiviteter kopplas flera gånger: {sorted(overlap)}")
            source_activities.update(group.source_activity_ids)
        if any(
            slots[slot_id].start_minute + demand.duration_minutes
            > slots[slot_id].latest_end_minute
            for slot_id in demand.candidate_slot_ids
        ):
            raise ValueError(f"Ett kandidatpass är för kort för {demand.exam_demand_id}.")
    previous = 0
    for step in problem.staffing.ladder:
        if step.max_participants <= previous or step.required_staff <= 0:
            raise ValueError("Bemanningstrappan måste ha stigande positiva gränser.")
        previous = step.max_participants
    if any(
        room.capacity <= 0
        or room.annual_fixed_cost_ore < 0
        or room.external_session_cost_ore < 0
        for room in problem.rooms
    ):
        raise ValueError("Salar måste ha positiv kapacitet och icke-negativa kostnader.")
    if any(
        room.available_slot_ids is not None
        and not set(room.available_slot_ids) <= known_slots
        for room in problem.rooms
    ):
        raise ValueError("En sal refererar till ett okänt tillgängligt pass.")
    parameter_ids = [item.parameter_id for item in problem.parameters]
    if len(parameter_ids) != len(set(parameter_ids)):
        raise ValueError("Frusna verksamhetsparametrar måste ha unika id:n.")
    total_participants = sum(item.participant_count for item in problem.demands)
    if (
        problem.scope.modeled_exam_demands != len(problem.demands)
        or problem.scope.modeled_participants != total_participants
    ):
        raise ValueError("Omfattningssammanfattningen stämmer inte med modellens behov.")
    if (
        problem.staffing.annual_cost_ore_per_staff < 0
        or problem.staffing.cost_ore_per_staff_session < 0
        or problem.staffing.preparation_minutes < 0
        or problem.staffing.closing_minutes < 0
    ):
        raise ValueError("Bemanningens tider och kostnader måste vara icke-negativa.")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
