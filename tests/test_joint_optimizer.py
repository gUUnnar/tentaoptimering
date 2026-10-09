from __future__ import annotations

from datetime import date
import tempfile
from pathlib import Path
import unittest

from tentaoptimering.joint_contract import (
    INPUT_SCHEMA_VERSION,
    CandidateSlot,
    ExamDemand,
    JointOptimizationInput,
    ParticipantGroup,
    Room,
    ScopeSummary,
    SolverSettings,
    StaffingCostPolicy,
    StaffingStep,
    read_problem,
    write_problem,
)
from tentaoptimering.joint_optimizer import solve_joint_optimization


def _group(group_id: str, count: int, *activities: str) -> ParticipantGroup:
    return ParticipantGroup(group_id, count, tuple(activities), "registered_count")


def _problem(
    demands: tuple[ExamDemand, ...],
    rooms: tuple[Room, ...],
    slots: tuple[CandidateSlot, ...],
    staff_cost: int = 1000,
    turnaround: int = 0,
) -> JointOptimizationInput:
    return JointOptimizationInput(
        INPUT_SCHEMA_VERSION,
        "hand-calculated",
        "dataset-hash",
        slots,
        demands,
        rooms,
        StaffingCostPolicy((StaffingStep(100, 1),), staff_cost),
        SolverSettings(5, 1, 1),
        (),
        ScopeSummary(2, 2, 0, 0, len(demands), sum(item.participant_count for item in demands)),
        turnaround,
    )


