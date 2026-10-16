"""Paid staff time and fixed bookings in the joint model, with hand-worked answers.

Paid time: every staff position of a room session is one paid pass, `max(worked, minimum) + travel` minutes, where `worked` is
preparation + longest exam + closing. Reservations: a fixed booking outside the optimised exams blocks its room for its
time (plus turnaround) and keeps the room in use. Both are checked against the monolithic model, the decomposed strategy
and the independent validator.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from joint_validation_cases import write_run  # noqa: E402
from tentaoptimering.joint_contract import (  # noqa: E402
    INPUT_SCHEMA_VERSION, CandidateSlot, ExamDemand, JointOptimizationInput, ParticipantGroup, Reservation, Room, ScopeSummary,
    SolverSettings, StaffingCostPolicy, StaffingStep, write_problem, write_result,
)
from tentaoptimering.joint_costing import cost_of_sessions, staffing_summary  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402

DAY = date(2026, 1, 12)


def _demand(demand_id: str, count: int, minutes: int, slots: tuple[str, ...], original: str | None = None, movable: bool = True) -> ExamDemand:
    return ExamDemand(demand_id, (ParticipantGroup(f"{demand_id}-g", count, (f"{demand_id}-a",), "registered_count"),), minutes, "Uppsala", slots,
                      original or slots[0], original_date=DAY, original_start_minute=480, movable=movable)


def _problem(demands, rooms, slots, rate: int = 10, minimum: int = 120, strategy: str = "monolithic", reservations=()) -> JointOptimizationInput:
    return JointOptimizationInput(
        INPUT_SCHEMA_VERSION, "paid-time", "hash", slots, demands, rooms,
        StaffingCostPolicy((StaffingStep(100, 1), StaffingStep(200, 2)), 0, 0, 30, 30, rate, minimum),
        SolverSettings(20, 1, 1, False, strategy), (),
        ScopeSummary(len(demands), len(demands), 0, 0, len(demands), sum(item.participant_count for item in demands)), 30,
        reservations=tuple(reservations),
    )


MORNING = CandidateSlot("am", DAY, "08:00", 480, 1200)
AFTERNOON = CandidateSlot("pm", DAY, "14:00", 840, 1200)


class PaidTimeTests(unittest.TestCase):
    def test_paid_minutes_are_prep_exam_closing_and_travel(self) -> None:
        # worked 30 + 120 + 30 = 180, travel 15: 195 paid minutes for the one staff position, at 10 öre each
        room = Room("r", "b", "Uppsala", 100, 1000, travel_paid_minutes=15)
        result = solve_joint_optimization(_problem((_demand("e", 40, 120, ("am",)),), (room,), (MORNING,)))
        self.assertEqual(result.solver.outcome, "optimal")
        self.assertEqual(result.costs.staff_paid_time_cost_ore, 1950)
        self.assertEqual(result.costs.comparable_total_cost_ore, 1000 + 1950)
        self.assertEqual((result.staffing_summary["passes"], result.staffing_summary["paid_minutes"]), (1, 195))

    def test_shortest_paid_pass_tops_up_a_short_session(self) -> None:
        # worked 30 + 30 + 30 = 90 < 120: paid 120 plus 15 travel
        room = Room("r", "b", "Uppsala", 100, 0, travel_paid_minutes=15)
        result = solve_joint_optimization(_problem((_demand("e", 40, 30, ("am",)),), (room,), (MORNING,)))
        self.assertEqual(result.staffing_summary["paid_minutes"], 135)
        self.assertEqual(result.staffing_summary["minimum_top_up_minutes"], 30)
        self.assertEqual(result.costs.staff_paid_time_cost_ore, 1350)

    def test_two_staff_positions_are_two_paid_passes(self) -> None:
        # 150 participants need 2 staff by the ladder: 2 x (180 + 0) = 360 paid minutes
        room = Room("r", "b", "Uppsala", 200, 0)
        result = solve_joint_optimization(_problem((_demand("e", 150, 120, ("am",)),), (room,), (MORNING,)))
        self.assertEqual(result.staffing_summary["passes"], 2)
        self.assertEqual(result.staffing_summary["paid_minutes"], 360)

    def test_more_paid_hours_when_the_room_saving_is_larger(self) -> None:
        near = Room("near", "b1", "Uppsala", 100, 5000)
        far = Room("far", "b2", "Uppsala", 100, 1000, travel_paid_minutes=120)
        demand = (_demand("e", 40, 120, ("am",)),)
        cheap_minutes = solve_joint_optimization(_problem(demand, (near, far), (MORNING,), rate=10))
        # far: rent 1 000 + 300 paid minutes x 10 = 4 000; near: rent 5 000 + 180 x 10 = 6 800
        self.assertEqual({row["room_id"] for row in cheap_minutes.assignments}, {"far"})
        self.assertEqual(cheap_minutes.staffing_summary["paid_minutes"], 300)
        self.assertEqual(cheap_minutes.costs.comparable_total_cost_ore, 4000)
        dear_minutes = solve_joint_optimization(_problem(demand, (near, far), (MORNING,), rate=100))
        # far: 1 000 + 30 000 = 31 000; near: 5 000 + 18 000 = 23 000: fewer paid hours now win
        self.assertEqual({row["room_id"] for row in dear_minutes.assignments}, {"near"})
        self.assertEqual(dear_minutes.staffing_summary["paid_minutes"], 180)
        self.assertEqual(dear_minutes.costs.comparable_total_cost_ore, 23000)

    def test_cost_of_a_given_plan_matches_the_solver(self) -> None:
        room = Room("r", "b", "Uppsala", 100, 1000, travel_paid_minutes=15)
        problem = _problem((_demand("e", 40, 120, ("am",)),), (room,), (MORNING,))
        result = solve_joint_optimization(problem)
        priced = cost_of_sessions(problem, result.room_sessions, result.staff_pool_size)
        self.assertEqual(priced["comparable_total_cost_ore"], result.costs.comparable_total_cost_ore)
        self.assertEqual(staffing_summary(problem, result.room_sessions)["paid_minutes"], 195)

    def test_decomposed_strategy_reaches_the_monolithic_optimum_with_paid_time(self) -> None:
        rooms = (Room("a", "b1", "Uppsala", 100, 3000, travel_paid_minutes=0), Room("b", "b2", "Uppsala", 100, 500, travel_paid_minutes=60))
        demands = (_demand("e1", 60, 180, ("am", "pm")), _demand("e2", 50, 120, ("am", "pm")), _demand("e3", 30, 60, ("am", "pm")))
        mono = solve_joint_optimization(_problem(demands, rooms, (MORNING, AFTERNOON), rate=15))
        deco = solve_joint_optimization(_problem(demands, rooms, (MORNING, AFTERNOON), rate=15, strategy="decomposed"))
        self.assertEqual(mono.solver.outcome, "optimal")
        self.assertEqual(deco.costs.comparable_total_cost_ore, mono.costs.comparable_total_cost_ore)
        self.assertEqual(deco.costs.staff_paid_time_cost_ore, deco.staffing_summary["paid_time_cost_ore"])
        self.assertLessEqual(deco.solver.best_objective_bound_ore, deco.costs.comparable_total_cost_ore)

    def test_independent_validator_recomputes_paid_time_and_catches_a_wrong_figure(self) -> None:
        room = Room("r", "b", "Uppsala", 100, 1000, travel_paid_minutes=15)
        problem = _problem((_demand("e", 40, 120, ("am",)),), (room,), (MORNING,))
        result = solve_joint_optimization(problem)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir()
            write_problem(problem, run / "joint_input.json")
            write_result(result, run / "joint_result.json")
            problem_json = json.loads((run / "joint_input.json").read_text(encoding="utf-8"))
            result_json = json.loads((run / "joint_result.json").read_text(encoding="utf-8"))
            write_run(run, problem_json, result_json)
            rules = {item["rule_id"]: item for item in validate_run(run)["rules"]}
            self.assertEqual(rules["paid_time_recomputed"]["status"], "pass")
            self.assertEqual(rules["costs_recomputed"]["status"], "pass")
            result_json["staffing_summary"]["paid_minutes"] += 60
            write_run(run, problem_json, result_json)
            rules = {item["rule_id"]: item for item in validate_run(run)["rules"]}
            self.assertEqual(rules["paid_time_recomputed"]["status"], "fail")


class ReservationTests(unittest.TestCase):
    def _two_room_problem(self, slots, reservations, strategy="monolithic") -> JointOptimizationInput:
        rooms = (Room("r1", "b1", "Uppsala", 100, 100), Room("r2", "b2", "Uppsala", 100, 200))
        return _problem((_demand("e", 40, 120, tuple(item.slot_id for item in slots)),), rooms, slots, rate=0, strategy=strategy, reservations=reservations)

    def test_a_booked_room_cannot_take_an_overlapping_session(self) -> None:
        booked = Reservation("b1", "r1", DAY, 480, 720)  # r1 is booked 08:00-12:00
        for strategy in ("monolithic", "decomposed"):
            with self.subTest(strategy):
                result = solve_joint_optimization(self._two_room_problem((MORNING,), (booked,), strategy))
                self.assertEqual({row["room_id"] for row in result.assignments}, {"r2"})
                # r1 is in use through its booking (100) and the exam sits in r2 (200)
                self.assertEqual(result.costs.annual_room_cost_ore, 300)

    def test_exam_moves_to_the_free_pass_in_the_booked_room(self) -> None:
        booked = Reservation("b1", "r1", DAY, 480, 720)
        for strategy in ("monolithic", "decomposed"):
            with self.subTest(strategy):
                result = solve_joint_optimization(self._two_room_problem((MORNING, AFTERNOON), (booked,), strategy))
                # 14:00 is after 12:00 + 30 minutes turnaround, so r1 can be shared at no extra rent
                self.assertEqual(result.schedule[0]["slot_id"], "pm")
                self.assertEqual({row["room_id"] for row in result.assignments}, {"r1"})
                self.assertEqual(result.costs.annual_room_cost_ore, 100)

    def test_turnaround_after_the_booking_is_kept(self) -> None:
        booked = Reservation("b1", "r1", DAY, 480, 780)  # until 13:00; the 14:00 pass would start 60 minutes later: allowed
        late = CandidateSlot("late", DAY, "13:15", 795, 1200)  # only 15 minutes after the booking ends: not allowed with 30 turnaround
        result = solve_joint_optimization(self._two_room_problem((late,), (booked,)))
        self.assertEqual({row["room_id"] for row in result.assignments}, {"r2"})

    def test_an_unused_reserved_room_still_costs(self) -> None:
        booked = Reservation("b1", "r1", DAY, 1000, 1100)  # booked in the evening, the exam sits in r2 in the morning
        result = solve_joint_optimization(self._two_room_problem((MORNING,), (booked,)))
        # the exam fits r1 in the morning (rent 100, already owned through the booking) and r2 would add 200
        self.assertEqual({row["room_id"] for row in result.assignments}, {"r1"})
        self.assertEqual(result.costs.annual_room_cost_ore, 100)

    def test_validator_flags_a_session_inside_a_booking(self) -> None:
        problem = self._two_room_problem((MORNING,), ())
        result = solve_joint_optimization(problem)
        self.assertEqual({row["room_id"] for row in result.assignments}, {"r1"})
        booked = replace(problem, reservations=(Reservation("b1", "r1", DAY, 600, 700),))  # added after the fact: the plan now violates it
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir()
            write_problem(booked, run / "joint_input.json")
            write_result(result, run / "joint_result.json")
            write_run(run, json.loads((run / "joint_input.json").read_text(encoding="utf-8")),
                      json.loads((run / "joint_result.json").read_text(encoding="utf-8")))
            rules = {item["rule_id"]: item for item in validate_run(run)["rules"]}
            self.assertEqual(rules["reservations_respected"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
