"""Build and persist a bounded real-data case for the joint optimizer."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
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
from .joint_validation import write_validation
from .optimizer_time import duration_minutes
from .parameter_catalog import freeze_parameter_values, load_parameter_catalog
from .provenance import sha256_file


def build_real_subset_problem(
    config_path: Path,
    processed_dir: Path,
    catalog_path: Path,
) -> JointOptimizationInput:
    """Adapt named real exam events without silently expanding or shrinking the subset.

    Every behaviour below is driven by the frozen parameter values, never by raw scenario keys.
    """
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

    catalog = load_parameter_catalog(catalog_path)
    parameters = freeze_parameter_values(catalog, _parameter_overrides(config), _rationales(config))
    values = {item.parameter_id: item.value for item in parameters}
    if values["demand.measure"] != "registered_count":
        raise ValueError("Endast efterfrågemåttet registered_count stöds av dataadaptern.")
    earlier, later = int(values["window.earlier_days"]), int(values["window.later_days"])

    events = _prepare_events(ready, values)
    slots = _slots(values, events, earlier, later)
    slot_by_key = {(item.scheduled_date, item.start_minute): item for item in slots}
    demands = tuple(_demand(event, slot_by_key, slots, values, earlier, later) for event in events)

    rooms = _rooms(rooms_frame, config["subset"]["plan_area"], slots, values)
    ladder = tuple(
        StaffingStep(int(item["max_participants"]), int(item["required_staff"]))
        for item in values["staffing.ladder"]
    )
    return JointOptimizationInput(
        schema_version=INPUT_SCHEMA_VERSION,
        problem_id=str(config["scenario"]["id"]),
        dataset_hash=_dataset_hash(processed_dir),
        slots=slots,
        demands=demands,
        rooms=rooms,
        staffing=StaffingCostPolicy(
            ladder=ladder,
            annual_cost_ore_per_staff=int(values["cost.staff_annual_ore"]),
            cost_ore_per_staff_session=int(values["cost.staff_session_ore"]),
            preparation_minutes=int(values["staffing.preparation_minutes"]),
            closing_minutes=int(values["staffing.closing_minutes"]),
        ),
        solver=SolverSettings(
            float(values["solver.time_limit_seconds"]), int(values["solver.seed"]), int(values["solver.workers"]),
            bool(values["solver.deterministic"]),
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


def _prepare_events(ready: pd.DataFrame, values: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve each named exam event to one historical occasion, duration and type."""
    events = []
    for event_id, frame in ready.groupby("exam_event_id", sort=True):
        dates = set(frame["scheduled_date"].astype(str))
        starts = set(str(value)[:5] for value in frame["booking_start_time"])
        if len(dates) != 1 or len(starts) != 1:
            raise ValueError(f"Samtentan {event_id} saknar gemensamt ursprungstillfälle.")
        durations = {int(duration_minutes(str(value))) for value in frame["scheduled_time"]}
        if len(durations) != 1:
            raise ValueError(f"Samtentan {event_id} har flera skrivtider: {sorted(durations)}")
        exam_types = sorted({str(value).lower() for value in frame["observed_exam_types"].fillna("")})
        exam_type = " ".join(exam_types)
        requirement, basis = _digital_requirement(frame["observed_digital_exam_values"], values)
        events.append({
            "event_id": str(event_id), "frame": frame,
            "original_date": date.fromisoformat(next(iter(dates))),
            "original_start": _clock_minutes(next(iter(starts))),
            "duration": next(iter(durations)),
            "requires_room": not all("hemtenta" in value or "hemma" in value for value in exam_types),
            "movable": any(token in exam_type for token in values["flex.movable_types"]),
            "digital_requirement": requirement, "digital_basis": basis,
        })
    return events


_DIGITAL_SEPARATORS = re.compile(r"\s*[|;,/]\s*")


def _digital_requirement(raw: pd.Series, values: dict[str, Any]) -> tuple[str, str]:
    """Classify the digital flag; a merged value such as ``Ja | Nej`` is never paper.

    The preparation step joins distinct booking values with `` | ``. Every value is split into
    tokens first, so a mixed event is recognised whether it arrives as several rows or as one
    merged value. Unrecognised content is never treated as paper.
    """
    tokens: set[str] = set()
    for value in raw.dropna():
        tokens.update(
            token for token in (part.strip().lower() for part in _DIGITAL_SEPARATORS.split(str(value))) if token
        )
    unrecognised = tokens - {"ja", "nej"}
    if "ja" in tokens and "nej" in tokens:
        return "e_exam", "observed_mixed"
    if "ja" in tokens:
        return "e_exam", "observed_mixed" if unrecognised else "observed_ja"
    if tokens == {"nej"}:
        return "paper", "observed_nej"
    if values["digital.unknown_demand_policy"] == "assume_paper":
        return "paper", "unobserved"
    return "e_exam", "unobserved"


