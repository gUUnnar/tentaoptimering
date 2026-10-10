"""The validator must find injected faults, and tell a rule breach from missing evidence."""

from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import joint_validation_cases as cases  # noqa: E402
from tentaoptimering.joint_validation import validate_run
from tentaoptimering.joint_validation.derive import peak_concurrent_staff, staff_for

REPO_ROOT = Path(__file__).resolve().parents[1]


def _rules(payload: dict) -> dict[str, dict]:
    return {item["rule_id"]: item for item in payload["rules"]}


def _failing(payload: dict) -> set[str]:
    return {item["rule_id"] for item in payload["rules"] if item["status"] == "fail"}


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def validate(self, problem: dict, result: dict, name: str = "run", **kwargs) -> dict:
        return validate_run(cases.write_run(self.dir / name, problem, result), **kwargs)


class ReferenceCaseTests(_Base):
    def test_hand_worked_case_passes_every_technical_rule(self) -> None:
        payload = self.validate(*cases.copy_case())
        technical = {item["rule_id"]: item["status"] for item in payload["rules"] if item["axis"] == "technical"}
        self.assertEqual({key for key, value in technical.items() if value == "fail"}, set())
        self.assertEqual(technical["each_demand_scheduled_once"], "pass")
        self.assertEqual(technical["fixed_exams_keep_history"], "pass")
        self.assertEqual(technical["non_room_demands"], "pass")
        self.assertEqual(technical["staffing_per_room_session"], "pass")
        self.assertEqual(technical["costs_recomputed"], "pass")
        self.assertTrue(payload["summary"]["technically_validated"])

    def test_technical_pass_is_not_business_verification(self) -> None:
        payload = self.validate(*cases.copy_case())
        self.assertEqual(payload["summary"]["technical_validation"], "pass")
        self.assertEqual(payload["summary"]["business_verification"], "not_evaluated")
        business = {item["rule_id"]: item["status"] for item in payload["rules"] if item["axis"] == "business"}
        self.assertNotIn("pass", business.values())
        self.assertEqual(business["student_overlap"], "not_evaluated")
        self.assertEqual(business["digital_compatibility_verified"], "not_evaluated")
        self.assertEqual(business["group_disjointness"], "not_evaluated")
        self.assertEqual(business["population_completeness"], "not_evaluated")

    def test_unresolved_activities_are_disclosed_not_hidden_behind_full_coverage(self) -> None:
        problem, result = cases.copy_case()
        result["limitations"] = []
        self.assertIn("scope_disclosed", _failing(self.validate(problem, result)))

    def test_solver_status_is_reported_but_not_proven(self) -> None:
        payload = self.validate(*cases.copy_case())
        self.assertEqual(payload["summary"]["solver_status"]["reported_outcome"], "optimal")
        self.assertIn("bevisar varken optimalitet", payload["summary"]["solver_status"]["note"])