class JointOptimizerTests(unittest.TestCase):
    def test_joint_cost_chooses_dearer_large_room_when_it_saves_staff(self) -> None:
        slot = CandidateSlot("s", date(2026, 1, 12), "am", 480, 720)
        demands = (
            ExamDemand("e1", (_group("g1", 40, "a1"),), 120, "Uppsala", ("s",), "s"),
            ExamDemand("e2", (_group("g2", 40, "a2"),), 120, "Uppsala", ("s",), "s"),
        )
        rooms = (
            Room("large", "large-building", "Uppsala", 80, 600),
            Room("small-a", "small-building", "Uppsala", 40, 100),
            Room("small-b", "small-building", "Uppsala", 40, 100),
        )

        result = solve_joint_optimization(_problem(demands, rooms, (slot,)))

        self.assertEqual(result.solver.outcome, "optimal")
        self.assertTrue(result.coverage.technical_placement_complete)
        self.assertEqual(result.coverage.participants_assigned_to_rooms, 80)
        self.assertEqual({row["room_id"] for row in result.assignments}, {"large"})
        self.assertEqual(result.costs.annual_room_cost_ore, 600)
        self.assertEqual(result.costs.annual_staff_pool_cost_ore, 1000)
        self.assertEqual(result.costs.comparable_total_cost_ore, 1600)

    def test_subgroups_are_counted_once_and_sources_cannot_be_reused(self) -> None:
        slot = CandidateSlot("s", date(2026, 1, 12), "am", 480, 720)
        demand = ExamDemand(
            "co-exam",
            (_group("cohort-a", 10, "source-a", "source-b"), _group("cohort-b", 15, "source-c")),
            60,
            "Uppsala",
            ("s",),
            "s",
        )
        result = solve_joint_optimization(
            _problem((demand,), (Room("room", "building", "Uppsala", 25, 1),), (slot,), 1)
        )
        self.assertEqual(demand.participant_count, 25)
        self.assertEqual(result.coverage.participants_total, 25)
        self.assertEqual(sum(row["participants"] for row in result.assignments), 25)

    def test_equal_cost_solution_keeps_original_slot(self) -> None:
        slots = (
            CandidateSlot("original", date(2026, 1, 12), "am", 480, 720),
            CandidateSlot("alternative", date(2026, 1, 13), "am", 480, 720),
        )
        demand = ExamDemand(
            "e1", (_group("g1", 10, "a1"),), 60, "Uppsala",
            ("original", "alternative"), "original",
        )
        result = solve_joint_optimization(
            _problem((demand,), (Room("room", "building", "Uppsala", 10, 1),), slots, 1)
        )
        self.assertEqual(result.schedule[0]["slot_id"], "original")
        self.assertEqual(result.changed_exam_demands, 0)
        self.assertEqual(result.solver.change_preference_status, "optimal_at_economic_optimum")

    def test_external_room_session_cost_competes_with_fixed_room_cost(self) -> None:
        slot = CandidateSlot("s", date(2026, 1, 12), "am", 480, 720)
        demand = ExamDemand("e1", (_group("g1", 10, "a1"),), 60, "Uppsala", ("s",), "s")
        rooms = (
            Room("fixed", "fixed", "Uppsala", 10, 1000),
            Room("external", "external", "Uppsala", 10, 0, external_session_cost_ore=100),
        )
        result = solve_joint_optimization(_problem((demand,), rooms, (slot,), staff_cost=0))
        self.assertEqual({row["room_id"] for row in result.assignments}, {"external"})
        self.assertEqual(result.costs.annual_room_cost_ore, 0)
        self.assertEqual(result.costs.external_room_session_cost_ore, 100)
        self.assertEqual(result.costs.comparable_total_cost_ore, 100)

    def test_infeasible_demand_is_never_returned_as_partial_placement(self) -> None:
        slot = CandidateSlot("s", date(2026, 1, 12), "am", 480, 720)
        demand = ExamDemand(
            "e1", (_group("g1", 60, "a1"),), 60, "Uppsala", ("s",), "s", max_rooms=1
        )
        result = solve_joint_optimization(
            _problem((demand,), (Room("room", "building", "Uppsala", 50, 1),), (slot,))
        )
        self.assertEqual(result.solver.outcome, "infeasible")
        self.assertFalse(result.coverage.technical_placement_complete)
        self.assertEqual(result.assignments, ())

    def test_digital_compatibility_and_course_conflicts_are_hard(self) -> None:
        slots = (
            CandidateSlot("am", date(2026, 1, 12), "am", 480, 600),
            CandidateSlot("pm", date(2026, 1, 12), "pm", 600, 720),
        )
        demands = (
            ExamDemand(
                "e1", (_group("g1", 10, "a1"),), 120, "Uppsala", ("am", "pm"), "am",
                course_code="COURSE", digital_requirement="e_exam",
            ),
            ExamDemand(
                "e2", (_group("g2", 10, "a2"),), 120, "Uppsala", ("am", "pm"), "pm",
                course_code="COURSE", digital_requirement="e_exam",
            ),
        )
        rooms = (
            Room("paper", "building", "Uppsala", 20, 0, digital_capabilities=("paper",)),
            Room("digital", "building", "Uppsala", 20, 1, digital_capabilities=("paper", "e_exam")),
        )
        result = solve_joint_optimization(_problem(demands, rooms, slots, 0))
        self.assertEqual(result.solver.outcome, "optimal")
        self.assertEqual({row["room_id"] for row in result.assignments}, {"digital"})
        self.assertEqual({row["slot_id"] for row in result.schedule}, {"am", "pm"})

    def test_turnaround_boundary_is_enforced_per_actual_session_end(self) -> None:
        first = ExamDemand("e1", (_group("g1", 10, "a1"),), 60, "Uppsala", ("first",), "first")
        second = ExamDemand("e2", (_group("g2", 10, "a2"),), 60, "Uppsala", ("second",), "second")
        room = (Room("room", "building", "Uppsala", 20, 1),)
        for second_start, expected in ((570, "optimal"), (569, "infeasible")):
            with self.subTest(second_start=second_start):
                slots = (
                    CandidateSlot("first", date(2026, 1, 12), "first", 480, 600),
                    CandidateSlot("second", date(2026, 1, 12), "second", second_start, 720),
                )
                result = solve_joint_optimization(
                    _problem((first, second), room, slots, 0, turnaround=30)
                )
                self.assertEqual(result.solver.outcome, expected)

    def test_contract_round_trip_preserves_version_and_dates(self) -> None:
        slot = CandidateSlot("s", date(2026, 1, 12), "am", 480, 720)
        demand = ExamDemand("e1", (_group("g1", 10, "a1"),), 60, "Uppsala", ("s",), "s")
        problem = _problem((demand,), (Room("room", "building", "Uppsala", 10, 1),), (slot,))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "problem.json"
            write_problem(problem, path)
            loaded = read_problem(path)
        self.assertEqual(loaded, problem)


if __name__ == "__main__":
    unittest.main()