def _demand(
    event: dict[str, Any],
    slot_by_key: dict[tuple[date, int], CandidateSlot],
    slots: tuple[CandidateSlot, ...],
    values: dict[str, Any],
    earlier: int,
    later: int,
) -> ExamDemand:
    original_key = (event["original_date"], event["original_start"])
    original_slot = slot_by_key.get(original_key)
    if event["movable"]:
        low, high = event["original_date"] - timedelta(days=earlier), event["original_date"] + timedelta(days=later)
        # The historical occasion competes only if it satisfies every user setting.
        candidates = tuple(
            slot.slot_id for slot in slots
            if not slot.reference_only and low <= slot.scheduled_date <= high
            and slot.start_minute + event["duration"] <= _latest_end_limit(values)
        )
    else:
        candidates = (original_slot.slot_id,) if original_slot is not None else ()
    frame = event["frame"]
    groups = tuple(
        ParticipantGroup(
            group_id=f"{event['event_id']}-group-{index:02d}",
            participant_count=_scaled_count(
                int(row.demand_value), int(values["demand.variation_pct"]), str(values["demand.rounding"])
            ),
            source_activity_ids=(str(row.activity_id),),
            count_basis=str(row.demand_measure_source_field),
        )
        for index, row in enumerate(frame.sort_values("activity_id").itertuples(index=False), start=1)
    )
    course_codes = sorted(set(frame["course_code"].dropna().astype(str)))
    max_rooms = int(values["rooms.max_rooms_per_exam"]) if values["rooms.allow_split"] else 1
    return ExamDemand(
        exam_demand_id=f"exam-{event['event_id']}",
        participant_groups=groups,
        duration_minutes=event["duration"],
        plan_area=str(frame.iloc[0]["observed_cities"]),
        candidate_slot_ids=candidates,
        original_slot_id=original_slot.slot_id if original_slot is not None else None,
        requires_room=event["requires_room"],
        course_code=course_codes[0] if len(course_codes) == 1 else None,
        conflict_group_ids=tuple(f"course:{code}" for code in course_codes),
        digital_requirement=event["digital_requirement"],
        max_rooms=max_rooms,
        allow_split_across_buildings=bool(values["rooms.allow_split_across_buildings"]),
        original_date=event["original_date"],
        original_start_minute=event["original_start"],
        movable=event["movable"],
        participant_group_basis="assumed_disjoint_groups_sum" if len(groups) > 1 else "single_activity",
        digital_requirement_basis=event["digital_basis"],
    )


def _rooms(
    rooms_frame: pd.DataFrame, plan_area: str, slots: tuple[CandidateSlot, ...], values: dict[str, Any]
) -> tuple[Room, ...]:
    selected = set(str(value) for value in values["rooms.selection"])
    rows = rooms_frame[
        rooms_frame["eligible_for_exploratory_capacity_poc"].astype(bool)
        & (rooms_frame["reference_city"] == plan_area)
    ].copy()
    if selected:
        rows = rows[rows["room_id"].isin(selected)]
    result = []
    for row in rows.itertuples(index=False):
        capabilities, basis = _room_digital(str(row.digital_capability_status), values)
        result.append(
            Room(
                room_id=str(row.room_id),
                building_id=_building_id(str(row.reference_address)),
                plan_area=str(row.reference_city),
                capacity=int(row.capacity_seats),
                annual_fixed_cost_ore=int(row.capacity_seats) * int(values["cost.room_annual_per_seat_ore"]),
                external_session_cost_ore=0,
                digital_capabilities=capabilities,
                available_slot_ids=tuple(
                    slot.slot_id for slot in slots
                    if _date_available(slot.scheduled_date, row.available_from, row.available_to)
                ),
                digital_support_basis=basis,
            )
        )
    return tuple(result)