# (name, mutation of the saved problem and result, rule that must fail)
def _mutations():
    def set_result(path, value):
        def apply(problem, result):
            target = result
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        return apply

    def drop_demand(problem, result):
        result["schedule"] = [row for row in result["schedule"] if row["exam_demand_id"] != "A"]

    def lose_participant(problem, result):
        result["assignments"][2]["participants"] = 69

    def overbook(problem, result):
        problem["rooms"][1]["capacity"] = 49  # A has 50 in R2

    def overlap(problem, result):
        problem["slots"][1]["start_minute"] = 600  # s2 at 10:00 overlaps R1 s1 (08:00-12:00)

    def short_turnaround(problem, result):
        problem["slots"][1]["start_minute"] = 749  # R1 s1 ends 12:00, turnaround 30 -> earliest 12:30
        _allow_start(problem, 749)

    def digital_in_paper_room(problem, result):
        result["assignments"][1]["room_id"] = "R2"  # B is digital, R2 is paper only

    def wrong_area(problem, result):
        problem["rooms"][1]["plan_area"] = "Visby"

    def forbidden_weekday(problem, result):
        for item in problem["parameters"]:
            if item["parameter_id"] == "calendar.weekdays":
                item["value"] = [1]  # Tuesday is no longer allowed; C is on Tuesday

    def blocked_date(problem, result):
        for item in problem["parameters"]:
            if item["parameter_id"] == "calendar.blocked_ranges":
                item["value"] = [{"start": "2026-01-13", "end": "2026-01-13"}]

    def outside_window(problem, result):
        for item in problem["parameters"]:
            if item["parameter_id"] == "window.later_days":
                item["value"] = 0  # C has original Tuesday... B moved earlier is fine; make window zero for B (same day) -> still ok
        problem["demands"][2]["original_date"] = "2026-01-20"  # C scheduled a week from its original

    def fixed_exam_moved(problem, result):
        result["schedule"][3]["slot_id"] = "s1"

    def too_few_staff(problem, result):
        result["room_sessions"][3]["required_staff"] = 1  # 70 participants need 2

    def wrong_pool(problem, result):
        result["staff_pool_size"] = 2  # peak is 3 on Tuesday

    def inflated_pool(problem, result):
        result["staff_pool_size"] = 4

    def wrong_cost_component(problem, result):
        result["costs"]["annual_room_cost_ore"] = 16001

    def wrong_total(problem, result):
        result["costs"]["comparable_total_cost_ore"] = 19601

    def objective_mismatch(problem, result):
        result["solver"]["objective_value_ore"] = 19000

    def wrong_changed(problem, result):
        result["changed_exam_demands"] = 2

    def fictitious_room(problem, result):
        result["assignments"][0]["room_id"] = "R9"

    def same_course(problem, result):
        problem["demands"][0]["course_code"] = "SHARED"
        problem["demands"][1]["course_code"] = "SHARED"  # A and B are both at s1

    def split_buildings(problem, result):
        problem["rooms"][1]["building_id"] = "b2"  # C uses R1 and R2

    def too_many_rooms(problem, result):
        problem["demands"][2]["max_rooms"] = 1

    def room_unavailable(problem, result):
        problem["rooms"][1]["available_slot_ids"] = ["s1"]  # C needs R2 on s3

    def double_counted_activity(problem, result):
        problem["demands"][1]["participant_groups"][0]["source_activity_ids"] = ["A-a1"]

    def room_for_home_exam(problem, result):
        result["assignments"].append({"exam_demand_id": "D", "slot_id": "s4", "room_id": "R1", "participants": 30})

    def reference_slot_as_choice(problem, result):
        result["schedule"][0]["slot_id"] = "s4"

    def repeated_demand(problem, result):
        result["schedule"].append(deepcopy(result["schedule"][0]))

    def reference_slot_inside_window(problem, result):
        # A's historical date is the reference slot's date, so only the reference flag can reject it.
        for item in problem["parameters"]:
            if item["parameter_id"] == "calendar.end_date":
                item["value"] = ""
        problem["demands"][0].update(original_date="2026-01-14", original_start_minute=480, original_slot_id="s4",
                                     candidate_slot_ids=["s1", "s2", "s3", "s4"])
        result["schedule"][0]["slot_id"] = "s4"
        result["assignments"][0]["slot_id"] = "s4"

    def wrong_coverage(problem, result):
        result["coverage"]["exam_demands_total"] = 6

    def claimed_complete_but_participants_missing(problem, result):
        result["coverage"]["participants_assigned_to_rooms"] = 259

    def reported_session_differs(problem, result):
        result["room_sessions"][3]["participants"] = 71

    def session_missing_from_report(problem, result):
        result["room_sessions"].pop()

    def phantom_session(problem, result):
        result["room_sessions"].append({"room_id": "R2", "building_id": "b1", "slot_id": "s2", "exam_demand_ids": ["E"],
                                        "participants": 40, "required_staff": 1, "available_again_minute": 990})

    return [
        ("upprepad tenta i schemat", repeated_demand, "each_demand_scheduled_once"),
        ("referenspass som val inom fönstret", reference_slot_inside_window, "movable_exams_follow_calendar"),
        ("felaktig rapporterad täckning", wrong_coverage, "coverage_reported_correctly"),
        ("täckning anges fullständig men deltagare saknas", claimed_complete_but_participants_missing, "coverage_reported_correctly"),
        ("rapporterat salstillfälle avviker", reported_session_differs, "room_sessions_reconstructed"),
        ("salstillfälle saknas i rapporten", session_missing_from_report, "room_sessions_reconstructed"),
        ("rapporterat salstillfälle finns inte", phantom_session, "room_sessions_reconstructed"),
        ("saknad tenta", drop_demand, "each_demand_scheduled_once"),
        ("saknad deltagare", lose_participant, "participants_placed"),
        ("överbeläggning med en plats", overbook, "room_capacity"),
        ("överlappande bokningar i samma sal", overlap, "room_turnaround_and_double_booking"),
        ("en minut för kort ställtid", short_turnaround, "room_turnaround_and_double_booking"),
        ("digital tenta i inkompatibel sal", digital_in_paper_room, "digital_compatibility_technical"),
        ("fel ort", wrong_area, "room_planning_area"),
        ("otillåten veckodag", forbidden_weekday, "movable_exams_follow_calendar"),
        ("spärrat datum", blocked_date, "movable_exams_follow_calendar"),
        ("utanför flyttfönstret", outside_window, "movable_exams_follow_calendar"),
        ("oflyttbar tenta flyttad", fixed_exam_moved, "fixed_exams_keep_history"),
        ("för få vakter", too_few_staff, "staffing_per_room_session"),
        ("för liten pool", wrong_pool, "staff_pool_covers_peak"),
        ("överflödig pool under optimalt utfall", inflated_pool, "staff_pool_not_inflated"),
        ("felaktig kostnadskomponent", wrong_cost_component, "costs_recomputed"),
        ("felaktig kostnadssumma", wrong_total, "costs_recomputed"),
        ("solvermål avviker från kostnad", objective_mismatch, "costs_recomputed"),
        ("felaktigt antal flyttar", wrong_changed, "changed_exams_recomputed"),
        ("fiktiv lokal", fictitious_room, "assignments_wellformed"),
        ("samma kurs samtidigt", same_course, "course_conflicts"),
        ("delning över byggnader", split_buildings, "building_split"),
        ("för många salar per tenta", too_many_rooms, "rooms_per_exam"),
        ("sal ej tillgänglig", room_unavailable, "room_availability"),
        ("aktivitet räknad två gånger", double_counted_activity, "no_double_counting"),
        ("hemtenta har fått sal", room_for_home_exam, "non_room_demands"),
        ("referenspass används som val", reference_slot_as_choice, "movable_exams_follow_calendar"),
    ]


