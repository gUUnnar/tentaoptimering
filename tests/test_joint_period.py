"""The choice of planning period: coverage from the data, the check of a period, and the scenario it gives.

Synthetic demand/booking files give exact expected counts; the rules are the ones in `joint_period` (an exam is in the
period by its historical date, the calendar is cut to the period, nothing outside the demand data is invented).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from tentaoptimering.joint_period import PLANNING_BASIS, PeriodError, PeriodRequest, coverage_payload, period_report, with_period

READY, MISSING = "ready_provisional_ladok_demand", "missing_configured_demand_value"
# (event, date, status, city)
DEMANDS = [
    ("e1", "2026-01-12", READY, "Uppsala"), ("e2", "2026-01-12", READY, "Uppsala"), ("e3", "2026-01-13", MISSING, "Uppsala"),
    ("e4", "2026-01-20", READY, "Uppsala"), ("e5", "2026-03-31", READY, "Uppsala"), ("e6", "2026-01-20", READY, "Visby"),
]
SCENARIO = {"schema_version": "joint-real-subset-v1", "scenario": {"id": "s"},
            "subset": {"plan_area": "Uppsala", "selection": "all_ready", "date_from": "2026-01-12", "date_to": "2026-03-31"},
            "parameters": {"window.earlier_days": 1}}


class PeriodTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.dir = Path(self._dir.name)
        pd.DataFrame({"exam_event_id": [d[0] for d in DEMANDS], "scheduled_date": [d[1] for d in DEMANDS],
                      "demand_input_status": [d[2] for d in DEMANDS], "observed_cities": [d[3] for d in DEMANDS]}
                     ).to_csv(self.dir / "optimization_demands.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame({"scheduled_date": ["2025-09-01", "2026-08-29"]}).to_csv(self.dir / "bookings.csv", index=False, encoding="utf-8-sig")

    def test_coverage_comes_from_the_data_per_area(self) -> None:
        payload = coverage_payload(self.dir, "Uppsala")
        self.assertEqual(payload["demand"]["first"], "2026-01-12")
        self.assertEqual(payload["demand"]["last"], "2026-03-31")
        self.assertEqual((payload["demand"]["ready_events"], payload["demand"]["not_ready_events"]), (4, 1))
        self.assertEqual({row["date"]: (row["ready"], row["not_ready"]) for row in payload["days"]},
                         {"2026-01-12": (2, 0), "2026-01-13": (0, 1), "2026-01-20": (1, 0), "2026-03-31": (1, 0)})
        self.assertEqual(payload["bookings"]["last"], "2026-08-29")  # shown, but no demand there
        self.assertEqual(payload["planning_basis"], PLANNING_BASIS)

    def test_without_data_nothing_is_claimed(self) -> None:
        payload = coverage_payload(self.dir / "missing", "Uppsala")
        self.assertFalse(payload["data_available"])
        self.assertIsNone(payload["demand"])

    def test_one_day_and_one_week(self) -> None:
        day = period_report(self.dir, "Uppsala", date(2026, 1, 12), date(2026, 1, 12))
        self.assertTrue(day["can_plan"])
        self.assertEqual((day["ready_events"], day["not_ready_events"]), (2, 0))
        week = period_report(self.dir, "Uppsala", date(2026, 1, 12), date(2026, 1, 18))
        self.assertEqual((week["ready_events"], week["not_ready_events"]), (2, 1))
        self.assertTrue(any("saknar deltagarantal" in text for text in week["warnings"]))

    def test_period_outside_coverage_is_refused_with_a_reason(self) -> None:
        april = period_report(self.dir, "Uppsala", date(2026, 4, 1), date(2026, 4, 30))
        self.assertFalse(april["can_plan"])
        self.assertIn("utanför efterfrågeunderlaget", april["error"])
        self.assertIn("2026-01-12", april["error"])

    def test_period_reaching_outside_is_cut_and_says_so(self) -> None:
        report = period_report(self.dir, "Uppsala", date(2026, 3, 25), date(2026, 4, 30))
        self.assertTrue(report["can_plan"])
        self.assertEqual((report["planned_from"], report["planned_to"]), ("2026-03-25", "2026-03-31"))
        self.assertTrue(any("okänd, inte tom" in text for text in report["warnings"]))

    def test_empty_and_reversed_periods(self) -> None:
        self.assertIn("inga tentor", period_report(self.dir, "Uppsala", date(2026, 2, 1), date(2026, 2, 5))["error"].lower())
        self.assertIn("senare", period_report(self.dir, "Uppsala", date(2026, 2, 5), date(2026, 2, 1))["error"])

    def test_scenario_for_period_is_a_copy_with_subset_and_calendar_cut(self) -> None:
        merged = with_period(SCENARIO, self.dir, PeriodRequest(date_from=date(2026, 1, 12), date_to=date(2026, 1, 20)))
        self.assertEqual((merged["subset"]["date_from"], merged["subset"]["date_to"]), ("2026-01-12", "2026-01-20"))
        self.assertEqual((merged["parameters"]["calendar.start_date"], merged["parameters"]["calendar.end_date"]), ("2026-01-12", "2026-01-20"))
        self.assertEqual(SCENARIO["subset"]["date_to"], "2026-03-31")  # the original is untouched
        self.assertNotIn("calendar.start_date", SCENARIO["parameters"])

    def test_scenario_with_named_exams_cannot_take_a_period(self) -> None:
        named = {**SCENARIO, "subset": {"plan_area": "Uppsala", "exam_event_ids": ["e1"]}}
        with self.assertRaises(PeriodError):
            with_period(named, self.dir, PeriodRequest(date_from=date(2026, 1, 12), date_to=date(2026, 1, 12)))


class RunDirectoryTests(unittest.TestCase):
    def test_runs_started_in_the_same_second_get_distinct_ordered_ids(self) -> None:
        from tentaoptimering.joint_inputs import _new_run_directory
        with tempfile.TemporaryDirectory() as folder:
            ids = [_new_run_directory(Path(folder) / "runs", "p")[0] for _ in range(4)]
        self.assertEqual(len(set(ids)), 4)
        self.assertEqual(ids, sorted(ids))
        self.assertTrue(all(item.endswith("Z-p") and item[8] == "T" for item in ids))


if __name__ == "__main__":
    unittest.main()
