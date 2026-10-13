"""A run for a chosen period goes through the ordinary engine, API, independent validation and summary.

Uses the locally prepared data (skipped without it): a single day and a week of the underlay are run with `period` in the
request, and the result is compared with an independent pandas count of the exams in the period.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_api import _wait_for_end  # noqa: E402
from test_joint_validation_run import CATALOG, PROCESSED  # noqa: E402
from tentaoptimering import joint_api  # noqa: E402
from tentaoptimering.app_storage import AppStorage  # noqa: E402
from tentaoptimering.job_manager import LocalJobManager  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest  # noqa: E402
from tentaoptimering.joint_period import PeriodRequest  # noqa: E402
from tentaoptimering.parameter_catalog import load_parameter_catalog  # noqa: E402

SCENARIO = "joint_underlay_period"
READY = "ready_provisional_ladok_demand"


@unittest.skipUnless((PROCESSED / "optimization_demands.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class PeriodRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.storage = AppStorage(Path(cls.temp.name))
        shutil.copytree(PROCESSED, cls.storage.processed_dir, dirs_exist_ok=True)
        cls.jobs = LocalJobManager()
        cls.demands = pd.read_csv(PROCESSED / "optimization_demands.csv", encoding="utf-8-sig")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.jobs.shutdown()
        cls.temp.cleanup()

    def _run(self, first: str, last: str) -> tuple[dict, dict]:
        request = JointRunRequest(scenario=SCENARIO, warm_start="none", threads=2, period=PeriodRequest(date_from=first, date_to=last))
        end = _wait_for_end(self.jobs, joint_api.start_joint_run(self.jobs, self.storage, request)["job_id"], seconds=300)
        self.assertEqual(end["status"], "completed", end.get("error"))
        return end, joint_api.run_summary(self.storage, end["run_id"])

    def _expected_events(self, first: str, last: str) -> int:
        rows = self.demands[(self.demands["demand_input_status"] == READY) & (self.demands["observed_cities"] == "Uppsala")]
        return int(rows[(rows["scheduled_date"] >= first) & (rows["scheduled_date"] <= last)]["exam_event_id"].nunique())

    def test_a_single_day_is_planned_completely_and_verified(self) -> None:
        _, summary = self._run("2026-02-09", "2026-02-09")
        self.assertEqual(summary["exams_total"], self._expected_events("2026-02-09", "2026-02-09"))
        self.assertTrue(summary["has_verified_solution"])
        self.assertTrue(summary["technical_placement_complete"])
        self.assertEqual(summary["verdicts"]["technical_validation"], "pass")
        self.assertEqual(summary["period"], {"date_from": "2026-02-09", "date_to": "2026-02-09", "requested_from": "2026-02-09",
                                               "requested_to": "2026-02-09", "partial": False, "partial_accepted": False})

    def test_the_result_is_marked_exploratory_and_its_cost_is_not_a_period_cost(self) -> None:
        _, summary = self._run("2026-02-09", "2026-02-15")
        self.assertEqual(summary["exams_total"], self._expected_events("2026-02-09", "2026-02-15"))
        basis = summary["planning_basis"]
        self.assertEqual((basis["mode"], basis["fixed_bookings_considered"]), ("exploratory", False))
        self.assertIn("inte kostnaden för perioden", basis["cost_note"])

    def test_a_partly_covered_period_runs_only_after_approval_and_the_result_shows_both_periods(self) -> None:
        request = dict(scenario=SCENARIO, warm_start="none", threads=2)
        asked = dict(date_from="2026-03-30", date_to="2026-04-30")
        with self.assertRaisesRegex(ValueError, "Godkänn uttryckligen"):
            joint_api.start_joint_run(self.jobs, self.storage, JointRunRequest(**request, period=PeriodRequest(**asked)))
        end = _wait_for_end(self.jobs, joint_api.start_joint_run(
            self.jobs, self.storage, JointRunRequest(**request, period=PeriodRequest(**asked, accept_partial=True)))["job_id"], seconds=300)
        self.assertEqual(end["status"], "completed", end.get("error"))
        period = joint_api.run_summary(self.storage, end["run_id"])["period"]
        self.assertEqual(period, {"date_from": "2026-03-30", "date_to": "2026-03-31", "requested_from": "2026-03-30",
                                  "requested_to": "2026-04-30", "partial": True, "partial_accepted": True})

    def test_the_cost_is_an_annual_capacity_cost_that_follows_from_rooms_and_the_staff_pool(self) -> None:
        for first, last in (("2026-02-09", "2026-02-09"), ("2026-02-09", "2026-02-15")):
            with self.subTest(period=(first, last)):
                end, summary = self._run(first, last)
                result = json.loads((self.storage.run_directory(end["run_id"]) / "joint_result.json").read_text(encoding="utf-8"))
                costs, staff_annual = result["costs"], 5_000_000  # cost.staff_annual_ore of the scenario
                self.assertEqual(costs["annual_staff_pool_cost_ore"], result["staff_pool_size"] * staff_annual)
                self.assertEqual(costs["comparable_total_cost_ore"], costs["annual_room_cost_ore"] + costs["external_room_session_cost_ore"]
                                 + costs["annual_staff_pool_cost_ore"] + costs["staff_session_cost_ore"])
                self.assertEqual(summary["cost_ore"], costs["comparable_total_cost_ore"])
                self.assertEqual(summary["planning_basis"]["cost_name"], "Modellerad årlig kapacitetskostnad för valt urval")

    def test_runs_of_different_periods_are_not_compared_as_equal(self) -> None:
        (day, _), (week, _) = self._run("2026-02-09", "2026-02-09"), self._run("2026-02-09", "2026-02-15")
        result = joint_api.compare_runs(self.storage, week["run_id"], day["run_id"], load_parameter_catalog(CATALOG))
        self.assertFalse(result["comparable"])
        self.assertIn("olika uppsättningar tentor", result["reason"])

    def test_a_period_outside_the_data_is_refused_before_any_job_starts(self) -> None:
        request = JointRunRequest(scenario=SCENARIO, period=PeriodRequest(date_from="2026-05-04", date_to="2026-05-08"))
        with self.assertRaisesRegex(ValueError, "utanför efterfrågeunderlaget"):
            joint_api.start_joint_run(self.jobs, self.storage, request)

    def test_a_period_cannot_be_combined_with_calendar_dates_as_parameters(self) -> None:
        request = JointRunRequest(scenario=SCENARIO, period=PeriodRequest(date_from="2026-02-09", date_to="2026-02-09"),
                                  parameters={"calendar.start_date": "2026-02-01"})
        with self.assertRaisesRegex(ValueError, "calendar.start_date"):
            joint_api.start_joint_run(self.jobs, self.storage, request)

    def test_the_period_check_over_the_api_function_matches_the_data(self) -> None:
        payload = joint_api.period_payload_for(self.storage, SCENARIO, "2026-02-09", "2026-02-15")
        self.assertEqual(payload["check"]["ready_events"], self._expected_events("2026-02-09", "2026-02-15"))
        self.assertEqual(payload["demand"]["first"], "2026-01-12")
        self.assertEqual(payload["demand"]["last"], "2026-03-31")
        self.assertIsNone(joint_api.period_payload_for(self.storage, SCENARIO)["check"])


if __name__ == "__main__":
    unittest.main()