def _allow_start(problem: dict, minute: int) -> None:
    for item in problem["parameters"]:
        if item["parameter_id"] == "calendar.start_times":
            item["value"] = item["value"] + [f"{minute // 60:02d}:{minute % 60:02d}"]


class InjectedFaultTests(_Base):
    def test_every_injected_fault_is_found_by_the_expected_rule(self) -> None:
        for name, mutate, expected in _mutations():
            with self.subTest(fault=name):
                problem, result = cases.copy_case()
                mutate(problem, result)
                payload = self.validate(problem, result, "fault")
                self.assertIn(expected, _failing(payload), f"{name}: {expected} borde ha fallerat; föll: {_failing(payload)}")
                self.assertFalse(payload["summary"]["technically_validated"])

    def test_unmutated_case_triggers_none_of_the_faults(self) -> None:
        self.assertEqual(_failing(self.validate(*cases.copy_case())), set())


class BoundaryTests(_Base):
    def test_capacity_exactly_at_the_limit_passes_and_one_seat_less_fails(self) -> None:
        problem, result = cases.copy_case()
        problem["rooms"][1]["capacity"] = 50
        self.assertNotIn("room_capacity", _failing(self.validate(problem, result, "ok")))
        problem["rooms"][1]["capacity"] = 49
        self.assertIn("room_capacity", _failing(self.validate(problem, result, "bad")))

    def test_turnaround_exactly_thirty_minutes_passes_and_twenty_nine_fails(self) -> None:
        for start, expected_fail in ((750, False), (749, True)):
            with self.subTest(start=start):
                problem, result = cases.copy_case()
                problem["slots"][1]["start_minute"] = start
                _allow_start(problem, start)
                row = next(item for item in result["room_sessions"] if item["room_id"] == "R1" and item["slot_id"] == "s2")
                row["available_again_minute"] = start + 120 + 30
                payload = self.validate(problem, result, f"t{start}")
                self.assertEqual("room_turnaround_and_double_booking" in _failing(payload), expected_fail)

    def test_exam_ending_exactly_at_the_latest_end_time_passes_and_one_minute_later_fails(self) -> None:
        for latest, expected_fail in (("16:00", False), ("15:59", True)):  # E starts 14:00 and lasts 2 h
            with self.subTest(latest_end=latest):
                problem, result = cases.copy_case()
                for item in problem["parameters"]:
                    if item["parameter_id"] == "calendar.latest_end_time":
                        item["value"] = latest
                payload = self.validate(problem, result, f"l{latest[:2]}")
                self.assertEqual("movable_exams_follow_calendar" in _failing(payload), expected_fail)

    def test_cost_total_that_does_not_equal_its_components_is_called_out(self) -> None:
        problem, result = cases.copy_case()
        result["costs"]["comparable_total_cost_ore"] = 19601
        payload = self.validate(problem, result)
        self.assertTrue(any("summerar" in text for text in _rules(payload)["costs_recomputed"]["objects"]))

    def test_staffing_ladder_at_every_limit(self) -> None:
        ladder = [(50, 1), (100, 2), (150, 3)]
        expected = {0: 0, 1: 1, 49: 1, 50: 1, 51: 2, 99: 2, 100: 2, 101: 3, 149: 3, 150: 3, 151: None}
        for occupancy, staff in expected.items():
            self.assertEqual(staff_for(occupancy, ladder), staff, occupancy)

    def test_staff_windows_touch_at_fifteen_minutes_and_overlap_at_sixteen(self) -> None:
        for prep, closing, pool, passes in (
            (15, 15, 1, True), (16, 15, 1, False), (15, 16, 1, False), (16, 16, 1, False), (16, 16, 2, True), (0, 0, 1, True),
        ):
            with self.subTest(preparation=prep, closing=closing, pool=pool):
                problem, result = cases.pair_case(prep, closing, pool)
                payload = self.validate(problem, result, f"p{prep}_{closing}_{pool}")
                self.assertEqual("staff_pool_covers_peak" not in _failing(payload), passes)

    def test_pool_one_larger_than_needed_fails_only_when_optimality_is_claimed(self) -> None:
        problem, result = cases.pair_case(15, 15, 2)
        self.assertIn("staff_pool_not_inflated", _failing(self.validate(problem, result, "claimed")))
        result["solver"].update(outcome="feasible_not_proven", best_objective_bound_ore=10000, relative_gap=0.5)
        self.assertNotIn("staff_pool_not_inflated", _failing(self.validate(problem, result, "unclaimed")))

    def test_peak_function_matches_hand_value_on_the_reference_case(self) -> None:
        from tentaoptimering.joint_validation.context import build_context
        from tentaoptimering.joint_validation.derive import build_sessions, staff_by_session
        problem, result = cases.copy_case()
        ctx = build_context(problem, result)
        sessions = build_sessions(ctx)
        self.assertEqual(peak_concurrent_staff(ctx, sessions, staff_by_session(ctx, sessions)), (3, "2026-01-13"))


