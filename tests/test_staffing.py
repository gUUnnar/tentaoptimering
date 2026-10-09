from __future__ import annotations

from datetime import date
import unittest

from tentaoptimering.staffing import StaffingPolicy, StaffingStep, StaffingTask, WorkShift, plan_staffing, required_staff


class StaffingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = StaffingPolicy(
            (StaffingStep(50, 1), StaffingStep(200, 2)),
            (WorkShift("day", 7 * 60, 19 * 60),),
            preparation_minutes=0, closing_minutes=0, minimum_break_minutes=30,
            maximum_continuous_minutes=300, maximum_daily_minutes=600,
            minimum_daily_rest_minutes=1200, travel_minutes_between_buildings=30,
        )

    def test_ladder_and_building_travel_change_required_pool(self) -> None:
        tasks = (
            StaffingTask("first", date(2026, 1, 12), 8 * 60, 9 * 60, "a", 40, required_staff(40, self.policy)),
            StaffingTask("second", date(2026, 1, 12), 9 * 60 + 15, 10 * 60 + 15, "b", 40, required_staff(40, self.policy)),
        )
        plan = plan_staffing(tasks, self.policy)

        self.assertTrue(plan.feasible)
        self.assertEqual(plan.worker_count, 2)
        self.assertEqual(required_staff(51, self.policy), 2)

    def test_break_and_rest_rules_block_reuse_of_one_worker(self) -> None:
        tasks = (
            StaffingTask("first", date(2026, 1, 12), 8 * 60, 10 * 60, "a", 20, 1),
            StaffingTask("second", date(2026, 1, 12), 10 * 60, 13 * 60 + 1, "a", 20, 1),
            StaffingTask("late", date(2026, 1, 12), 16 * 60, 18 * 60, "a", 20, 1),
            StaffingTask("third", date(2026, 1, 13), 7 * 60, 8 * 60, "a", 20, 1),
        )
        plan = plan_staffing(tasks, self.policy)

        self.assertTrue(plan.feasible)
        self.assertEqual(plan.worker_count, 3)

    def test_task_outside_configured_shift_is_infeasible(self) -> None:
        plan = plan_staffing((
            StaffingTask("late", date(2026, 1, 12), 18 * 60, 20 * 60, "a", 20, 1),
        ), self.policy)

        self.assertFalse(plan.feasible)
        self.assertEqual(plan.reason, "task_outside_shift:late")

    def test_long_supervision_uses_recorded_relief_segments(self) -> None:
        plan = plan_staffing((
            StaffingTask("long", date(2026, 1, 12), 8 * 60, 18 * 60, "a", 20, 1),
        ), self.policy)

        self.assertTrue(plan.feasible)
        self.assertEqual(plan.worker_count, 2)
        self.assertEqual([row["task_id"] for row in plan.assignments], ["long#1", "long#2"])
        self.assertTrue(all(row["end_minute"] - row["start_minute"] <= 300 for row in plan.assignments))


if __name__ == "__main__":
    unittest.main()
