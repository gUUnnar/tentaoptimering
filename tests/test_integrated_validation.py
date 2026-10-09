from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from tentaoptimering.integrated_validation import validate_integrated_term_run, write_validation_report
from tentaoptimering.run_integrity import write_run_integrity_manifest


SCENARIO = '''
scenario_id = "validation-test"
description = "test"
[calendar]
start_date = "2026-01-12"
end_date = "2026-01-12"
allowed_weekdays = [1]
turnaround_minutes = 30
[[calendar.passes]]
pass_id = "am"
start_time = "08:00"
latest_end_time = "12:00"
[[calendar.passes]]
pass_id = "pm"
start_time = "10:00"
latest_end_time = "14:00"
[compatibility]
digital_compatibility_mode = "all_exploratory_candidate_rooms_assumed_compatible_with_observed_formats"
[staffing]
staff_per_room_session = 1
annual_cost_ore_per_staff = 1
[costs]
annual_room_cost_ore_per_seat = 1
[[assumption]]
id = "room_availability"
value = "all selected candidate rooms available for every configured slot"
unit = "availability_mode"
source = "test"
rationale = "test"
status = "test"
'''


class IntegratedValidationTests(unittest.TestCase):
    def _run_dir(self, assignments: list[dict[str, object]], staff_pool: int = 1) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        (directory / "scenario.toml").write_text(SCENARIO, encoding="utf-8")
        inputs = {
            "demands": [
                {"exam_demand_id": "demand-1", "participants": 10, "duration_minutes": 120, "plan_area": "Uppsala", "allowed_pass_ids": None},
                {"exam_demand_id": "demand-2", "participants": 10, "duration_minutes": 120, "plan_area": "Uppsala", "allowed_pass_ids": None},
            ],
            "rooms": [
                {"room_id": "room-u", "capacity": 10, "plan_area": "Uppsala", "annual_cost_ore": 1},
                {"room_id": "room-u2", "capacity": 10, "plan_area": "Uppsala", "annual_cost_ore": 1},
                {"room_id": "room-u3", "capacity": 10, "plan_area": "Uppsala", "annual_cost_ore": 1},
                {"room_id": "room-v", "capacity": 10, "plan_area": "Visby", "annual_cost_ore": 1},
            ],
            "demand_traceability": [
                {"exam_demand_id": "demand-1", "source_activity_id": "demand-1", "course_code": "COURSE"},
                {"exam_demand_id": "demand-2", "source_activity_id": "demand-2", "course_code": "COURSE"},
            ],
            "scope_metrics": {
                "source_activities_total": 2,
                "included_source_activities": 2,
                "unresolved_source_activities": 0,
                "excluded_source_activities": 0,
                "model_ready_exam_demands": 2,
            },
            "scope_decisions": [
                {"activity_id": "demand-1", "scope_status": "included", "scope_reason_code": "test"},
                {"activity_id": "demand-2", "scope_status": "included", "scope_reason_code": "test"},
            ],
        }
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        (directory / "result.json").write_text(json.dumps({"run_id": "test", "solution": {"anonymous_staff_pool_size": staff_pool}}), encoding="utf-8")
        pd.DataFrame(assignments).to_csv(directory / "assignments.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(directory / "room_sessions.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(directory / "staff_assignments.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(inputs["demand_traceability"]).to_csv(directory / "demand_traceability.csv", index=False, encoding="utf-8-sig")
        write_run_integrity_manifest(directory, "test")
        return directory

    def _rules(self, report: dict[str, object]) -> dict[str, dict[str, object]]:
        return {item["rule_id"]: item for item in report["rules"]}  # type: ignore[index]

    def test_full_technical_placement_can_still_be_business_not_verified(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        report = validate_integrated_term_run(directory)

        self.assertEqual(report["technical_placement_completeness"]["status"], "pass")
        self.assertEqual(report["business_feasibility"]["status"], "not_verified")
        self.assertEqual(self._rules(report)["course_program_conflicts"]["status"], "not_evaluated")
        self.assertTrue((directory / "validation.json").exists() is False)
        write_validation_report(directory)
        self.assertTrue((directory / "validation.json").is_file())
        self.assertTrue((directory / "validation.md").is_file())

    def test_rejects_changed_frozen_scenario_and_model_inputs(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        scenario = (directory / "scenario.toml").read_text(encoding="utf-8")
        (directory / "scenario.toml").write_text(scenario.replace('latest_end_time = "12:00"', 'latest_end_time = "11:00"'), encoding="utf-8")
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["run_artifact_integrity"]["status"], "fail")

    def test_editable_status_cannot_promote_program_conflict_rule_to_pass(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        scenario = (directory / "scenario.toml").read_text(encoding="utf-8")
        (directory / "scenario.toml").write_text(
            scenario + '\n[conflicts]\npolicy = "same_course_hard_constraint"\nprogram_relation_data_status = "verified"\n',
            encoding="utf-8",
        )
        write_run_integrity_manifest(directory, "test")
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["run_artifact_integrity"]["status"], "pass")
        self.assertEqual(rules["course_program_conflicts"]["status"], "not_evaluated")

    def test_reports_unresolved_source_activities_without_marking_them_placed(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        inputs = json.loads((directory / "model_inputs.json").read_text(encoding="utf-8"))
        inputs["scope_metrics"].update({"source_activities_total": 3, "unresolved_source_activities": 1})
        inputs["scope_decisions"].append({"activity_id": "unresolved-1", "scope_status": "unresolved", "scope_reason_code": "missing_link"})
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        write_run_integrity_manifest(directory, "test")
        report = validate_integrated_term_run(directory)
        rules = self._rules(report)

        self.assertEqual(report["technical_placement_completeness"]["status"], "pass")
        self.assertEqual(rules["unresolved_source_activities"]["status"], "not_evaluated")
        self.assertEqual(report["scope"]["unresolved_activity_ids"], ["unresolved-1"])

    def test_rejects_scope_metrics_that_do_not_match_saved_decisions(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        inputs = json.loads((directory / "model_inputs.json").read_text(encoding="utf-8"))
        inputs["scope_metrics"]["included_source_activities"] = 3
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        write_run_integrity_manifest(directory, "test")

        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["source_scope_accounting"]["status"], "fail")

    def test_detects_missing_or_double_counted_participants_and_capacity(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 20},
            {"exam_demand_id": "demand-2", "room_id": "room-u", "slot_id": "2026-01-12-pm", "participants": 10},
        ])
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["included_demand_coverage"]["status"], "fail")
        self.assertEqual(rules["room_capacity"]["status"], "fail")

    def test_detects_split_start_for_one_exam_demand(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 5},
            {"exam_demand_id": "demand-1", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 5},
            {"exam_demand_id": "demand-2", "room_id": "room-u3", "slot_id": "2026-01-12-am", "participants": 10},
        ], staff_pool=3)
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["included_demand_coverage"]["status"], "fail")

    def test_detects_overlapping_passes_in_same_room(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["room_time_intervals"]["status"], "fail")

    def test_detects_plan_area_and_aggregate_staffing_failures(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-v", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=1)
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["plan_area"]["status"], "fail")
        self.assertEqual(rules["aggregate_staffing"]["status"], "fail")

    def test_accepts_overstaffing_but_rejects_invalid_rows(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=3)
        self.assertEqual(self._rules(validate_integrated_term_run(directory))["aggregate_staffing"]["status"], "pass")

        invalid = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "unknown-room", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "unknown-slot", "participants": -10},
        ])
        self.assertEqual(self._rules(validate_integrated_term_run(invalid))["assignment_rows"]["status"], "fail")

    def test_rejects_invalid_demand_and_room_model_inputs(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        inputs = json.loads((directory / "model_inputs.json").read_text(encoding="utf-8"))
        inputs["demands"][0]["participants"] = 0
        inputs["rooms"][0]["capacity"] = -1
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["model_inputs"]["status"], "fail")

    def test_detects_duration_outside_pass_and_disallowed_pass(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        scenario = (directory / "scenario.toml").read_text(encoding="utf-8")
        (directory / "scenario.toml").write_text(scenario.replace('latest_end_time = "12:00"', 'latest_end_time = "09:00"'), encoding="utf-8")
        inputs = json.loads((directory / "model_inputs.json").read_text(encoding="utf-8"))
        inputs["demands"][1]["allowed_pass_ids"] = ["am"]
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["calendar_pass_constraints"]["status"], "fail")

    def test_marks_unconfigured_digital_and_availability_rules_not_evaluated(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u", "slot_id": "2026-01-12-pm", "participants": 10},
        ])
        scenario = (directory / "scenario.toml").read_text(encoding="utf-8")
        (directory / "scenario.toml").write_text(scenario.replace("all_exploratory_candidate_rooms_assumed_compatible_with_observed_formats", "not_configured").replace("all selected candidate rooms available for every configured slot", "not_configured"), encoding="utf-8")
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["digital_compatibility"]["status"], "not_evaluated")
        self.assertEqual(rules["room_availability"]["status"], "not_evaluated")

    def test_detects_explicit_digital_availability_and_course_conflict_failures(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        scenario = (directory / "scenario.toml").read_text(encoding="utf-8")
        (directory / "scenario.toml").write_text(
            scenario.replace('start_time = "10:00"', 'start_time = "09:00"')
            + '\n[conflicts]\npolicy = "same_course_hard_constraint; program_relation_when_source_available"\nprogram_relation_data_status = "verified"\n',
            encoding="utf-8",
        )
        inputs = json.loads((directory / "model_inputs.json").read_text(encoding="utf-8"))
        for demand in inputs["demands"]:
            demand["course_code"] = "COURSE"
            demand["digital_requirement"] = "e_exam"
        inputs["rooms"][0]["digital_capabilities"] = ["paper"]
        inputs["rooms"][0]["available_slot_ids"] = ["2026-01-12-pm"]
        inputs["rooms"][1]["digital_capabilities"] = ["e_exam"]
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")

        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["digital_compatibility"]["status"], "fail")
        self.assertEqual(rules["room_availability"]["status"], "fail")
        self.assertEqual(rules["course_program_conflicts"]["status"], "fail")

    def test_validates_persisted_individual_staffing_assignments(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 10},
            {"exam_demand_id": "demand-2", "room_id": "room-u2", "slot_id": "2026-01-12-pm", "participants": 10},
        ], staff_pool=2)
        pd.DataFrame([
            {"staff_id": "staff-1", "task_id": "room-u|2026-01-12-am", "scheduled_date": "2026-01-12", "start_minute": 480, "end_minute": 630, "building_id": "room-u", "travel_before_minutes": 0},
            {"staff_id": "staff-2", "task_id": "room-u2|2026-01-12-pm", "scheduled_date": "2026-01-12", "start_minute": 600, "end_minute": 750, "building_id": "room-u2", "travel_before_minutes": 0},
        ]).to_csv(directory / "staff_assignments.csv", index=False, encoding="utf-8-sig")

        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["individual_staffing_constraints"]["status"], "not_evaluated")


if __name__ == "__main__":
    unittest.main()