class EvidenceVersusBreachTests(_Base):
    def test_missing_calendar_parameters_are_not_evaluated_not_failed(self) -> None:
        problem, result = cases.copy_case()
        problem["parameters"] = [item for item in problem["parameters"] if not item["parameter_id"].startswith(("calendar.", "window."))]
        payload = self.validate(problem, result)
        rules = _rules(payload)
        self.assertEqual(rules["movable_exams_follow_calendar"]["status"], "not_evaluated")
        self.assertNotIn("movable_exams_follow_calendar", _failing(payload))

    def test_missing_course_data_is_not_evaluated(self) -> None:
        problem, result = cases.copy_case()
        for demand in problem["demands"]:
            demand["course_code"], demand["conflict_group_ids"] = None, []
        self.assertEqual(_rules(self.validate(problem, result))["course_conflicts"]["status"], "not_evaluated")

    def test_missing_historical_occasion_is_not_evaluated(self) -> None:
        problem, result = cases.copy_case()
        for demand in problem["demands"]:
            demand["original_date"], demand["original_start_minute"], demand["original_slot_id"] = None, None, None
        payload = self.validate(problem, result)
        self.assertEqual(_rules(payload)["movable_exams_follow_calendar"]["status"], "not_evaluated")
        self.assertEqual(_rules(payload)["fixed_exams_keep_history"]["status"], "not_evaluated")

    def test_manipulated_metadata_cannot_give_business_pass(self) -> None:
        """P-3: labels and values stored in the input are claims, never evidence."""
        problem, result = cases.copy_case()
        defined = {item["parameter_id"] for item in problem["parameters"]}
        problem["parameters"] += [cases._param(name, None) for name in ("calendar.exam_periods", "rules.keep_course_order") if name not in defined]
        for item in problem["parameters"]:
            item["basis"], item["engine_support"] = "verified", "implemented"
            item["rationale"] = "verifierad av verksamheten"
        problem["scope"]["unresolved_source_activities"] = 0
        problem["demands"][0]["participant_group_basis"] = "single_activity"
        payload = self.validate(problem, result)
        business = {item["rule_id"]: item["status"] for item in payload["rules"] if item["axis"] == "business"}
        self.assertNotIn("pass", business.values(), business)
        self.assertNotEqual(payload["summary"]["business_verification"], "pass")
        self.assertEqual(business["calendar_rules_verified"], "not_evaluated")
        self.assertEqual(business["population_completeness"], "not_evaluated")
        self.assertIn("märkningen", _rules(payload)["calendar_rules_verified"]["reason"])

    def test_no_user_setting_can_turn_an_unchecked_rule_into_pass(self) -> None:
        problem, result = cases.copy_case()
        problem["parameters"].append(cases._param("program_relation_data_status", "verified"))
        problem["parameters"].append(cases._param("conflict_policy", "same_course_hard_constraint verified"))
        rules = _rules(self.validate(problem, result))
        self.assertEqual(rules["student_overlap"]["status"], "not_evaluated")
        self.assertEqual(rules["digital_compatibility_verified"]["status"], "not_evaluated")

    def test_result_without_solution_has_nothing_to_validate_and_no_partial_placement(self) -> None:
        problem, result = cases.copy_case()
        result.update(schedule=[], assignments=[], room_sessions=[], costs=None, staff_pool_size=None, changed_exam_demands=None)
        result["solver"].update(outcome="infeasible", objective_value_ore=None, best_objective_bound_ore=None, relative_gap=None)
        result["coverage"].update(exam_demands_scheduled=0, participants_assigned_to_rooms=0, non_room_participants_scheduled=0, technical_placement_complete=False)
        payload = self.validate(problem, result)
        rules = _rules(payload)
        self.assertEqual(rules["no_partial_placement"]["status"], "pass")
        self.assertEqual(rules["room_capacity"]["status"], "not_applicable")
        self.assertEqual(payload["summary"]["technical_validation"], "pass")  # only no_partial_placement and wellformed apply
        self.assertEqual(rules["solver_report_consistent"]["status"], "pass")
        problem2, result2 = cases.copy_case()
        result2["solver"].update(outcome="infeasible")
        self.assertIn("no_partial_placement", _failing(self.validate(problem2, result2, "partial")))

    def test_solver_report_must_be_internally_consistent(self) -> None:
        problem, result = cases.copy_case()
        result["solver"]["best_objective_bound_ore"] = 100
        self.assertIn("solver_report_consistent", _failing(self.validate(problem, result)))


