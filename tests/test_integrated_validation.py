from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from tentaoptimering.integrated_validation import validate_integrated_term_run, write_validation_report


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
                {"room_id": "room-v", "capacity": 10, "plan_area": "Visby", "annual_cost_ore": 1},
            ],
            "demand_traceability": [{"exam_demand_id": "demand-1", "course_code": "COURSE"}],
            "scope_metrics": {},
        }
        (directory / "model_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")
        (directory / "result.json").write_text(json.dumps({"run_id": "test", "solution": {"anonymous_staff_pool_size": staff_pool}}), encoding="utf-8")
        pd.DataFrame(assignments).to_csv(directory / "assignments.csv", index=False, encoding="utf-8-sig")
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

    def test_detects_missing_or_double_counted_participants_and_capacity(self) -> None:
        directory = self._run_dir([
            {"exam_demand_id": "demand-1", "room_id": "room-u", "slot_id": "2026-01-12-am", "participants": 20},
            {"exam_demand_id": "demand-2", "room_id": "room-u", "slot_id": "2026-01-12-pm", "participants": 10},
        ])
        rules = self._rules(validate_integrated_term_run(directory))

        self.assertEqual(rules["included_demand_coverage"]["status"], "fail")
        self.assertEqual(rules["room_capacity"]["status"], "fail")

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


if __name__ == "__main__":
    unittest.main()
