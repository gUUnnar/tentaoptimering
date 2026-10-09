from __future__ import annotations

from datetime import date
import unittest

from tentaoptimering.integrated_config import IntegratedTermScenario
from tentaoptimering.integrated_inputs import TermModelInputs
from tentaoptimering.integrated_term import IntegratedDemand, IntegratedRoom
from tentaoptimering.staffing import StaffingPolicy, StaffingStep, WorkShift
from tentaoptimering.term_calendar import CalendarPass, TermCalendar
from tentaoptimering.term_run import run_first_term_schedule


class TermRunTests(unittest.TestCase):
    def test_persisted_staff_times_include_preparation_and_only_one_closing_period(self) -> None:
        scenario = IntegratedTermScenario(
            "test", "test", TermCalendar(date(2026, 1, 12), date(2026, 1, 12), (1,), (CalendarPass("day", "08:00", "12:00"),), 30),
            1, 1, 1, "test", "same_course_hard_constraint", "verified",
            StaffingPolicy((StaffingStep(20, 1),), (WorkShift("day", 7 * 60, 13 * 60),), 30, 30, 30, 360, 360, 660, 0), 0, (),
        )
        inputs = TermModelInputs(
            (IntegratedDemand("demand", 10, 120, "Uppsala"),),
            (IntegratedRoom("room", 20, "Uppsala", 1),), (),
            {"included_source_activities": 1, "source_activities_total": 1, "unresolved_source_activities": 0},
        )

        result = run_first_term_schedule(inputs, scenario)

        self.assertEqual(result.status, "constructive_feasible")
        self.assertEqual(result.staff_assignments[0]["start_minute"], 450)
        self.assertEqual(result.staff_assignments[0]["end_minute"], 630)

    def test_overlapping_passes_cannot_share_one_room_during_placement(self) -> None:
        scenario = IntegratedTermScenario(
            "overlap", "test", TermCalendar(
                date(2026, 1, 12), date(2026, 1, 12), (1,),
                (CalendarPass("am", "08:00", "12:00"), CalendarPass("mid", "09:00", "13:00")), 30,
            ),
            1, 1, 1, "test", "same_course_hard_constraint", "verified",
            StaffingPolicy((StaffingStep(20, 1),), (WorkShift("day", 7 * 60, 14 * 60),), 0, 0, 30, 300, 600, 660, 0), 0, (),
        )
        inputs = TermModelInputs(
            (IntegratedDemand("first", 10, 120, "Uppsala"), IntegratedDemand("second", 10, 120, "Uppsala")),
            (IntegratedRoom("room", 10, "Uppsala", 1),), (),
            {"included_source_activities": 2, "source_activities_total": 2, "unresolved_source_activities": 0},
        )

        result = run_first_term_schedule(inputs, scenario)

        self.assertEqual(result.status, "no_constructive_full_solution")


if __name__ == "__main__":
    unittest.main()
