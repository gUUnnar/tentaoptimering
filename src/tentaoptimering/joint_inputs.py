"""Build and persist a real-data case for the joint optimizer: named events or a whole selected term."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
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
from .joint_observed_rooms import observed_unregistered_rooms, with_price
from .joint_options import building_id, select_rooms
from .joint_report import build_report, validation_lines
from .joint_resources import build_resource_layer, save_pack_snapshot
from .joint_progress import EVENTS_FILE, ProgressSink, emit, phase
from .joint_selection import select_ready_demands
from .joint_strategy.resources import CancelToken, ExecutionBudget
from .joint_strategy.warm_start import StartReport
from .joint_validation import write_validation
from .joint_wishes import EventWish, load_wishes, require_wishes, uses_window, uses_wishes, wish_candidate_ids, wish_for
from .joint_warm_start import AUTO, decision_record, explain, find_start, report_lines, write_decision
from .parameter_catalog import freeze_parameter_values, load_parameter_catalog
from .provenance import sha256_file
from .run_meta import new_meta, run_kind, write_meta

SCENARIO_COPY = "joint_scenario.toml"


def build_real_subset_problem(
    config_path: Path,
    processed_dir: Path,
    catalog_path: Path,
) -> JointOptimizationInput:
    """Adapt real exam events (named, or selected by a rule in `[subset]`) without silently expanding or shrinking them.

    Every behaviour below is driven by the frozen parameter values, never by raw scenario keys.
    """
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "joint-real-subset-v1":
        raise ValueError(f"Okänd konfigurationsversion: {config.get('schema_version')}")
    demands_frame = pd.read_csv(processed_dir / "optimization_demands.csv", encoding="utf-8-sig")
    rooms_frame = pd.read_csv(processed_dir / "optimization_rooms.csv", encoding="utf-8-sig")
    scope_frame = pd.read_csv(processed_dir / "demand_scope.csv", encoding="utf-8-sig")
    ready = select_ready_demands(demands_frame, config["subset"])

    catalog = load_parameter_catalog(catalog_path)
    parameters = freeze_parameter_values(catalog, _parameter_overrides(config), _rationales(config))
    values = {item.parameter_id: item.value for item in parameters}
    if values["demand.measure"] != "registered_count":
        raise ValueError("Endast efterfrågemåttet registered_count stöds av dataadaptern.")
    earlier, later = int(values["window.earlier_days"]), int(values["window.later_days"])

    wishes = load_wishes(processed_dir)
    require_wishes(wishes, values)
    events = _prepare_events(ready, values, wishes)
    slots = _slots(values, events, earlier, later)
    slot_by_key = {(item.scheduled_date, item.start_minute): item for item in slots}
    demands = tuple(_demand(event, slot_by_key, slots, values, earlier, later) for event in events)

    rooms = _rooms(rooms_frame, config["subset"]["plan_area"], slots, values)
    if values["rooms.include_observed_unregistered"]:
        inventory_path = processed_dir / "room_inventory.csv"
        inventory = pd.read_csv(inventory_path, encoding="utf-8-sig") if inventory_path.is_file() else None
        price = int(values["cost.room_annual_per_seat_ore"])
        extra = observed_unregistered_rooms(inventory, config["subset"]["plan_area"], tuple(slot.slot_id for slot in slots), {room.room_id for room in rooms})
        rooms = rooms + tuple(with_price(room, price) for room in extra)
    ladder = tuple(
        StaffingStep(int(item["max_participants"]), int(item["required_staff"]))
        for item in values["staffing.ladder"]
    )
    rooms, staff, reservations, basis = build_resource_layer(
        rooms, values, parameters, config["subset"]["plan_area"], slots, catalog_path, processed_dir,
        {item["event_id"] for item in events},
    )
    return JointOptimizationInput(
        schema_version=INPUT_SCHEMA_VERSION,
        problem_id=str(config["scenario"]["id"]),
        dataset_hash=dataset_hash(processed_dir),
        slots=slots,
        demands=demands,
        rooms=rooms,
        staffing=StaffingCostPolicy(
            ladder=ladder,
            annual_cost_ore_per_staff=staff["annual_cost_ore_per_staff"]["value"],
            cost_ore_per_staff_session=int(values["cost.staff_session_ore"]),
            preparation_minutes=int(values["staffing.preparation_minutes"]),
            closing_minutes=int(values["staffing.closing_minutes"]),
            paid_minute_cost_ore=staff["paid_minute_cost_ore"]["value"],
            min_paid_minutes=staff["min_paid_minutes"]["value"],
        ),
        solver=SolverSettings(
            float(values["solver.time_limit_seconds"]), int(values["solver.seed"]), int(values["solver.workers"]),
            bool(values["solver.deterministic"]), str(values["solver.strategy"]), float(values["solver.relative_gap_limit"]),
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
        preference=str(values["wish.tiebreak"]),
        reservations=reservations,
        resource_basis=basis,
    )


def _new_run_directory(runs_dir: Path, problem_id: str) -> tuple[str, Path]:
    """Create the directory of a new run. The id keeps its time stamp format; a run that starts in the same second as
    another (short periods finish in under a second) gets the next free second, so ids stay unique and ordered."""
    stamp = int(time.time())
    while True:
        run_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(stamp))}-{problem_id}"
        try:
            (runs_dir / run_id).mkdir(parents=True, exist_ok=False)  # parents: the runs folder may not exist yet
        except FileExistsError:
            stamp += 1
            continue
        return run_id, runs_dir / run_id


def _prepare_events(ready: pd.DataFrame, values: dict[str, Any], wishes: dict[str, EventWish] | None) -> list[dict[str, Any]]:
    """Resolve each named exam event to one historical occasion, duration and type."""
    events = []
    for event_id, frame in ready.groupby("exam_event_id", sort=True):
        dates = set(frame["scheduled_date"].astype(str))
        starts = set(str(value)[:5] for value in frame["booking_start_time"])
        if len(dates) != 1 or len(starts) != 1:
            raise ValueError(f"Samtentan {event_id} saknar gemensamt ursprungstillfälle.")
        durations = {int(_duration_minutes(str(value))) for value in frame["scheduled_time"]}
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
            "wish": wish_for(wishes, str(event_id)),
        })
        # Wished dates widen the calendar only when the policy lets wishes steer the dates.
        events[-1]["wish_days"] = events[-1]["wish"].days() if uses_wishes(str(values["wish.candidate_policy"])) else []
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
        policy = str(values["wish.candidate_policy"])
        wished = wish_candidate_ids(event, slots, policy, str(values["wish.time_policy"]), _latest_end_limit(values))
        # The historical occasion competes only if it satisfies every user setting.
        candidates = tuple(
            slot.slot_id for slot in slots
            if not slot.reference_only and slot.slot_id in wished or (
                uses_window(policy) and not slot.reference_only and low <= slot.scheduled_date <= high
                and slot.start_minute + event["duration"] <= _latest_end_limit(values))
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
        wish_dates=event["wish"].dates, wish_status=event["wish"].status, wish_reason=event["wish"].reason,
    )


def _rooms(
    rooms_frame: pd.DataFrame, plan_area: str, slots: tuple[CandidateSlot, ...], values: dict[str, Any]
) -> tuple[Room, ...]:
    rows = select_rooms(rooms_frame, plan_area, values["rooms.selection"])  # an unknown room id is an error, not ignored
    result = []
    for row in rows.itertuples(index=False):
        capabilities, basis = _room_digital(str(row.digital_capability_status), values)
        result.append(
            Room(
                room_id=str(row.room_id),
                building_id=building_id(str(row.reference_address)),
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
    warm_start: str | None = AUTO,
    budget: ExecutionBudget | None = None,
    cancel: CancelToken | None = None,
    progress: ProgressSink | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build, solve, save and validate one run.

    `meta` (name, kind, base run, changes; see `run_meta`) is saved as `joint_run.json` before the solve, so that
    even a run that fails or is cancelled says what it was. Without it the run is described by its scenario alone.

    `warm_start` is "auto" (the newest usable earlier run of the same problem), "none", or the run id of an
    earlier run. The earlier placement is only a starting point: the solver re-checks it against the new
    instance, and the independent post-validation of the new run is made as for any run.

    `progress` only observes the run. The run directory is created as soon as the problem is built (and before
    the solve), so that the sink can write `joint_events.jsonl` there while the run is going on; the artifacts
    that exist afterwards are the same as without a sink, plus that file.
    """
    problem = build_real_subset_problem(config_path, processed_dir, catalog_path)
    choice = find_start(runs_dir, problem, warm_start)
    budget = (budget or ExecutionBudget()).resolve(problem.solver)
    report = StartReport()
    run_id, run_dir = _new_run_directory(runs_dir, problem.problem_id)
    shutil.copyfile(config_path, run_dir / SCENARIO_COPY)  # the scenario file that this run actually used
    write_meta(run_dir, {**(meta or new_meta(
        name=None, kind=run_kind(problem.problem_id, {}, False), scenario_id=problem.problem_id, base_run_id=None, changes={}, period=None,
        processed_dir=processed_dir, catalog_path=catalog_path)), "dataset_hash": problem.dataset_hash})
    if progress is not None:
        progress.run_id = run_id
        progress.attach(run_dir / EVENTS_FILE)
        progress.defer("finished")  # the last event comes after the artifacts are saved and validated
        if choice.source is None:
            emit(progress, "warm_start", decision="not_used", explanation=explain(choice, report), source_run_id=None)
    report.source_run_id = choice.source.run_id if choice.source else None
    try:
        result = solve_joint_optimization(problem, choice.start, budget, cancel, report, progress)
        decision = decision_record(choice, problem, report, budget)
        with phase(progress, "finalize"):
            saved = _save_and_validate(
                problem, result, decision, choice, run_id, run_dir, config_path, processed_dir, catalog_path
            )
        if progress is not None:
            progress.release()  # the solver's `finished` is the last event only once everything is saved and validated
        return saved
    except BaseException as error:
        if progress is not None:
            # The solver may have ended well, but the run did not: its held-back success event must not end the log.
            progress.discard("finished")
            if not progress.has("finished"):
                emit(progress, "finished", outcome="failed", cost_ore=None, bound_ore=None,
                     cancelled=bool(cancel and cancel.cancelled), error=f"{type(error).__name__}: {error}")
        raise
    finally:
        if progress is not None:
            progress.close()  # the log file is this run's; the events stay readable from memory


