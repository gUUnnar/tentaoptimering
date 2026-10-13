"""The staffing ladder of the business material (two guards at least) against the model, worked out by hand.

The ladder 1-65: 2, 66-135: 3, 136-220: 4, 221-250: 5, 251-300: 6 comes from a presentation and is NOT a verified rule. This
test only shows what the model does with such a ladder, so that the difference to the earlier 1/2/3 ladder is known:

- the guards of a room session follow the number of participants in that room (the first step whose limit is not
  exceeded), so 250 participants get the step "up to 250" and 251 get the next;
- a first step of two guards means every room session has at least two;
- a room never holds more participants than the highest limit of the ladder (a modelling assumption, not a rule);
- the cost, the placement and the independent post-validation use the same ladder (the validator reads it from the saved input).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_strategy import _group, _validate  # noqa: E402
from tentaoptimering.joint_contract import (  # noqa: E402
    INPUT_SCHEMA_VERSION, CandidateSlot, ExamDemand, JointOptimizationInput, Room, ScopeSummary, SolverSettings,
    StaffingCostPolicy, StaffingStep,
)
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402

BUSINESS = (StaffingStep(65, 2), StaffingStep(135, 3), StaffingStep(220, 4), StaffingStep(250, 5), StaffingStep(300, 6))
EARLIER = (StaffingStep(50, 1), StaffingStep(150, 2), StaffingStep(300, 3))


def _case(participants: int, rooms: tuple[int, ...], ladder: tuple[StaffingStep, ...], strategy: str) -> JointOptimizationInput:
    """One exam on one day; every guard costs 1 000 öre per year in the pool, rooms and sessions are free."""
    slots = (CandidateSlot("s1", date(2026, 1, 12), "08:00", 480, 1200),)
    demands = (ExamDemand("e", (_group("e", participants),), 240, "Uppsala", ("s1",), "s1", original_date=date(2026, 1, 12),
                          original_start_minute=480),)
    rooms_ = tuple(Room(f"r{index}", "b1", "Uppsala", seats, 0) for index, seats in enumerate(rooms, start=1))
    return JointOptimizationInput(
        INPUT_SCHEMA_VERSION, "ladder", "hash", slots, demands, rooms_, StaffingCostPolicy(ladder, 1000),
        SolverSettings(20, 1, 1, False, strategy, 0.0), (), ScopeSummary(1, 1, 0, 0, 1, participants), 30,
    )


class LadderTests(unittest.TestCase):
    def _solve(self, problem):
        result = solve_joint_optimization(problem)
        with tempfile.TemporaryDirectory() as temp:
            failing = [item["rule_id"] for item in _validate(Path(temp), problem, result)["rules"] if item["status"] == "fail"] if result.schedule else []
        return result, failing

    def test_the_guards_follow_the_step_of_the_room_for_both_strategies(self) -> None:
        # (participants, expected guards): the business ladder, the limit itself belongs to its own step
        for strategy in ("monolithic", "decomposed"):
            for participants, guards in ((1, 2), (40, 2), (65, 2), (66, 3), (135, 3), (136, 4), (220, 4), (221, 5), (250, 5)):
                with self.subTest(strategy=strategy, participants=participants):
                    result, failing = self._solve(_case(participants, (260,), BUSINESS, strategy))
                    self.assertEqual(result.solver.outcome, "optimal")
                    self.assertEqual((result.staff_pool_size, result.costs.comparable_total_cost_ore), (guards, 1000 * guards))
                    self.assertEqual(failing, [])

    def test_the_same_exam_needs_fewer_guards_with_the_earlier_ladder_so_costs_are_not_comparable(self) -> None:
        for participants, business, earlier in ((40, 2, 1), (100, 3, 2), (200, 4, 3)):
            with self.subTest(participants=participants):
                self.assertEqual(self._solve(_case(participants, (260,), BUSINESS, "decomposed"))[0].staff_pool_size, business)
                self.assertEqual(self._solve(_case(participants, (260,), EARLIER, "decomposed"))[0].staff_pool_size, earlier)

    def test_a_split_exam_is_staffed_per_room(self) -> None:
        """260 participants do not fit one 150-seat room. Any split with both parts up to 135 gives 3 + 3 guards (per room)."""
        result, failing = self._solve(_case(260, (150, 150), BUSINESS, "decomposed"))
        self.assertEqual((result.solver.outcome, result.staff_pool_size), ("optimal", 6))
        parts = sorted(row["participants"] for row in result.assignments)
        self.assertEqual((sum(parts), len(parts), max(parts) <= 135), (260, 2, True))
        self.assertEqual(failing, [])

    def test_a_room_never_holds_more_than_the_highest_limit_of_the_ladder(self) -> None:
        """The material does not say what happens above 300. The model caps a room at the top limit of the ladder: an
        exam of 320 does not go into one 400-seat room, it has to be split. That is a modelling assumption, not a rule."""
        result, failing = self._solve(_case(320, (400,), BUSINESS, "decomposed"))
        self.assertEqual(result.solver.outcome, "infeasible")  # one room only: capped at 300 by the ladder
        self.assertEqual(failing, [])
        split, failing = self._solve(_case(320, (400, 400), BUSINESS, "decomposed"))
        self.assertEqual((split.solver.outcome, split.staff_pool_size), ("optimal", 7))  # 135 + 185: 3 + 4 guards
        self.assertEqual(failing, [])

    def test_a_ladder_with_the_limit_in_both_steps_is_rejected_or_read_in_the_stated_order(self) -> None:
        """The material gives 221-250 and 250-300, so 250 is in both. The model reads the first step that holds the number."""
        problem = _case(250, (260,), BUSINESS, "decomposed")
        result, _ = self._solve(problem)
        self.assertEqual(result.staff_pool_size, 5)  # 250 -> "up to 250": 5 guards, not 6
        higher = self._solve(_case(251, (260,), BUSINESS, "decomposed"))[0]
        self.assertEqual(higher.staff_pool_size, 6)


if __name__ == "__main__":
    unittest.main()
