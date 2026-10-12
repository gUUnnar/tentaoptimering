"""Regression tests for two cancellation faults.

1. Reading `WallTime()` of a CP-SAT solver that was never started raised RuntimeError. A run cancelled
   between the loop check and the relaxation solve crashed instead of stopping.
2. The monolithic strategy ignored the cancel token in both of its solve phases.

A cancelled run keeps a complete verified solution it already has, and never accepts an incomplete one.
A cancelled check is "unknown": never infeasible, never a cut.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from test_joint_strategy import _dense_case, _two_day_problem, _validate  # noqa: E402
from tentaoptimering.joint_contract import SolverSettings  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_strategy import resources  # noqa: E402
from tentaoptimering.joint_strategy.aggregate import solve_master  # noqa: E402
from tentaoptimering.joint_strategy.resources import CancelToken  # noqa: E402
from tentaoptimering.joint_strategy.subproblems import is_infeasible, restrict, solve_part  # noqa: E402


def _failing(payload: dict) -> list[str]:
    return [item["rule_id"] for item in payload["rules"] if item["status"] == "fail"]


def _cancelled() -> CancelToken:
    token = CancelToken()
    token.cancel()
    return token


class UnstartedSolverTests(unittest.TestCase):
    """A solver that was never started must not be read, and must not count as a verdict."""

    def test_the_relaxation_stops_cleanly_when_cancelled_before_its_solve(self) -> None:
        master = solve_master(_two_day_problem("decomposed"), 10.0, SolverSettings(10, 1, 2), cancel=_cancelled())
        self.assertEqual((master.status, master.plans, master.objective, master.bound), ("unknown", (), None, None))

    def test_a_cancelled_day_check_is_unknown_not_infeasible(self) -> None:
        problem = _two_day_problem("decomposed")
        days = frozenset({problem.slots[0].scheduled_date})
        exams = {item.exam_demand_id for item in problem.demands if problem.slots[0].slot_id in item.candidate_slot_ids}
        sub = restrict(problem, days, exams, problem.rooms)
        self.assertEqual(solve_part(sub, days, None, frozenset(), 5.0, time.perf_counter() + 30, problem.solver, _cancelled()),
                         ("unknown", None, None))
        # Only a proof counts as infeasible: a cancelled check never produces the proof a cut would need.
        self.assertFalse(is_infeasible(problem, days, exams, problem.rooms, None, 5.0, time.perf_counter() + 30, problem.solver, _cancelled()))

    def test_the_wall_time_helper_survives_an_unstarted_solver(self) -> None:
        self.assertEqual(resources.wall_time(cp_model.CpSolver()), 0.0)


class MonolithicCancelTests(unittest.TestCase):
    def test_cancelled_before_the_first_phase_gives_no_solution_and_no_partial_placement(self) -> None:
        result = solve_joint_optimization(_two_day_problem("monolithic"), None, None, _cancelled())
        self.assertEqual(result.solver.outcome, "no_feasibility_conclusion")  # unknown, not "infeasible"
        self.assertEqual((result.schedule, result.assignments, result.room_sessions, result.costs), ((), (), (), None))
        self.assertFalse(result.coverage.technical_placement_complete)

    def test_cancelled_between_the_phases_keeps_the_verified_economic_optimum(self) -> None:
        problem = _two_day_problem("monolithic")
        token, calls, original = CancelToken(), [], resources.solve_cancellable

        def cancel_after_the_first_phase(solver, model, cancel):
            status = original(solver, model, cancel)
            calls.append(status)
            token.cancel()
            return status

        with mock.patch.object(resources, "solve_cancellable", cancel_after_the_first_phase):
            result = solve_joint_optimization(problem, None, None, token)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], cp_model.UNKNOWN, "the change-preference phase must not run after a cancel")
        self.assertEqual(result.solver.outcome, "optimal")  # the economic optimum was proven before the cancel
        self.assertEqual(result.costs.comparable_total_cost_ore, 1300)
        self.assertEqual(result.solver.change_preference_status, "not_run_time_limit_after_economic_optimum")
        self.assertTrue(result.coverage.technical_placement_complete)
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(_failing(_validate(Path(temp), problem, result)), [])

    def test_cancelled_during_the_second_phase_keeps_the_economic_solution(self) -> None:
        problem = _two_day_problem("monolithic")
        token, count, original = CancelToken(), [0], resources.solve_cancellable

        def cancel_in_the_second_phase(solver, model, cancel):
            count[0] += 1
            if count[0] == 2:
                token.cancel()  # the token is set as the second solve is about to start
            return original(solver, model, cancel)

        with mock.patch.object(resources, "solve_cancellable", cancel_in_the_second_phase):
            result = solve_joint_optimization(problem, None, None, token)
        self.assertEqual(count[0], 2)
        self.assertEqual((result.solver.outcome, result.costs.comparable_total_cost_ore), ("optimal", 1300))
        self.assertEqual(result.solver.change_preference_status, "not_run_time_limit_after_economic_optimum")
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(_failing(_validate(Path(temp), problem, result)), [])

    def test_cancelled_midway_returns_a_complete_verified_solution_or_none(self) -> None:
        for delay in (0.05, 0.4):
            with self.subTest(delay=delay), tempfile.TemporaryDirectory() as temp:
                events, rooms, overrides = _dense_case(12)
                problem, _ = fx._solve(Path(temp), events, rooms, overrides)
                problem = replace(problem, solver=SolverSettings(60, 5, 2, False, "monolithic", 0.0))
                token = CancelToken()
                timer = threading.Timer(delay, token.cancel)
                timer.start()
                self.addCleanup(timer.cancel)
                started = time.perf_counter()
                result = solve_joint_optimization(problem, None, None, token)
                self.assertLess(time.perf_counter() - started, 15.0)
                self.assertNotEqual(result.solver.outcome, "infeasible", "a cancel is not a proof of infeasibility")
                if result.schedule:
                    self.assertTrue(result.coverage.technical_placement_complete)
                    self.assertEqual(result.coverage.exam_demands_scheduled, result.coverage.exam_demands_total)
                    self.assertEqual(_failing(_validate(Path(temp), problem, result)), [])
                else:
                    self.assertEqual(result.solver.outcome, "no_feasibility_conclusion")
                    self.assertFalse(result.coverage.technical_placement_complete)

    def test_without_a_token_nothing_changes(self) -> None:
        result = solve_joint_optimization(_two_day_problem("monolithic"))
        self.assertEqual((result.solver.outcome, result.costs.comparable_total_cost_ore), ("optimal", 1300))
        self.assertEqual(result.solver.change_preference_status, "optimal_at_economic_optimum")


if __name__ == "__main__":
    unittest.main()