class RegressionFromReviewTests(_Base):
    """Review findings: empty schedule, slot-own end limit, undefined parameters, broken rows."""

    def test_optimal_with_empty_schedule_is_not_technically_validated(self) -> None:
        problem, result = cases.copy_case()
        result["schedule"], result["assignments"], result["room_sessions"] = [], [], []
        payload = self.validate(problem, result)
        failing = _failing(payload)
        self.assertIn("each_demand_scheduled_once", failing)
        self.assertIn("participants_placed", failing)
        self.assertFalse(payload["summary"]["technically_validated"])
        self.assertEqual(payload["summary"]["technical_validation"], "fail")

    def test_exam_must_end_within_the_chosen_slots_own_limit(self) -> None:
        for limit, expected_fail in ((960, False), (959, True)):  # E starts 14:00 (840) and lasts 2 h
            with self.subTest(slot_limit=limit):
                problem, result = cases.copy_case()
                for slot in problem["slots"]:
                    if slot["slot_id"] == "s2":
                        slot["latest_end_minute"] = limit
                payload = self.validate(problem, result, f"s{limit}")
                self.assertEqual("slot_end_limit" in _failing(payload), expected_fail)

    def test_a_group_with_an_undefined_parameter_is_never_verified(self) -> None:
        problem, result = cases.copy_case()
        defined = {item["parameter_id"] for item in problem["parameters"]}
        problem["parameters"] += [cases._param(name, None, "verified") for name in ("calendar.exam_periods", "rules.keep_course_order") if name not in defined]
        for item in problem["parameters"]:
            if item["parameter_id"].startswith(("window.", "calendar.", "rules.keep")):
                item["basis"] = "verified"
        problem["parameters"] = [item for item in problem["parameters"] if item["parameter_id"] != "calendar.weekdays"]
        rule = _rules(self.validate(problem, result))["calendar_rules_verified"]
        self.assertEqual(rule["status"], "not_evaluated")
        self.assertIn("calendar.weekdays", rule["objects"])

    def test_broken_rows_give_a_structured_report_not_an_exception(self) -> None:
        broken = {
            "schedule row without demand id": lambda r: r["schedule"].append({"slot_id": "s1"}),
            "schedule row without slot": lambda r: r["schedule"][0].pop("slot_id"),
            "schedule row not an object": lambda r: r["schedule"].append("x"),
            "assignment without participants": lambda r: r["assignments"][0].pop("participants"),
            "assignment with text participants": lambda r: r["assignments"][0].update(participants="många"),
            "assignment without room": lambda r: r["assignments"][0].pop("room_id"),
            "schedule is not a list": lambda r: r.update(schedule={"a": 1}),
            "session row not an object": lambda r: r["room_sessions"].append(7),
            "solver is not an object": lambda r: r.update(solver="optimal"),
        }
        for name, mutate in broken.items():
            with self.subTest(name):
                problem, result = cases.copy_case()
                mutate(result)
                payload = self.validate(problem, result, name.replace(" ", "_"))
                self.assertFalse(payload["summary"]["technically_validated"])
                self.assertEqual(payload["summary"]["technical_validation"], "fail")


