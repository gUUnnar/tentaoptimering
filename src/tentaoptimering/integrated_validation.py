"""Independent post-validation of an exploratory integrated term run."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from .integrated_config import IntegratedTermScenario, load_integrated_term_scenario
from .staffing_validation import validate_staffing
from .term_calendar import CalendarSlot, generate_calendar_slots


PASS = "pass"
FAIL = "fail"
NOT_EVALUATED = "not_evaluated"
NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    status: str
    reason: str
    object_ids: tuple[str, ...]
    assumption_only: bool = False


def validate_integrated_term_run(run_dir: Path) -> dict[str, Any]:
    """Validate saved run artifacts without invoking its placement algorithm."""
    scenario = load_integrated_term_scenario(run_dir / "scenario.toml")
    inputs = json.loads((run_dir / "model_inputs.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assignments = pd.read_csv(run_dir / "assignments.csv", encoding="utf-8-sig")
    staff_path = run_dir / "staff_assignments.csv"
    staff_assignments = pd.read_csv(staff_path, encoding="utf-8-sig") if staff_path.is_file() else None
    model_inputs, demands, rooms = _model_inputs(inputs)
    slots = {item.slot_id: item for item in generate_calendar_slots(scenario.calendar)}
    assignment_rows, valid_assignments = _assignment_rows(assignments, demands, rooms, slots)
    rules = (
        model_inputs,
        assignment_rows,
        _coverage(valid_assignments, demands),
        _calendar_pass_constraints(valid_assignments, demands, slots),
        _capacity(valid_assignments, rooms),
        _room_intervals(valid_assignments, demands, scenario, slots),
        _location(valid_assignments, demands, rooms),
        _digital_compatibility(valid_assignments, demands, rooms, scenario),
        _availability(valid_assignments, rooms, scenario),
        _course_program_conflicts(valid_assignments, demands, slots, scenario),
        _aggregate_staffing(valid_assignments, demands, scenario, slots, result),
        _individual_staffing(valid_assignments, staff_assignments, demands, rooms, scenario, slots),
    )
    technical = _technical_status(rules)
    business = _business_status(rules)
    return {
        "schema_version": 1,
        "run_id": result.get("run_id"),
        "validation_method": "independent_post_validation",
        "technical_placement_completeness": technical,
        "business_feasibility": business,
        "rules": [asdict(rule) for rule in rules],
    }


def _model_inputs(inputs: dict[str, Any]) -> tuple[RuleResult, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    demands: dict[str, dict[str, Any]] = {}
    rooms: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    raw_demands = inputs.get("demands")
    raw_rooms = inputs.get("rooms")
    if not isinstance(raw_demands, list):
        failures.append("demands")
        raw_demands = []
    if not isinstance(raw_rooms, list):
        failures.append("rooms")
        raw_rooms = []
    for item in raw_demands:
        demand_id = str(item.get("exam_demand_id", "")) if isinstance(item, dict) else ""
        valid = isinstance(item, dict) and demand_id.strip() and demand_id not in demands and _positive_int(item.get("participants")) and _positive_int(item.get("duration_minutes")) and isinstance(item.get("plan_area"), str) and bool(item["plan_area"].strip())
        if not valid:
            failures.append(f"exam_demand:{demand_id or 'missing'}")
            continue
        demands[demand_id] = item
    for item in raw_rooms:
        room_id = str(item.get("room_id", "")) if isinstance(item, dict) else ""
        valid = isinstance(item, dict) and room_id.strip() and room_id not in rooms and _positive_int(item.get("capacity")) and isinstance(item.get("plan_area"), str) and bool(item["plan_area"].strip())
        if not valid:
            failures.append(f"room:{room_id or 'missing'}")
            continue
        rooms[room_id] = item
    return _result("model_inputs", failures, "Sparade behov och rum har giltiga identifierare, positiva heltalsantal och planeringsområden."), demands, rooms


def write_validation_report(run_dir: Path) -> dict[str, Any]:
    report = validate_integrated_term_run(run_dir)
    (run_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "validation.md").write_text(_markdown(report), encoding="utf-8")
    return {"report": report, "artifacts": {name: str((run_dir / name).resolve()) for name in ("validation.json", "validation.md")}}


def _assignment_rows(
    assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], rooms: dict[str, dict[str, Any]],
    slots: dict[str, CalendarSlot],
) -> tuple[RuleResult, pd.DataFrame]:
    required = ("exam_demand_id", "room_id", "slot_id", "participants")
    missing = [column for column in required if column not in assignments]
    if missing:
        return RuleResult("assignment_rows", FAIL, "Fördelningsartefakten saknar obligatoriska kolumner.", tuple(missing)), pd.DataFrame(columns=required)
    valid_rows = []
    failures = []
    for index, row in assignments.iterrows():
        demand_id, room_id, slot_id = (str(row[column]) for column in required[:3])
        seats = pd.to_numeric(pd.Series([row["participants"]]), errors="coerce").iloc[0]
        valid = (
            demand_id in demands and room_id in rooms and slot_id in slots
            and not pd.isna(seats) and math.isfinite(float(seats))
            and float(seats).is_integer() and int(seats) > 0
        )
        if not valid:
            failures.append(f"row:{index}")
            continue
        valid_rows.append({"exam_demand_id": demand_id, "room_id": room_id, "slot_id": slot_id, "participants": int(seats)})
    return _result("assignment_rows", failures, "Alla fördelningsrader har kända identifierare och positiva heltalsantal."), pd.DataFrame(valid_rows, columns=required)


def _coverage(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]]) -> RuleResult:
    totals = assignments.groupby("exam_demand_id")["participants"].sum().to_dict() if not assignments.empty else {}
    failures: list[str] = []
    for demand_id, demand in demands.items():
        starts = assignments.loc[assignments["exam_demand_id"] == demand_id, "slot_id"].unique()
        if int(totals.get(demand_id, 0)) != int(demand["participants"]) or len(starts) != 1:
            failures.append(demand_id)
    failures.extend(str(item) for item in totals if str(item) not in demands)
    return _result("included_demand_coverage", failures, "Varje inkluderat behov har exakt rätt antal deltagare och ett gemensamt startpass.")


def _calendar_pass_constraints(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], slots: dict[str, CalendarSlot]) -> RuleResult:
    failures = []
    for row in assignments.itertuples(index=False):
        demand = demands[str(row.exam_demand_id)]
        slot = slots[str(row.slot_id)]
        allowed = demand.get("allowed_pass_ids")
        duration = int(demand["duration_minutes"])
        if duration <= 0 or slot.start_minute + duration > slot.latest_end_minute or (allowed is not None and slot.pass_id not in allowed):
            failures.append(f"{row.exam_demand_id}:{row.slot_id}")
    return _result("calendar_pass_constraints", failures, "Varje tentamenslängd ryms i ett tillåtet kalenderpass.")


def _capacity(assignments: pd.DataFrame, rooms: dict[str, dict[str, Any]]) -> RuleResult:
    failures: list[str] = []
    for (room_id, slot_id), rows in assignments.groupby(["room_id", "slot_id"]):
        room = rooms.get(str(room_id))
        if room is None or int(rows["participants"].sum()) > int(room["capacity"]):
            failures.append(f"{room_id}:{slot_id}")
    return _result("room_capacity", failures, "Salarnas absoluta kapacitet respekteras per salstillfälle.")


def _room_intervals(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot]) -> RuleResult:
    intervals: list[tuple[str, str, int, int]] = []
    invalid: list[str] = []
    for (room_id, slot_id), rows in assignments.groupby(["room_id", "slot_id"]):
        slot = slots.get(str(slot_id))
        known = [demands.get(str(value)) for value in rows["exam_demand_id"]]
        if slot is None or any(item is None for item in known):
            invalid.append(f"{room_id}:{slot_id}")
            continue
        end = slot.start_minute + max(int(item["duration_minutes"]) for item in known if item) + scenario.calendar.turnaround_minutes
        intervals.append((str(room_id), slot.scheduled_date.isoformat(), slot.start_minute, end))
    failures = invalid[:]
    for index, (room, day, start, end) in enumerate(intervals):
        for other_room, other_day, other_start, other_end in intervals[index + 1:]:
            if room == other_room and day == other_day and start < other_end and other_start < end:
                failures.append(f"{room}:{day}:{start}-{end}|{other_start}-{other_end}")
    return _result("room_time_intervals", failures, "Ingen sal har överlappande pass, inklusive sluttid och ställtid.")


def _location(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], rooms: dict[str, dict[str, Any]]) -> RuleResult:
    failures = []
    for row in assignments.itertuples(index=False):
        demand, room = demands.get(str(row.exam_demand_id)), rooms.get(str(row.room_id))
        if demand is None or room is None or demand["plan_area"] != room["plan_area"]:
            failures.append(f"{row.exam_demand_id}:{row.room_id}")
    return _result("plan_area", failures, "Behov och sal ligger i samma planeringsområde.")


def _digital_compatibility(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], rooms: dict[str, dict[str, Any]], scenario: IntegratedTermScenario) -> RuleResult:
    explicit = False
    failures = []
    missing = []
    for row in assignments.itertuples(index=False):
        demand, room = demands[str(row.exam_demand_id)], rooms[str(row.room_id)]
        requirement = str(demand.get("digital_requirement", "unknown"))
        capabilities = room.get("digital_capabilities")
        if requirement in {"", "unknown", "none"}:
            continue
        explicit = True
        if not isinstance(capabilities, list):
            missing.append(f"{row.exam_demand_id}:{row.room_id}")
        elif "all" not in capabilities and requirement not in capabilities:
            failures.append(f"{row.exam_demand_id}:{row.room_id}")
    if failures:
        return _result("digital_compatibility", failures, "Digital kompatibilitet respekteras.")
    if missing:
        return RuleResult("digital_compatibility", NOT_EVALUATED, "Digitalt krav saknar sparad kompatibilitetsmatris.", tuple(missing))
    if explicit:
        return RuleResult("digital_compatibility", PASS, "Explicit digital kompatibilitetsmatris respekteras.", ())
    expected = "all_exploratory_candidate_rooms_assumed_compatible_with_observed_formats"
    if scenario.digital_compatibility_mode == expected:
        return RuleResult("digital_compatibility", PASS, "Global kompatibilitet är ett aktivt scenarioantagande, inte verifierad matris.", (), True)
    return RuleResult("digital_compatibility", NOT_EVALUATED, "Ingen aktiverad verifierbar kompatibilitetsmatris finns.", ())


def _availability(assignments: pd.DataFrame, rooms: dict[str, dict[str, Any]], scenario: IntegratedTermScenario) -> RuleResult:
    explicit = False
    failures = []
    for row in assignments.itertuples(index=False):
        allowed = rooms[str(row.room_id)].get("available_slot_ids")
        if allowed is None:
            continue
        explicit = True
        if not isinstance(allowed, list) or str(row.slot_id) not in allowed:
            failures.append(f"{row.room_id}:{row.slot_id}")
    if failures:
        return _result("room_availability", failures, "Salens explicita tillgänglighet respekteras.")
    if explicit:
        return RuleResult("room_availability", PASS, "Explicit salstillgänglighet respekteras.", ())
    values = {item.assumption_id: item.value for item in scenario.assumptions}
    if values.get("room_availability") == "all selected candidate rooms available for every configured slot":
        return RuleResult("room_availability", PASS, "Full tillgänglighet är ett aktivt scenarioantagande, inte verifierad kalender.", (), True)
    return RuleResult("room_availability", NOT_EVALUATED, "Verifierad salbokningskalender saknas.", ())


def _course_program_conflicts(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], slots: dict[str, CalendarSlot], scenario: IntegratedTermScenario) -> RuleResult:
    if "same_course_hard_constraint" not in scenario.conflict_policy:
        return RuleResult("course_program_conflicts", NOT_EVALUATED, "Ingen aktiv kurskrockspolicy är sparad i scenariot.", ())
    starts = {str(demand_id): str(rows.iloc[0]["slot_id"]) for demand_id, rows in assignments.groupby("exam_demand_id")}
    known = [item for item in demands.values() if str(item.get("course_code", "")).strip()]
    if not known:
        return RuleResult("course_program_conflicts", NOT_EVALUATED, "Inga explicita kurs- eller programrelationer finns i modellindata.", ())
    failures = []
    for index, left in enumerate(known):
        for right in known[index + 1:]:
            same_course = left.get("course_code") == right.get("course_code")
            programs = set(left.get("program_ids") or ()).intersection(right.get("program_ids") or ())
            if not same_course and not programs:
                continue
            left_slot, right_slot = slots.get(starts.get(str(left["exam_demand_id"]), "")), slots.get(starts.get(str(right["exam_demand_id"]), ""))
            if left_slot and right_slot and left_slot.scheduled_date == right_slot.scheduled_date and left_slot.start_minute < right_slot.start_minute + int(right["duration_minutes"]) and right_slot.start_minute < left_slot.start_minute + int(left["duration_minutes"]):
                failures.append(f"{left['exam_demand_id']}:{right['exam_demand_id']}")
    if failures:
        return _result("course_program_conflicts", failures, "Kurs- och programkrockar respekteras.")
    if scenario.program_conflict_data_status != "verified":
        return RuleResult("course_program_conflicts", NOT_EVALUATED, "Kurskrockar är kontrollerade, men programrelationer saknar verifierad täckning.", ("program_relation_data_status",))
    return RuleResult("course_program_conflicts", PASS, "Kurs- och programkrockar respekteras med verifierade relationer.", ())


def _aggregate_staffing(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot], result: dict[str, Any]) -> RuleResult:
    intervals = _session_intervals(assignments, demands, scenario, slots)
    expected = 0
    for _room, day, start, end, count in intervals:
        concurrent = sum(other_count for _other_room, other_day, other_start, other_end, other_count in intervals if other_day == day and start < other_end and other_start < end)
        expected = max(expected, concurrent)
    actual = result.get("solution", {}).get("anonymous_staff_pool_size")
    if actual is None:
        return RuleResult("aggregate_staffing", NOT_EVALUATED, "Körningsresultatet saknar anonym bemanningspool.", ())
    if not isinstance(actual, int) or actual < 0:
        return RuleResult("aggregate_staffing", FAIL, "Bemanningspoolen är inte ett icke-negativt heltal.", ("anonymous_staff_pool_size",))
    return _result("aggregate_staffing", [] if actual >= expected else [f"minimum:{expected}|actual:{actual}"], "Anonym samtidig bemanning uppfyller aktiverat minimikrav.")


def _individual_staffing(assignments: pd.DataFrame, staff_assignments: pd.DataFrame | None, demands: dict[str, dict[str, Any]], rooms: dict[str, dict[str, Any]], scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot]) -> RuleResult:
    status, reason, object_ids = validate_staffing(assignments, staff_assignments, demands, rooms, scenario, slots)
    return RuleResult("individual_staffing_constraints", status, reason, object_ids)


def _session_intervals(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot]) -> list[tuple[str, str, int, int, int]]:
    intervals = []
    for (room_id, slot_id), rows in assignments.groupby(["room_id", "slot_id"]):
        slot = slots.get(str(slot_id))
        known = [demands.get(str(value)) for value in rows["exam_demand_id"]]
        if slot is None or any(item is None for item in known):
            continue
        participants = int(rows["participants"].sum())
        intervals.append((
            str(room_id), slot.scheduled_date.isoformat(),
            slot.start_minute - scenario.staffing_policy.preparation_minutes,
            slot.start_minute + max(int(item["duration_minutes"]) for item in known if item) + max(
                scenario.staffing_policy.closing_minutes, scenario.calendar.turnaround_minutes,
            ),
            _staff_required(participants, scenario),
        ))
    return intervals


def _staff_required(participants: int, scenario: IntegratedTermScenario) -> int:
    for step in scenario.staffing_policy.ladder:
        if participants <= step.up_to_participants:
            return step.staff_required
    return 10**9


def _result(rule_id: str, failures: list[str], pass_reason: str) -> RuleResult:
    if failures:
        return RuleResult(rule_id, FAIL, "Regeln bröts för angivna objekt.", tuple(sorted(set(failures))))
    return RuleResult(rule_id, PASS, pass_reason, ())


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _technical_status(rules: tuple[RuleResult, ...]) -> dict[str, Any]:
    relevant = {"model_inputs", "assignment_rows", "included_demand_coverage", "calendar_pass_constraints", "room_capacity", "room_time_intervals", "plan_area"}
    failed = [item.rule_id for item in rules if item.rule_id in relevant and item.status == FAIL]
    return {"status": PASS if not failed else FAIL, "reason": "Alla tekniska placeringsregler passerar." if not failed else "Teknisk placeringsregel bruten.", "failed_rules": failed}


def _business_status(rules: tuple[RuleResult, ...]) -> dict[str, Any]:
    failed = [item.rule_id for item in rules if item.status == FAIL]
    missing = [item.rule_id for item in rules if item.status == NOT_EVALUATED or item.assumption_only]
    if failed:
        return {"status": FAIL, "reason": "Minst en kontrollerad verksamhetsregel bröts.", "failed_rules": failed, "not_verified_rules": missing}
    if missing:
        return {"status": "not_verified", "reason": "Obligatoriska regler saknar verifierad data eller modellstöd.", "failed_rules": [], "not_verified_rules": missing}
    return {"status": PASS, "reason": "Alla aktiverade verksamhetsregler är verifierade.", "failed_rules": [], "not_verified_rules": []}


def _markdown(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Oberoende eftervalidering", "",
        f"- Teknisk placeringsfullständighet: `{report['technical_placement_completeness']['status']}`.",
        f"- Verksamhetsmässig genomförbarhet: `{report['business_feasibility']['status']}`.", "",
        "| Regel | Status | Orsak | Objekt |", "| --- | --- | --- | --- |",
        *[f"| {item['rule_id']} | {item['status']} | {item['reason']} | {', '.join(item['object_ids'])} |" for item in report["rules"]], "",
    ])
