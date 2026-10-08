from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import tomllib
from typing import Any


OBJECTIVE_NAMES = (
    "unplaced_participants",
    "unplaced_exams",
    "distinct_rooms",
    "room_open_minutes",
    "unused_seat_minutes",
    "rescheduled_exams",
    "room_reassignments",
)


@dataclass(frozen=True)
class ScenarioConfig:
    schema_version: int
    scenario_id: str
    description: str
    date_shift_earlier_days: int
    date_shift_later_days: int
    start_time_shift_minutes: int
    start_time_step_minutes: int
    allowed_weekdays: tuple[int, ...]
    earliest_start_time: str
    latest_end_time: str
    turnaround_minutes: int
    allowed_room_ids: tuple[str, ...]
    capacity_safety_margin_ratio: float
    allow_co_location: bool
    allow_split: bool
    max_rooms_per_exam: int
    enforce_historical_city: bool
    availability_mode: str
    special_support_mode: str
    digital_compatibility_mode: str
    allow_unplaced: bool
    objective_weights: dict[str, int]
    max_time_seconds: float
    num_workers: int
    random_seed: int
    relative_gap_limit: float

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_weekdays"] = list(self.allowed_weekdays)
        payload["allowed_room_ids"] = list(self.allowed_room_ids)
        return payload


def _table(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Körningskonfigurationen saknar tabellen [{name}].")
    return value


def _required(table: dict[str, Any], key: str, table_name: str) -> Any:
    if key not in table:
        raise ValueError(f"Körningskonfigurationen saknar [{table_name}].{key}.")
    return table[key]


def _minutes(value: str, field: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"{field} måste anges som HH:MM.") from error
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"{field} ligger utanför ett giltigt dygn: {value}.")
    return hour * 60 + minute


def _validate(config: ScenarioConfig) -> None:
    if config.schema_version != 1:
        raise ValueError("Endast schema_version = 1 stöds för körningskonfigurationer.")
    if not config.scenario_id.strip():
        raise ValueError("scenario_id får inte vara tomt.")
    non_negative = {
        "date_shift_earlier_days": config.date_shift_earlier_days,
        "date_shift_later_days": config.date_shift_later_days,
        "start_time_shift_minutes": config.start_time_shift_minutes,
        "turnaround_minutes": config.turnaround_minutes,
        "capacity_safety_margin_ratio": config.capacity_safety_margin_ratio,
        "relative_gap_limit": config.relative_gap_limit,
    }
    for name, value in non_negative.items():
        if value < 0:
            raise ValueError(f"{name} får inte vara negativt.")
    if config.start_time_step_minutes <= 0:
        raise ValueError("start_time_step_minutes måste vara större än noll.")
    if not config.allowed_weekdays or any(day not in range(1, 8) for day in config.allowed_weekdays):
        raise ValueError("allowed_weekdays ska innehålla ISO-veckodagar 1–7.")
    if _minutes(config.earliest_start_time, "earliest_start_time") >= _minutes(
        config.latest_end_time, "latest_end_time"
    ):
        raise ValueError("earliest_start_time måste ligga före latest_end_time.")
    if not config.allowed_room_ids:
        raise ValueError("allowed_room_ids måste innehålla minst ett explicit rums-ID.")
    if config.max_rooms_per_exam <= 0:
        raise ValueError("max_rooms_per_exam måste vara större än noll.")
    if not config.allow_split and config.max_rooms_per_exam != 1:
        raise ValueError("max_rooms_per_exam måste vara 1 när allow_split är false.")
    if config.max_time_seconds <= 0 or config.num_workers <= 0:
        raise ValueError("Solverns tidsgräns och antal workers måste vara större än noll.")
    missing_weights = set(OBJECTIVE_NAMES) - set(config.objective_weights)
    extra_weights = set(config.objective_weights) - set(OBJECTIVE_NAMES)
    if missing_weights or extra_weights:
        raise ValueError(
            "[objective.weights] måste ange exakt följande mål: "
            + ", ".join(OBJECTIVE_NAMES)
        )
    if any(not isinstance(value, int) or value < 0 for value in config.objective_weights.values()):
        raise ValueError("Alla målviktningar måste vara icke-negativa heltal.")
    supported_uncertainty_modes = {"not_modeled_with_warning"}
    if config.special_support_mode not in supported_uncertainty_modes:
        raise ValueError("Endast special_support_mode = not_modeled_with_warning stöds ännu.")
    if config.digital_compatibility_mode not in supported_uncertainty_modes:
        raise ValueError("Endast digital_compatibility_mode = not_modeled_with_warning stöds ännu.")
    if config.availability_mode != "scenario_rooms_assumed_available_without_calendar_guarantee":
        raise ValueError("Okänt availability_mode för denna PoC-version.")


def load_scenario_config(path: Path) -> ScenarioConfig:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    time = _table(payload, "time")
    placement = _table(payload, "placement")
    objective = _table(payload, "objective")
    solver = _table(payload, "solver")
    weights = _table(objective, "weights")
    config = ScenarioConfig(
        schema_version=_required(payload, "schema_version", "root"),
        scenario_id=_required(payload, "scenario_id", "root"),
        description=_required(payload, "description", "root"),
        date_shift_earlier_days=_required(time, "date_shift_earlier_days", "time"),
        date_shift_later_days=_required(time, "date_shift_later_days", "time"),
        start_time_shift_minutes=_required(time, "start_time_shift_minutes", "time"),
        start_time_step_minutes=_required(time, "start_time_step_minutes", "time"),
        allowed_weekdays=tuple(_required(time, "allowed_weekdays", "time")),
        earliest_start_time=_required(time, "earliest_start_time", "time"),
        latest_end_time=_required(time, "latest_end_time", "time"),
        turnaround_minutes=_required(time, "turnaround_minutes", "time"),
        allowed_room_ids=tuple(_required(placement, "allowed_room_ids", "placement")),
        capacity_safety_margin_ratio=_required(
            placement, "capacity_safety_margin_ratio", "placement"
        ),
        allow_co_location=_required(placement, "allow_co_location", "placement"),
        allow_split=_required(placement, "allow_split", "placement"),
        max_rooms_per_exam=_required(placement, "max_rooms_per_exam", "placement"),
        enforce_historical_city=_required(
            placement, "enforce_historical_city", "placement"
        ),
        availability_mode=_required(placement, "availability_mode", "placement"),
        special_support_mode=_required(placement, "special_support_mode", "placement"),
        digital_compatibility_mode=_required(
            placement, "digital_compatibility_mode", "placement"
        ),
        allow_unplaced=_required(placement, "allow_unplaced", "placement"),
        objective_weights={name: _required(weights, name, "objective.weights") for name in OBJECTIVE_NAMES},
        max_time_seconds=_required(solver, "max_time_seconds", "solver"),
        num_workers=_required(solver, "num_workers", "solver"),
        random_seed=_required(solver, "random_seed", "solver"),
        relative_gap_limit=_required(solver, "relative_gap_limit", "solver"),
    )
    _validate(config)
    return config

