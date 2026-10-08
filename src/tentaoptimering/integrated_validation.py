"""Independent post-validation of an exploratory integrated term run."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .integrated_config import IntegratedTermScenario, load_integrated_term_scenario
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
    demands = {str(item["exam_demand_id"]): item for item in inputs["demands"]}
    rooms = {str(item["room_id"]): item for item in inputs["rooms"]}
    slots = {item.slot_id: item for item in generate_calendar_slots(scenario.calendar)}
    rules = (
        _coverage(assignments, demands),
        _capacity(assignments, rooms),
        _room_intervals(assignments, demands, scenario, slots),
        _location(assignments, demands, rooms),
        _digital_compatibility(scenario),
        _availability(scenario),
        _course_program_conflicts(inputs),
        _aggregate_staffing(assignments, demands, scenario, slots, result),
        _individual_staffing(),
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


def write_validation_report(run_dir: Path) -> dict[str, Any]:
    report = validate_integrated_term_run(run_dir)
    (run_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "validation.md").write_text(_markdown(report), encoding="utf-8")
    return {"report": report, "artifacts": {name: str((run_dir / name).resolve()) for name in ("validation.json", "validation.md")}}


def _coverage(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]]) -> RuleResult:
    totals = assignments.groupby("exam_demand_id")["participants"].sum().to_dict() if not assignments.empty else {}
    failures = []
    for demand_id, demand in demands.items():
        if int(totals.get(demand_id, 0)) != int(demand["participants"]):
            failures.append(demand_id)
    failures.extend(str(item) for item in totals if str(item) not in demands)
    return _result("included_demand_coverage", failures, "Varje inkluderat behov har exakt rätt antal placerade deltagare.")


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


def _digital_compatibility(scenario: IntegratedTermScenario) -> RuleResult:
    expected = "all_exploratory_candidate_rooms_assumed_compatible_with_observed_formats"
    if scenario.digital_compatibility_mode == expected:
        return RuleResult("digital_compatibility", PASS, "Global kompatibilitet är ett aktivt scenarioantagande, inte verifierad matris.", (), True)
    return RuleResult("digital_compatibility", NOT_EVALUATED, "Ingen aktiverad verifierbar kompatibilitetsmatris finns.", ())


def _availability(scenario: IntegratedTermScenario) -> RuleResult:
    values = {item.assumption_id: item.value for item in scenario.assumptions}
    if values.get("room_availability") == "all selected candidate rooms available for every configured slot":
        return RuleResult("room_availability", PASS, "Full tillgänglighet är ett aktivt scenarioantagande, inte verifierad kalender.", (), True)
    return RuleResult("room_availability", NOT_EVALUATED, "Verifierad salbokningskalender saknas.", ())


def _course_program_conflicts(inputs: dict[str, Any]) -> RuleResult:
    traceability = inputs.get("demand_traceability", [])
    if not traceability:
        return RuleResult("course_program_conflicts", NOT_EVALUATED, "Kurs-/programrelationer saknas.", ("course_program_conflict_policy",))
    return RuleResult("course_program_conflicts", NOT_EVALUATED, "Kurskoder finns, men ingen aktiverad krockpolicy eller programrelation finns.", ("course_program_conflict_policy",))


def _aggregate_staffing(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot], result: dict[str, Any]) -> RuleResult:
    intervals = _session_intervals(assignments, demands, scenario, slots)
    expected = 0
    for _room, day, start, end in intervals:
        concurrent = sum(other_day == day and start < other_end and other_start < end for _other_room, other_day, other_start, other_end in intervals)
        expected = max(expected, concurrent * scenario.staff_per_room_session)
    actual = result.get("solution", {}).get("anonymous_staff_pool_size")
    if actual is None:
        return RuleResult("aggregate_staffing", NOT_EVALUATED, "Körningsresultatet saknar anonym bemanningspool.", ())
    return _result("aggregate_staffing", [] if int(actual) == expected else [f"expected:{expected}|actual:{actual}"], "Anonym samtidig bemanning motsvarar aktiverad bemanningsregel.")


def _individual_staffing() -> RuleResult:
    return RuleResult("individual_staffing_constraints", NOT_EVALUATED, "Modellen saknar individuella resurser samt regler för raster, restid, kompetens och arbetstid.", ())


def _session_intervals(assignments: pd.DataFrame, demands: dict[str, dict[str, Any]], scenario: IntegratedTermScenario, slots: dict[str, CalendarSlot]) -> list[tuple[str, str, int, int]]:
    intervals = []
    for (room_id, slot_id), rows in assignments.groupby(["room_id", "slot_id"]):
        slot = slots.get(str(slot_id))
        known = [demands.get(str(value)) for value in rows["exam_demand_id"]]
        if slot is None or any(item is None for item in known):
            continue
        intervals.append((str(room_id), slot.scheduled_date.isoformat(), slot.start_minute, slot.start_minute + max(int(item["duration_minutes"]) for item in known if item) + scenario.calendar.turnaround_minutes))
    return intervals


def _result(rule_id: str, failures: list[str], pass_reason: str) -> RuleResult:
    if failures:
        return RuleResult(rule_id, FAIL, "Regeln bröts för angivna objekt.", tuple(sorted(set(failures))))
    return RuleResult(rule_id, PASS, pass_reason, ())


def _technical_status(rules: tuple[RuleResult, ...]) -> dict[str, Any]:
    relevant = {"included_demand_coverage", "room_capacity", "room_time_intervals", "plan_area"}
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
