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

from tentaoptimering import joint_period
from tentaoptimering.joint_period import PeriodError, PeriodRequest, coverage_payload, period_report, with_period

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
        self.assertEqual(payload["planning_basis"], joint_period.planning_basis(self.dir))

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

    def test_a_partly_covered_period_needs_the_users_explicit_approval(self) -> None:
        asked = dict(date_from=date(2026, 1, 1), date_to=date(2026, 4, 30))
        report = period_report(self.dir, "Uppsala", asked["date_from"], asked["date_to"])
        self.assertTrue(report["partial"])
        self.assertEqual((report["planned_from"], report["planned_to"]), ("2026-01-12", "2026-03-31"))
        self.assertIn("inte hela den valda perioden", " ".join(report["warnings"]))
        with self.assertRaisesRegex(PeriodError, "Godkänn uttryckligen den kortare perioden 2026-01-12–2026-03-31"):
            with_period(SCENARIO, self.dir, PeriodRequest(**asked))
        merged = with_period(SCENARIO, self.dir, PeriodRequest(**asked, accept_partial=True))
        self.assertEqual(merged["period"], {"requested_from": "2026-01-01", "requested_to": "2026-04-30", "planned_from": "2026-01-12",
                                            "planned_to": "2026-03-31", "partial": True, "partial_accepted": True})
        self.assertEqual(merged["parameters"]["calendar.end_date"], "2026-03-31")

    def test_a_fully_covered_period_is_not_partial_and_needs_no_approval(self) -> None:
        merged = with_period(SCENARIO, self.dir, PeriodRequest(date_from=date(2026, 1, 12), date_to=date(2026, 1, 20)))
        self.assertFalse(merged["period"]["partial"])
        self.assertFalse(period_report(self.dir, "Uppsala", date(2026, 1, 12), date(2026, 3, 31))["partial"])

    def test_scenario_with_named_exams_cannot_take_a_period(self) -> None:
        named = {**SCENARIO, "subset": {"plan_area": "Uppsala", "exam_event_ids": ["e1"]}}
        with self.assertRaises(PeriodError):
            with_period(named, self.dir, PeriodRequest(date_from=date(2026, 1, 12), date_to=date(2026, 1, 12)))


class PlanningBasisTests(unittest.TestCase):
    """The reading of a result is derived from what the engine can do and what the data says, so it can change without code."""

    def _dir(self, operational: str = "False", demand: bool = True) -> Path:
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(folder, ignore_errors=True))
        pd.DataFrame({"room_id": ["r1", "r2"], "eligible_for_exploratory_capacity_poc": ["True", "True"],
                      "eligible_for_operational_scheduling": [operational, "True"]}).to_csv(folder / "optimization_rooms.csv", index=False)
        if demand:
            pd.DataFrame({"exam_event_id": ["e"], "scheduled_date": ["2026-01-12"], "demand_input_status": [READY], "observed_cities": ["Uppsala"]}).to_csv(
                folder / "optimization_demands.csv", index=False)
        return folder

    def test_today_it_is_exploratory_with_each_reason_stated(self) -> None:
        basis = joint_period.planning_basis(self._dir())
        codes = [item["code"] for item in basis["reasons"]]
        self.assertEqual((basis["mode"], basis["fixed_bookings_considered"]), ("exploratory", False))
        self.assertEqual(codes, ["external_bookings_not_modelled", "rooms_not_operationally_approved", "demand_provisional"])
        self.assertIn("1 av 2 salar", basis["reasons"][1]["text"])

    def test_approved_rooms_remove_that_reason_and_the_room_check_follows_the_rooms_used(self) -> None:
        self.assertNotIn("rooms_not_operationally_approved", [item["code"] for item in joint_period.planning_basis(self._dir("True"))["reasons"]])
        only_r2 = joint_period.planning_basis(self._dir("False"), {"r2"})  # r1 is the unapproved one; the run did not use it
        self.assertNotIn("rooms_not_operationally_approved", [item["code"] for item in only_r2["reasons"]])

    def test_it_becomes_reliable_only_when_no_reason_holds(self) -> None:
        folder = self._dir("True")
        saved = joint_period.ENGINE_MODELS_EXTERNAL_BOOKINGS, joint_period.READY_STATUS
        self.addCleanup(lambda: (setattr(joint_period, "ENGINE_MODELS_EXTERNAL_BOOKINGS", saved[0]), setattr(joint_period, "READY_STATUS", saved[1])))
        joint_period.ENGINE_MODELS_EXTERNAL_BOOKINGS, joint_period.READY_STATUS = True, "ready_confirmed"
        basis = joint_period.planning_basis(folder)
        self.assertEqual((basis["mode"], basis["reasons"], basis["label"]), ("reliable", [], "Tillförlitlig planering"))

    def test_without_a_room_register_nothing_is_approved(self) -> None:
        basis = joint_period.planning_basis(Path(tempfile.mkdtemp()))
        self.assertIn("room_register_missing", [item["code"] for item in basis["reasons"]])


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