def _room_digital(status: str, values: dict[str, Any]) -> tuple[tuple[str, ...], str]:
    """Published support is documented capacity; partial support is allowed only as an unverified policy."""
    if status.startswith("all_places"):
        return ("paper", "e_exam"), "all_places"
    if status.startswith("supports_e_exam"):
        if values["digital.partial_support_policy"] == "allow_unverified":
            return ("paper", "e_exam"), "some_places_unquantified"
        return ("paper",), "some_places_unquantified"
    return ("paper",), "unknown"


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
    validation = write_validation(
        run_dir, processed_dir=processed_dir, config_path=config_path, catalog_path=catalog_path
    )
    with (run_dir / "joint_report.md").open("a", encoding="utf-8") as report:
        report.write(chr(10).join(_validation_lines(validation["summary"])))
    return {
        "run_id": run_id,
        "result": json.loads((run_dir / "joint_result.json").read_text(encoding="utf-8")),
        "validation": validation["summary"],
        "artifacts": {path.name: str(path.resolve()) for path in run_dir.iterdir()},
    }


def _validation_lines(summary: dict[str, Any]) -> list[str]:
    """Report the three verdicts separately; the solver result itself is never altered."""
    return [
        "", "## Oberoende eftervalidering (joint_validation.md)", "",
        f"- Solverns status (återgiven, ej bevisad av valideraren): `{summary['solver_status']['reported_outcome']}`.",
        f"- Teknisk eftervalidering: `{summary['technical_validation']}`.",
        f"- Verksamhetsmässig verifiering: `{summary['business_verification']}`.",
        f"- Filernas ursprung och integritet: `{summary['provenance']}`.",
        f"- Tekniskt validerad: `{summary['technically_validated']}`.", "",
    ]


def _latest_end_limit(values: dict[str, Any]) -> int:
    return _clock_minutes(str(values["calendar.latest_end_time"]))


def _slots(
    values: dict[str, Any], events: list[dict[str, Any]], earlier: int, later: int
) -> tuple[CandidateSlot, ...]:
    """Generate allowed (date, start) occasions, plus reference occasions for fixed exams."""
    originals = [item["original_date"] for item in events]
    first = date.fromisoformat(str(values["calendar.start_date"])) if values["calendar.start_date"] else min(originals) - timedelta(days=earlier)
    last = date.fromisoformat(str(values["calendar.end_date"])) if values["calendar.end_date"] else max(originals) + timedelta(days=later)
    weekdays = set(int(value) for value in values["calendar.weekdays"])
    blocked = [
        (date.fromisoformat(str(item["start"])), date.fromisoformat(str(item["end"])))
        for item in values["calendar.blocked_ranges"]
    ]
    earliest = _clock_minutes(str(values["calendar.earliest_start_time"]))
    latest = _latest_end_limit(values)
    starts = sorted({
        _clock_minutes(str(value)) for value in values["calendar.start_times"]
        if _clock_minutes(str(value)) >= earliest
    })
    needed_end: dict[tuple[date, int], int] = {}
    for item in events:
        if not item["movable"]:
            key = (item["original_date"], item["original_start"])
            needed_end[key] = max(needed_end.get(key, 0), item["original_start"] + item["duration"])
    slots: dict[tuple[date, int], CandidateSlot] = {}
    current = first
    while current <= last:
        if current.isoweekday() in weekdays and not any(low <= current <= high for low, high in blocked):
            for start in starts:
                slots[current, start] = _slot(current, start, max(latest, needed_end.get((current, start), 0)), False)
        current += timedelta(days=1)
    for (day, start), end in needed_end.items():
        if (day, start) not in slots:
            slots[day, start] = _slot(day, start, max(latest, end), True)
    return tuple(sorted(slots.values(), key=lambda item: (item.scheduled_date, item.start_minute)))


def _slot(day: date, start: int, latest_end: int, reference_only: bool) -> CandidateSlot:
    label = _clock_text(start)
    return CandidateSlot(f"{day.isoformat()}T{label}", day, label, start, latest_end, reference_only)


def _parameter_overrides(config: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in config["parameters"].items()}


def _rationales(config: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in config.get("rationales", {}).items()}


def _scaled_count(count: int, percentage: int, rounding: str) -> int:
    """Scale with exact integer arithmetic so rounding never depends on float noise."""
    numerator = count * (100 + percentage)
    if rounding == "up":
        return max(1, -(-numerator // 100))
    if rounding == "nearest":
        return max(1, (numerator + 50) // 100)
    if rounding == "down":
        return max(1, numerator // 100)
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
        "## Verifieringsstatus", "",
        *[f"- {key}: {value}" for key, value in (result.verification or {}).items()], "",
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
