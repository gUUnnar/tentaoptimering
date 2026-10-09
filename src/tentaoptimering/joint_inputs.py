"""Build and persist a bounded real-data case for the joint optimizer."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import time
import tomllib
from typing import Any

import pandas as pd

from .joint_contract import (
    INPUT_SCHEMA_VERSION,
    CandidateSlot,
    ExamDemand,
    JointOptimizationInput,
    ParticipantGroup,
    Room,
    ScopeSummary,
    SolverSettings,
    StaffingCostPolicy,
    StaffingStep,
    write_problem,
    write_result,
)
from .joint_optimizer import solve_joint_optimization
from .optimizer_time import duration_minutes
from .parameter_catalog import freeze_parameter_values, load_parameter_catalog
from .provenance import sha256_file


def build_real_subset_problem(
    config_path: Path,
    processed_dir: Path,
    catalog_path: Path,
) -> JointOptimizationInput:
    """Adapt named real exam events without silently expanding or shrinking the subset."""
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "joint-real-subset-v1":
        raise ValueError(f"Okänd konfigurationsversion: {config.get('schema_version')}")
    demands_frame = pd.read_csv(processed_dir / "optimization_demands.csv", encoding="utf-8-sig")
    rooms_frame = pd.read_csv(processed_dir / "optimization_rooms.csv", encoding="utf-8-sig")
    scope_frame = pd.read_csv(processed_dir / "demand_scope.csv", encoding="utf-8-sig")
    selected_events = tuple(str(value) for value in config["subset"]["exam_event_ids"])
    ready = demands_frame[
        demands_frame["exam_event_id"].isin(selected_events)
        & (demands_frame["demand_input_status"] == "ready_provisional_ladok_demand")
    ].copy()
    found = set(ready["exam_event_id"].astype(str))
    if found != set(selected_events):
        raise ValueError(f"Det verkliga delmängdsfallet saknar event: {sorted(set(selected_events) - found)}")

    parameter_overrides = _parameter_overrides(config)
    catalog = load_parameter_catalog(catalog_path)
    parameters = freeze_parameter_values(catalog, parameter_overrides, _rationales(config))
    values = {item.parameter_id: item.value for item in parameters}
    slots = _slots(config)
    slot_by_date_time = {
        (item.scheduled_date.isoformat(), _clock_text(item.start_minute)): item.slot_id for item in slots
    }
    demands = []
    for event_id, frame in ready.groupby("exam_event_id", sort=True):
        dates = set(frame["scheduled_date"].astype(str))
        starts = set(frame["booking_start_time"].astype(str))
        if len(dates) != 1 or len(starts) != 1:
            raise ValueError(f"Samtentan {event_id} saknar gemensamt ursprungstillfälle.")
        original_date = next(iter(dates))
        original_start = next(iter(starts))[:5]
        original_slot = slot_by_date_time.get((original_date, original_start))
        if original_slot is None:
            raise ValueError(f"Ursprungspasset {original_date} {original_start} saknas för {event_id}.")
        exam_types = [value.lower() for value in set(frame["observed_exam_types"].fillna("").astype(str))]
        exam_type = " ".join(sorted(exam_types))
        requires_room = not all("hemtenta" in value or "hemma" in value for value in exam_types)
        movable = any(token in exam_type for token in values["flex.movable_types"])
        durations = {int(duration_minutes(str(value))) for value in frame["scheduled_time"]}
        if len(durations) != 1:
            raise ValueError(f"Samtentan {event_id} har flera skrivtider: {sorted(durations)}")
        duration = next(iter(durations))
        candidates = _candidate_slots(
            slots,
            date.fromisoformat(original_date),
            int(values["window.earlier_days"]) if movable else 0,
            int(values["window.later_days"]) if movable else 0,
            duration,
        )
        if original_slot not in candidates:
            candidates = tuple(sorted(set(candidates) | {original_slot}))
        groups = tuple(
            ParticipantGroup(
                group_id=f"{event_id}-group-{index:02d}",
                participant_count=_scaled_count(
                    int(row.demand_value), int(values["demand.variation_pct"]), str(values["demand.rounding"])
                ),
                source_activity_ids=(str(row.activity_id),),
                count_basis=str(row.demand_measure_source_field),
            )
            for index, row in enumerate(frame.sort_values("activity_id").itertuples(index=False), start=1)
        )
        course_codes = sorted(set(frame["course_code"].dropna().astype(str)))
        digital_values = {str(value).strip().lower() for value in frame["observed_digital_exam_values"].dropna()}
        demands.append(
            ExamDemand(
                exam_demand_id=f"exam-{event_id}",
                participant_groups=groups,
                duration_minutes=duration,
                plan_area=str(frame.iloc[0]["observed_cities"]),
                candidate_slot_ids=candidates,
                original_slot_id=original_slot,
                requires_room=requires_room,
                course_code=course_codes[0] if len(course_codes) == 1 else None,
                conflict_group_ids=tuple(f"course:{code}" for code in course_codes),
                digital_requirement="e_exam" if "ja" in digital_values else "paper",
                max_rooms=int(values["rooms.max_rooms_per_exam"]),
                allow_split_across_buildings=bool(values["rooms.allow_split_across_buildings"]),
            )
        )

    selected_room_ids = set(str(value) for value in values["rooms.selection"])
    room_rows = rooms_frame[
        rooms_frame["eligible_for_exploratory_capacity_poc"].astype(bool)
        & (rooms_frame["reference_city"] == config["subset"]["plan_area"])
    ].copy()
    if selected_room_ids:
        room_rows = room_rows[room_rows["room_id"].isin(selected_room_ids)]
    rooms = tuple(
        Room(
            room_id=str(row.room_id),
            building_id=_building_id(str(row.reference_address)),
            plan_area=str(row.reference_city),
            capacity=int(row.capacity_seats),
            annual_fixed_cost_ore=int(row.capacity_seats) * int(values["cost.room_annual_per_seat_ore"]),
            external_session_cost_ore=0,
            digital_capabilities=("paper", "e_exam") if str(row.digital_capability_status).startswith("all_places") else ("paper",),
            available_slot_ids=tuple(
                slot.slot_id for slot in slots
                if _date_available(slot.scheduled_date, row.available_from, row.available_to)
            ),
        )
        for row in room_rows.itertuples(index=False)
    )
    ladder = tuple(
        StaffingStep(int(item["max_participants"]), int(item["required_staff"]))
        for item in values["staffing.ladder"]
    )
    modeled_activities = sum(len(group.source_activity_ids) for demand in demands for group in demand.participant_groups)
    return JointOptimizationInput(
        schema_version=INPUT_SCHEMA_VERSION,
        problem_id=str(config["scenario"]["id"]),
        dataset_hash=_dataset_hash(processed_dir),
        slots=slots,
        demands=tuple(demands),
        rooms=rooms,
        staffing=StaffingCostPolicy(
            ladder=ladder,
            annual_cost_ore_per_staff=int(values["cost.staff_annual_ore"]),
            cost_ore_per_staff_session=int(values["cost.staff_session_ore"]),
            preparation_minutes=int(values["staffing.preparation_minutes"]),
            closing_minutes=int(values["staffing.closing_minutes"]),
        ),
        solver=SolverSettings(
            float(values["solver.time_limit_seconds"]), int(values["solver.seed"]), 1
        ),
        parameters=parameters,
        scope=ScopeSummary(
            source_activities_total=len(scope_frame),
            included_source_activities=int((scope_frame["scope_status"] == "included").sum()),
            unresolved_source_activities=int((scope_frame["scope_status"] == "unresolved").sum()),
            excluded_source_activities=int((scope_frame["scope_status"] == "excluded").sum()),
            modeled_exam_demands=len(demands),
            modeled_participants=sum(item.participant_count for item in demands),
        ),
        turnaround_minutes=int(values["calendar.turnaround_minutes"]),
    )


def run_real_subset(
    config_path: Path,
    processed_dir: Path,
    catalog_path: Path,
    runs_dir: Path,
) -> dict[str, Any]:
    problem = build_real_subset_problem(config_path, processed_dir, catalog_path)
    result = solve_joint_optimization(problem)
    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{problem.problem_id}"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_problem(problem, run_dir / "joint_input.json")
    write_result(result, run_dir / "joint_result.json")
    (run_dir / "joint_report.md").write_text(_report(problem, result), encoding="utf-8")
    manifest = {
        "input_sha256": sha256_file(run_dir / "joint_input.json"),
        "result_sha256": sha256_file(run_dir / "joint_result.json"),
        "config_sha256": sha256_file(config_path),
        "catalog_sha256": sha256_file(catalog_path),
    }
    (run_dir / "joint_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "run_id": run_id,
        "result": json.loads((run_dir / "joint_result.json").read_text(encoding="utf-8")),
        "artifacts": {path.name: str(path.resolve()) for path in run_dir.iterdir()},
    }


def _slots(config: dict[str, Any]) -> tuple[CandidateSlot, ...]:
    start = date.fromisoformat(config["calendar"]["start_date"])
    end = date.fromisoformat(config["calendar"]["end_date"])
    weekdays = set(int(value) for value in config["parameters"]["calendar.weekdays"])
    result = []
    current = start
    while current <= end:
        if current.isoweekday() in weekdays:
            for item in config["calendar"]["pass"]:
                start_minute = _clock_minutes(str(item["start_time"]))
                result.append(
                    CandidateSlot(
                        f"{current.isoformat()}-{item['pass_id']}", current, str(item["pass_id"]),
                        start_minute, _clock_minutes(str(item["latest_end_time"])),
                    )
                )
        current += timedelta(days=1)
    return tuple(result)


def _candidate_slots(
    slots: tuple[CandidateSlot, ...], original_date: date, earlier: int, later: int, duration: int
) -> tuple[str, ...]:
    return tuple(
        slot.slot_id for slot in slots
        if original_date - timedelta(days=earlier) <= slot.scheduled_date <= original_date + timedelta(days=later)
        and slot.start_minute + duration <= slot.latest_end_minute
    )


def _parameter_overrides(config: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in config["parameters"].items()}


def _rationales(config: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in config.get("rationales", {}).items()}


def _scaled_count(count: int, percentage: int, rounding: str) -> int:
    value = count * (100 + percentage) / 100
    if rounding == "up":
        return max(1, math.ceil(value))
    if rounding == "nearest":
        return max(1, int(value + 0.5))
    if rounding == "down":
        return max(1, math.floor(value))
    raise ValueError(f"Okänd avrundningsregel: {rounding}")


def _date_available(value: date, available_from: object, available_to: object) -> bool:
    lower = None if pd.isna(available_from) else date.fromisoformat(str(available_from))
    upper = None if pd.isna(available_to) else date.fromisoformat(str(available_to))
    return (lower is None or value >= lower) and (upper is None or value <= upper)


def _dataset_hash(processed_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in ("optimization_demands.csv", "optimization_rooms.csv", "demand_scope.csv"):
        digest.update(bytes.fromhex(sha256_file(processed_dir / name)))
    return digest.hexdigest()


def _building_id(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")


def _clock_minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def _clock_text(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _report(problem: JointOptimizationInput, result: Any) -> str:
    solver = result.solver
    costs = result.costs
    return "\n".join([
        f"# Gemensam verklig delmängd: {problem.problem_id}", "",
        f"- Solverutfall: `{solver.outcome}` (`{solver.raw_status}`).",
        f"- Beräkningstid: {solver.wall_time_seconds:.3f} sekunder.",
        f"- Funnet jämförbart kostnadsmål: {solver.objective_value_ore} öre.",
        f"- Bästa kostnadsgräns: {solver.best_objective_bound_ore} öre.",
        f"- Relativt gap: {solver.relative_gap}.",
        f"- Teknisk placeringsfullständighet: {result.coverage.technical_placement_complete}.",
        f"- Behov/deltagare: {result.coverage.exam_demands_scheduled}/{result.coverage.exam_demands_total}, {result.coverage.participants_total} deltagare.",
        f"- Bemanningspool: {result.staff_pool_size} anonyma samtidiga resurser.",
        f"- Ändrade tentamenstillfällen: {result.changed_exam_demands}.", "",
        "## Kostnadskomponenter", "",
        f"- Långsiktiga salar: {costs.annual_room_cost_ore if costs else None} öre.",
        f"- Externa salstillfällen: {costs.external_room_session_cost_ore if costs else None} öre.",
        f"- Årlig bemanningspool: {costs.annual_staff_pool_cost_ore if costs else None} öre.",
        f"- Rörlig salstillfällesbemanning: {costs.staff_session_cost_ore if costs else None} öre.", "",
        "## Datatäckning och begränsningar", "",
        f"- Modellerade tentamensbehov: {problem.scope.modeled_exam_demands} av en uttryckligen vald delmängd.",
        f"- Hela källpopulationen: {problem.scope.source_activities_total} aktiviteter, varav {problem.scope.unresolved_source_activities} oavgjorda.",
        *[f"- {item}" for item in result.limitations], "",
    ])
