from __future__ import annotations

import unittest

from tentaoptimering.synthetic_integrated import (
    SyntheticExamDemand,
    SyntheticPass,
    SyntheticRoom,
    solve_synthetic_integrated,
)


class SyntheticIntegratedTests(unittest.TestCase):
    def test_co_located_exams_form_one_room_session_with_latest_end(self) -> None:
        result = solve_synthetic_integrated(
            exams=(
                SyntheticExamDemand("exam-a", 15, 60, ("morning",)),
                SyntheticExamDemand("exam-b", 20, 120, ("morning",)),
            ),
            passes=(SyntheticPass("morning", 480, 120, 30),),
            rooms=(SyntheticRoom("large", 40, 100000, 10000),),
        )
        self.assertEqual(len(result.room_sessions), 1)
        session = result.room_sessions[0]
        self.assertEqual(set(session["exam_demand_ids"]), {"exam-a", "exam-b"})
        self.assertEqual(session["available_again_minute"], 630)

    def test_higher_staffing_cost_can_unlock_larger_room_saving(self) -> None:
        result = solve_synthetic_integrated(
            exams=(
                SyntheticExamDemand("exam-a", 20, 120, ("morning",)),
                SyntheticExamDemand("exam-b", 20, 90, ("morning",)),
            ),
            passes=(SyntheticPass("morning", 480, 180, 30),),
            rooms=(
                SyntheticRoom("large", 40, 350000, 10000),
                SyntheticRoom("small-1", 20, 40000, 120000),
                SyntheticRoom("small-2", 20, 40000, 120000),
            ),
        )
        self.assertEqual(result.annual_room_cost_ore, 80000)
        self.assertEqual(result.staffing_cost_ore, 240000)
        self.assertEqual(result.objective_ore, 320000)
        self.assertEqual(sum(item["participants"] for item in result.assignments), 40)
        self.assertEqual({item["room_id"] for item in result.room_sessions}, {"small-1", "small-2"})
        self.assertTrue(all(item["available_again_minute"] >= 600 for item in result.room_sessions))


if __name__ == "__main__":
    unittest.main()