def _save_and_validate(
    problem: JointOptimizationInput, result: Any, decision: dict[str, Any], choice: Any, run_id: str, run_dir: Path,
    config_path: Path, processed_dir: Path, catalog_path: Path,
) -> dict[str, Any]:
    """Write the artifacts of a solved run and validate them independently."""
    write_problem(problem, run_dir / "joint_input.json")
    write_result(result, run_dir / "joint_result.json")
    (run_dir / "joint_report.md").write_text(build_report(problem, result), encoding="utf-8")
    manifest = {
        "input_sha256": sha256_file(run_dir / "joint_input.json"),
        "result_sha256": sha256_file(run_dir / "joint_result.json"),
        "config_sha256": sha256_file(config_path),
        "catalog_sha256": sha256_file(catalog_path),
        "warm_start_source_run_id": choice.source.run_id if choice.source else None,
        "warm_start_source_result_sha256": choice.source.result_sha256 if choice.source else None,
        "resource_pack_sha256": save_pack_snapshot(problem.resource_basis, catalog_path, run_dir),
    }
    write_decision(run_dir, decision)
    (run_dir / "joint_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    validation = write_validation(
        run_dir, processed_dir=processed_dir, config_path=config_path, catalog_path=catalog_path
    )
    with (run_dir / "joint_report.md").open("a", encoding="utf-8") as handle:
        handle.write(chr(10).join(validation_lines(validation["summary"]) + report_lines(decision)))
    return {
        "run_id": run_id,
        "warm_start": decision,
        "result": json.loads((run_dir / "joint_result.json").read_text(encoding="utf-8")),
        "validation": validation["summary"],
        "artifacts": {path.name: str(path.resolve()) for path in run_dir.iterdir()},
    }


def _latest_end_limit(values: dict[str, Any]) -> int:
    return _clock_minutes(str(values["calendar.latest_end_time"]))


def _slots(
    values: dict[str, Any], events: list[dict[str, Any]], earlier: int, later: int
) -> tuple[CandidateSlot, ...]:
    """Generate allowed (date, start) occasions, plus reference occasions for fixed exams."""
    originals = [item["original_date"] for item in events] + [day for item in events for day in item["wish_days"]]
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


def dataset_hash(processed_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in ("optimization_demands.csv", "optimization_rooms.csv", "demand_scope.csv"):
        digest.update(bytes.fromhex(sha256_file(processed_dir / name)))
    return digest.hexdigest()


def _clock_minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def _duration_minutes(value: str) -> int:
    """Minutes in a `HH:MM-HH:MM` interval; an end at or before the start means the next day."""
    start_text, end_text = value.split("-", maxsplit=1)
    start, end = _clock_minutes(start_text), _clock_minutes(end_text)
    return (end if end > start else end + 24 * 60) - start


def _clock_text(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"