class IntegrityTests(_Base):
    def test_changed_result_file_breaks_the_manifest(self) -> None:
        directory = cases.write_run(self.dir / "run", *cases.copy_case())
        path = directory / "joint_result.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        result["changed_exam_demands"] = 0
        path.write_text(json.dumps(result), encoding="utf-8")
        payload = validate_run(directory)
        self.assertIn("manifest_hashes", _failing(payload))
        self.assertEqual(payload["summary"]["provenance"], "fail")

    def test_changed_input_file_breaks_the_manifest(self) -> None:
        directory = cases.write_run(self.dir / "run", *cases.copy_case())
        path = directory / "joint_input.json"
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self.assertIn("manifest_hashes", _failing(validate_run(directory)))

    def test_broken_manifest_is_a_failure_and_missing_manifest_is_not_evaluated(self) -> None:
        directory = cases.write_run(self.dir / "run", *cases.copy_case())
        manifest = json.loads((directory / "joint_manifest.json").read_text(encoding="utf-8"))
        manifest["input_sha256"] = "0" * 64
        (directory / "joint_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn("manifest_hashes", _failing(validate_run(directory)))
        (directory / "joint_manifest.json").unlink()
        payload = validate_run(directory)
        self.assertEqual(_rules(payload)["manifest_hashes"]["status"], "not_evaluated")
        self.assertIn("artifacts_present_and_readable", _failing(payload))

    def test_unreadable_or_missing_artifacts_are_reported(self) -> None:
        directory = cases.write_run(self.dir / "run", *cases.copy_case())
        (directory / "joint_result.json").write_text("{not json", encoding="utf-8")
        payload = validate_run(directory)
        self.assertIn("artifacts_present_and_readable", _failing(payload))
        self.assertEqual(payload["summary"]["technical_validation"], "not_applicable")

    def test_wrong_schema_version_or_foreign_result_fails(self) -> None:
        problem, result = cases.copy_case()
        result["schema_version"] = "joint-optimization-result-v1"
        result["problem_id"] = "another-problem"
        failing = _failing(self.validate(problem, result))
        self.assertIn("schema_versions", failing)
        self.assertIn("result_belongs_to_input", failing)

    def test_dataset_hash_is_checked_against_the_processed_files(self) -> None:
        import hashlib
        processed = self.dir / "processed"
        processed.mkdir()
        digest = hashlib.sha256()
        for name in ("optimization_demands.csv", "optimization_rooms.csv", "demand_scope.csv"):
            (processed / name).write_text(name, encoding="utf-8")
            digest.update(bytes.fromhex(hashlib.sha256((processed / name).read_bytes()).hexdigest()))
        problem, result = cases.copy_case()
        problem["dataset_hash"] = digest.hexdigest()
        self.assertEqual(_rules(self.validate(problem, result, "ok", processed_dir=processed))["dataset_hash"]["status"], "pass")
        (processed / "demand_scope.csv").write_text("changed", encoding="utf-8")
        self.assertEqual(_rules(self.validate(problem, result, "bad", processed_dir=processed))["dataset_hash"]["status"], "fail")
        self.assertEqual(_rules(self.validate(problem, result, "none"))["dataset_hash"]["status"], "not_evaluated")

    def test_source_files_are_hash_checked_when_a_manifest_is_given(self) -> None:
        import hashlib
        source = self.dir / "source"
        source.mkdir()
        (source / "a.xlsx").write_bytes(b"raw")
        manifest = self.dir / "run_manifest.json"
        manifest.write_text(json.dumps({"sources": {"a": {"filename": "a.xlsx", "sha256": hashlib.sha256(b"raw").hexdigest()}}}), encoding="utf-8")
        problem, result = cases.copy_case()
        args = dict(source_dir=source, source_manifest=manifest)
        self.assertEqual(_rules(self.validate(problem, result, "ok", **args))["source_data_hashes"]["status"], "pass")
        (source / "a.xlsx").write_bytes(b"changed")
        self.assertEqual(_rules(self.validate(problem, result, "bad", **args))["source_data_hashes"]["status"], "fail")


class IndependenceTests(unittest.TestCase):
    def test_validator_shares_only_contract_constants_with_the_optimizer(self) -> None:
        package = REPO_ROOT / "src" / "tentaoptimering" / "joint_validation"
        own = {path.stem for path in package.glob("*.py")}
        for path in package.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(alias.name.startswith("tentaoptimering"), f"{path.name} importerar {alias.name}")
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level == 0:
                    self.assertFalse((node.module or "").startswith("tentaoptimering"), f"{path.name} importerar {node.module}")
                elif node.level == 1:
                    self.assertTrue(node.module is None or node.module in own, f"{path.name} importerar {node.module}")
                else:
                    self.assertEqual(node.module, "joint_contract", f"{path.name}: endast kontraktskonstanter får delas")
                    self.assertEqual({alias.name for alias in node.names}, {"INPUT_SCHEMA_VERSION", "RESULT_SCHEMA_VERSION"})


if __name__ == "__main__":
    unittest.main()
