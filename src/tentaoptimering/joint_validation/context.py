"""Read-only views of the saved input and result.

Only the file format (JSON field names and schema versions) is shared with the producer. Nothing
from the optimizer, its staffing functions or its derived values is imported or trusted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

SOLUTION_OUTCOMES = ("optimal", "feasible_not_proven")


class MalformedArtifact(ValueError):
    """Raised for a missing or wrongly typed field in a saved artifact."""


@dataclass(frozen=True)
class Slot:
    slot_id: str
    day: date
    start: int
    latest_end: int
    reference_only: bool


@dataclass(frozen=True)
class Demand:
    demand_id: str
    group_counts: tuple[int, ...]
    source_activities: tuple[str, ...]
    group_ids: tuple[str, ...]
    duration: int
    area: str
    candidates: frozenset[str]
    original_slot_id: str | None
    requires_room: bool
    course_code: str | None
    conflict_groups: frozenset[str]
    digital_requirement: str
    max_rooms: int
    split_across_buildings: bool
    original_day: date | None
    original_start: int | None
    movable: bool
    group_basis: str
    digital_basis: str

    @property
    def participants(self) -> int:
        return sum(self.group_counts)


@dataclass(frozen=True)
class Room:
    room_id: str
    building: str
    area: str
    capacity: int
    fixed_cost: int
    external_cost: int
    digital_capabilities: frozenset[str]
    available_slots: frozenset[str] | None
    digital_basis: str


@dataclass
class Context:
    problem: dict[str, Any]
    result: dict[str, Any]
    slots: dict[str, Slot]
    demands: dict[str, Demand]
    rooms: dict[str, Room]
    parameters: dict[str, Any]
    parameter_meta: dict[str, dict[str, Any]]
    ladder: list[tuple[int, int]]
    preparation: int
    closing: int
    turnaround: int
    staff_annual_cost: int
    staff_session_cost: int
    schedule: dict[str, dict[str, Any]] = field(default_factory=dict)
    assignments: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    has_solution: bool = False

    def slot_of(self, demand_id: str) -> Slot | None:
        row = self.schedule.get(demand_id)
        return self.slots.get(str(row["slot_id"])) if row else None


def _need(mapping: dict[str, Any], key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping:
        raise MalformedArtifact(f"{where}: fältet '{key}' saknas")
    return mapping[key]


def _day(value: Any, where: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise MalformedArtifact(f"{where}: ogiltigt datum {value!r}") from error


def _int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedArtifact(f"{where}: heltal förväntades, fick {value!r}")
    return value


def build_context(problem: dict[str, Any], result: dict[str, Any]) -> Context:
    """Parse the saved artifacts; any missing or malformed field raises MalformedArtifact."""
    slots = {}
    for item in _need(problem, "slots", "indata"):
        slot_id = str(_need(item, "slot_id", "pass"))
        if slot_id in slots:
            raise MalformedArtifact(f"pass: dubblerat slot_id {slot_id}")
        slots[slot_id] = Slot(
            slot_id, _day(_need(item, "scheduled_date", slot_id), slot_id),
            _int(_need(item, "start_minute", slot_id), slot_id),
            _int(_need(item, "latest_end_minute", slot_id), slot_id),
            bool(item.get("reference_only", False)),
        )
    demands: dict[str, Demand] = {}
    for item in _need(problem, "demands", "indata"):
        demand_id = str(_need(item, "exam_demand_id", "tentamensbehov"))
        if demand_id in demands:
            raise MalformedArtifact(f"tentamensbehov: dubblerat id {demand_id}")
        groups = _need(item, "participant_groups", demand_id)
        original_day = item.get("original_date")
        demands[demand_id] = Demand(
            demand_id,
            tuple(_int(_need(group, "participant_count", demand_id), demand_id) for group in groups),
            tuple(str(activity) for group in groups for activity in _need(group, "source_activity_ids", demand_id)),
            tuple(str(_need(group, "group_id", demand_id)) for group in groups),
            _int(_need(item, "duration_minutes", demand_id), demand_id),
            str(_need(item, "plan_area", demand_id)),
            frozenset(str(value) for value in _need(item, "candidate_slot_ids", demand_id)),
            item.get("original_slot_id"),
            bool(item.get("requires_room", True)),
            item.get("course_code"),
            frozenset(str(value) for value in item.get("conflict_group_ids", ())),
            str(item.get("digital_requirement", "none")),
            _int(item.get("max_rooms", 8), demand_id),
            bool(item.get("allow_split_across_buildings", False)),
            _day(original_day, demand_id) if original_day else None,
            item.get("original_start_minute"),
            bool(item.get("movable", True)),
            str(item.get("participant_group_basis", "single_activity")),
            str(item.get("digital_requirement_basis", "observed")),
        )
    rooms = {}
    for item in _need(problem, "rooms", "indata"):
        room_id = str(_need(item, "room_id", "sal"))
        available = item.get("available_slot_ids")
        rooms[room_id] = Room(
            room_id, str(_need(item, "building_id", room_id)), str(_need(item, "plan_area", room_id)),
            _int(_need(item, "capacity", room_id), room_id),
            _int(item.get("annual_fixed_cost_ore", 0), room_id), _int(item.get("external_session_cost_ore", 0), room_id),
            frozenset(str(value) for value in item.get("digital_capabilities", ("paper",))),
            frozenset(str(value) for value in available) if available is not None else None,
            str(item.get("digital_support_basis", "not_stated")),
        )
    staffing = _need(problem, "staffing", "indata")
    ladder = [
        (_int(_need(step, "max_participants", "trappa"), "trappa"), _int(_need(step, "required_staff", "trappa"), "trappa"))
        for step in _need(staffing, "ladder", "bemanning")
    ]
    parameters = {str(item["parameter_id"]): item.get("value") for item in problem.get("parameters", ())}
    meta = {str(item["parameter_id"]): item for item in problem.get("parameters", ())}
    context = Context(
        problem, result, slots, demands, rooms, parameters, meta, ladder,
        _int(staffing.get("preparation_minutes", 0), "bemanning"), _int(staffing.get("closing_minutes", 0), "bemanning"),
        _int(problem.get("turnaround_minutes", 0), "indata"),
        _int(_need(staffing, "annual_cost_ore_per_staff", "bemanning"), "bemanning"),
        _int(staffing.get("cost_ore_per_staff_session", 0), "bemanning"),
    )
    solver = _need(result, "solver", "resultat")
    outcome = _need(solver, "outcome", "solver")
    context.schedule = {
        str(_need(row, "exam_demand_id", "schemarad")): _schedule_row(row)
        for row in _rows(result, "schedule")
    }
    context.assignments = [_assignment_row(row) for row in _rows(result, "assignments")]
    context.sessions = [_session_row(row) for row in _rows(result, "room_sessions")]
    # A reported solution with an empty schedule is not "no solution": the missing demands must fail.
    context.has_solution = outcome in SOLUTION_OUTCOMES
    return context


def _rows(result: dict[str, Any], key: str) -> list[Any]:
    value = result.get(key, [])
    if not isinstance(value, list):
        raise MalformedArtifact(f"resultat: '{key}' ska vara en lista")
    return value


def _schedule_row(row: dict[str, Any]) -> dict[str, Any]:
    _need(row, "slot_id", "schemarad")
    if "participants" in row:
        _int(row["participants"], "schemarad.participants")
    return row


def _assignment_row(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("exam_demand_id", "slot_id", "room_id"):
        _need(row, key, "salsplacering")
    _int(_need(row, "participants", "salsplacering"), "salsplacering.participants")
    return row


def _session_row(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise MalformedArtifact("salstillfälle: objekt förväntades")
    return row
