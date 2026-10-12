"""Parallel day checks must change how fast the exact checks run, never what they decide.

- One thread and memory budget is shared: simultaneous checks x workers per check never exceeds it.
- The result of a batch is independent of which check finishes first.
- Parallel and sequential runs have the same cost function and the same optimum, and every result passes
  the independent validator.
- An interrupt or an exhausted time budget returns a complete verified solution or none, never a partial one,
  and never turns a missed check into a cut or a cached verdict.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import random
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from test_joint_strategy import _dense_case, _two_day_problem, _validate, _with  # noqa: E402
from test_joint_validation_differential import _random_case  # noqa: E402
from tentaoptimering.joint_contract import SolverSettings  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_strategy import verification  # noqa: E402
from tentaoptimering.joint_strategy.resources import (  # noqa: E402
    CancelToken, ExecutionBudget, plan_batch, run_ordered, solve_cancellable, task_memory_mb,
)
from tentaoptimering.joint_strategy.warm_start import StartReport  # noqa: E402


def _failing_rules(payload: dict) -> list[str]:
    return [item["rule_id"] for item in payload["rules"] if item["status"] == "fail"]


def _threads_back_to(count: int, seconds: float = 3.0) -> int:
    """Worker threads end a moment after a stop; wait for them instead of sampling once."""
    end = time.perf_counter() + seconds
    while threading.active_count() > count and time.perf_counter() < end:
        time.sleep(0.02)
    return threading.active_count()


def _signature(result) -> str:
    """Everything a run decides, in a stable text form."""
    return json.dumps({"s": result.schedule, "a": result.assignments, "r": result.room_sessions, "c": result.costs,
                       "p": result.staff_pool_size}, sort_keys=True, default=lambda value: value.__dict__)


class PlanTests(unittest.TestCase):
    def test_threads_are_shared_and_never_exceeded(self) -> None:
        for threads in (1, 2, 4, 8, 12):
            for tasks in (0, 1, 2, 3, 7, 8, 9, 73):
                with self.subTest(threads=threads, tasks=tasks):
                    parallel, workers = plan_batch(tasks, 40.0, ExecutionBudget(threads, 10**6))
                    self.assertGreaterEqual(parallel, 1)
                    self.assertGreaterEqual(workers, 1)
                    self.assertLessEqual(parallel * workers, threads)
                    self.assertLessEqual(parallel, max(1, tasks))

    def test_eight_checks_do_not_each_get_eight_threads(self) -> None:
        self.assertEqual(plan_batch(73, 40.0, ExecutionBudget(8, 10**6)), (8, 1))
        self.assertEqual(plan_batch(4, 40.0, ExecutionBudget(8, 10**6)), (4, 2))
        self.assertEqual(plan_batch(1, 40.0, ExecutionBudget(8, 10**6)), (1, 8))

    def test_memory_limits_how_many_checks_run_at_once(self) -> None:
        self.assertEqual(plan_batch(73, 100.0, ExecutionBudget(8, 350)), (3, 2))
        self.assertEqual(plan_batch(73, 100.0, ExecutionBudget(8, 50)), (1, 8))  # one check always fits: it runs alone
        self.assertLess(task_memory_mb(100), task_memory_mb(10000))

    def test_switching_parallel_checks_off_gives_the_old_sequential_plan(self) -> None:
        self.assertEqual(plan_batch(73, 40.0, ExecutionBudget(8, 10**6, parallel_day_checks=False)), (1, 8))

    def test_the_scenarios_worker_count_is_the_default_thread_budget(self) -> None:
        settings = SolverSettings(10, 1, 6)
        self.assertEqual(ExecutionBudget().resolve(settings).threads, 6)
        self.assertEqual(ExecutionBudget(3).resolve(settings).threads, 3)
        self.assertGreater(ExecutionBudget().resolve(settings).memory_mb, 0)


class OrderedRunTests(unittest.TestCase):
    def test_results_follow_call_order_whichever_call_finishes_first(self) -> None:
        delays = [0.15, 0.0, 0.1, 0.05, 0.2, 0.01]
        calls = [lambda index=index, delay=delay: (time.sleep(delay), index)[1] for index, delay in enumerate(delays)]
        self.assertEqual(run_ordered(calls, 4), list(range(len(delays))))

    def test_the_lowest_numbered_error_is_raised_and_the_others_are_stopped(self) -> None:
        token = CancelToken()

        def call(index: int):
            def run():
                time.sleep(0.2 if index == 1 else 0.0)
                if index in (1, 4):
                    raise RuntimeError(f"call {index}")
                return index
            return run

        before = threading.active_count()
        with self.assertRaisesRegex(RuntimeError, "call 1"):  # call 4 fails first in time
            run_ordered([call(index) for index in range(6)], 3, token)
        self.assertTrue(token.cancelled)
        self.assertEqual(_threads_back_to(before), before, "worker threads were left running")

    def test_cancelling_stops_a_running_cp_sat_solve_and_blocks_new_ones(self) -> None:
        rng = random.Random(1)
        model = cp_model.CpModel()
        variables = [model.NewBoolVar(f"x{index}") for index in range(60)]
        weights = [rng.randrange(10**14, 10**15) for _ in variables]
        model.Add(sum(weight * var for weight, var in zip(weights, variables)) == sum(weights) // 3 + 7)  # hard to settle
        token, solver = CancelToken(), cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30
        solver.parameters.num_search_workers = 2
        threading.Timer(0.4, token.cancel).start()
        started = time.perf_counter()
        status = solve_cancellable(solver, model, token)
        self.assertEqual(status, cp_model.UNKNOWN)
        self.assertLess(time.perf_counter() - started, 5.0)
        self.assertEqual(solve_cancellable(cp_model.CpSolver(), model, token), cp_model.UNKNOWN)  # already cancelled: not started


class CheckerTests(unittest.TestCase):
    def _batch(self, problem, budget):
        checker = verification.Checker(problem, time.perf_counter() + 60, budget)
        rooms = problem.rooms
        requests = [verification.Request("day", frozenset({slot.scheduled_date}), frozenset(
            item.exam_demand_id for item in problem.demands if slot.slot_id in item.candidate_slot_ids), None, rooms)
            for slot in problem.slots[::2]]
        return checker, requests

    def test_identical_requests_are_solved_once_and_cached(self) -> None:
        checker, requests = self._batch(_two_day_problem("decomposed"), ExecutionBudget(4, 10**6))
        first = checker.check_many(requests + requests)
        self.assertEqual(checker.calls["day"], len(requests))
        again = checker.check_many(requests)
        self.assertEqual(checker.calls["day"], len(requests))
        self.assertEqual([item[0] for item in again], [item[0] for item in first[:len(requests)]])

    def test_a_check_that_missed_the_deadline_is_neither_cached_nor_a_verdict(self) -> None:
        problem = _two_day_problem("decomposed")
        checker = verification.Checker(problem, time.perf_counter() - 1, ExecutionBudget(2, 10**6))
        _, requests = self._batch(problem, ExecutionBudget(2, 10**6))
        self.assertEqual({item[0] for item in checker.check_many(requests)}, {"unknown"})
        self.assertEqual(checker.cache, {})

    def test_a_cancelled_check_is_unknown_and_not_cached(self) -> None:
        problem = _two_day_problem("decomposed")
        token = CancelToken()
        token.cancel()
        checker = verification.Checker(problem, time.perf_counter() + 60, ExecutionBudget(2, 10**6), token)
        _, requests = self._batch(problem, ExecutionBudget(2, 10**6))
        self.assertEqual({item[0] for item in checker.check_many(requests)}, {"unknown"})
        self.assertEqual(checker.cache, {})


class EconomicEquivalenceTests(unittest.TestCase):
    """Parallel checks and sequential checks minimise the same function over the same placements."""

    def test_parallel_and_sequential_runs_reach_the_same_optimum_as_the_monolithic_model(self) -> None:
        compared = 0
        for seed in range(10):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as temp:
                events, rooms, overrides = _random_case(seed)
                problem, _ = fx._solve(Path(temp), events, rooms, {**overrides, "solver.time_limit_seconds": 1.0})
                rng = random.Random(seed)
                problem = replace(problem, rooms=tuple(
                    replace(room, external_session_cost_ore=rng.choice((0, 300, 2000)),
                            annual_fixed_cost_ore=rng.choice((0, room.annual_fixed_cost_ore))) for room in problem.rooms))
                exact = solve_joint_optimization(_with(problem, "monolithic"))
                if exact.solver.outcome != "optimal":
                    continue
                compared += 1
                runs = {}
                for label, budget in (("sequential", ExecutionBudget(4, None, False)), ("parallel", ExecutionBudget(4, None, True))):
                    runs[label] = solve_joint_optimization(_with(problem, "decomposed"), None, budget)
                    self.assertGreaterEqual(runs[label].solver.objective_value_ore, exact.solver.objective_value_ore)
                    if runs[label].solver.outcome == "optimal":
                        self.assertEqual(runs[label].solver.objective_value_ore, exact.solver.objective_value_ore)
                    self.assertEqual(_failing_rules(_validate(Path(temp), problem, runs[label])), [])
                if all(run.solver.outcome == "optimal" for run in runs.values()):
                    self.assertEqual(runs["sequential"].costs, runs["parallel"].costs)
        self.assertGreaterEqual(compared, 5)

    def test_the_cut_path_gives_the_same_optimum_in_parallel_and_sequentially(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _dense_case(12)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            exact = solve_joint_optimization(_with(problem, "monolithic", limit=60))
            self.assertEqual(exact.solver.outcome, "optimal")
            for parallel in (False, True):
                with self.subTest(parallel=parallel):
                    result = solve_joint_optimization(replace(problem, solver=SolverSettings(60, 5, 2, False, "decomposed", 0.0)),
                                                      None, ExecutionBudget(2, None, parallel))
                    self.assertEqual(result.solver.outcome, "optimal")
                    self.assertEqual(result.solver.objective_value_ore, exact.solver.objective_value_ore)
                    self.assertEqual(_failing_rules(_validate(Path(temp), problem, result)), [])

    def test_the_hand_calculated_optimum_holds_in_parallel(self) -> None:
        result = solve_joint_optimization(_two_day_problem("decomposed"), None, ExecutionBudget(4, None, True))
        self.assertEqual((result.solver.outcome, result.costs.comparable_total_cost_ore, result.staff_pool_size), ("optimal", 1300, 1))


class OrderIndependenceTests(unittest.TestCase):
    def test_the_result_does_not_depend_on_which_check_finishes_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _dense_case(12)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            problem = replace(problem, solver=SolverSettings(60, 5, 2, True, "decomposed", 0.0))  # deterministic CP-SAT
            original = verification.Checker._solve_one
            signatures = set()
            for trial in range(4):
                rng = random.Random(trial)

                def delayed(self, request, settings, rng=rng):
                    time.sleep(rng.random() * 0.05)  # shuffles the order in which the checks finish
                    return original(self, request, settings)

                with mock.patch.object(verification.Checker, "_solve_one", delayed):
                    result = solve_joint_optimization(problem, None, ExecutionBudget(2, None, True))
                self.assertEqual(result.solver.outcome, "optimal")
                signatures.add(_signature(result))
            self.assertEqual(len(signatures), 1, "the result changed with the completion order")


class BudgetTests(unittest.TestCase):
    def test_simultaneous_checks_times_workers_stay_within_the_thread_budget(self) -> None:
        lock, state = threading.Lock(), {"now": 0, "peak_threads": 0}
        original = verification.Checker._solve_one

        def watched(self, request, settings):
            with lock:
                state["now"] += settings.num_workers
                state["peak_threads"] = max(state["peak_threads"], state["now"])
            try:
                time.sleep(0.02)
                return original(self, request, settings)
            finally:
                with lock:
                    state["now"] -= settings.num_workers

        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _dense_case(12)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            with mock.patch.object(verification.Checker, "_solve_one", watched):
                solve_joint_optimization(replace(problem, solver=SolverSettings(30, 5, 4, False, "decomposed", 0.0)), None,
                                         ExecutionBudget(3, None, True))
        self.assertGreater(state["peak_threads"], 1, "no checks ran at the same time")
        self.assertLessEqual(state["peak_threads"], 3)

    def test_the_time_limit_holds_with_parallel_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _dense_case(12)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            for limit in (1.0, 3.0):
                with self.subTest(limit=limit):
                    started = time.perf_counter()
                    result = solve_joint_optimization(_with(problem, "decomposed", limit=limit), None, ExecutionBudget(4, None, True))
                    self.assertLess(time.perf_counter() - started, limit + 1.5)
                    self.assertEqual(result.coverage.technical_placement_complete, bool(result.schedule))
                    if result.schedule:
                        self.assertEqual(_failing_rules(_validate(Path(temp), problem, result)), [])


class InterruptTests(unittest.TestCase):
    def _problem(self, temp: str):
        events, rooms, overrides = _dense_case(12)
        problem, _ = fx._solve(Path(temp), events, rooms, overrides)
        return replace(problem, solver=SolverSettings(60, 5, 2, False, "decomposed", 0.0))

    def test_a_run_cancelled_before_it_starts_has_no_solution_and_no_partial_placement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            token = CancelToken()
            token.cancel()
            report = StartReport()
            result = solve_joint_optimization(self._problem(temp), None, ExecutionBudget(2), token, report)
            self.assertEqual(result.solver.outcome, "no_feasibility_conclusion")
            self.assertEqual((result.schedule, result.assignments, result.room_sessions, result.costs), ((), (), (), None))
            self.assertFalse(result.coverage.technical_placement_complete)
            self.assertTrue(report.interrupted)

    def test_a_run_cancelled_midway_returns_a_complete_verified_solution_or_none(self) -> None:
        for delay in (0.05, 0.3, 1.0):
            with self.subTest(delay=delay), tempfile.TemporaryDirectory() as temp:
                problem = self._problem(temp)
                token = CancelToken()
                timer = threading.Timer(delay, token.cancel)
                timer.start()
                self.addCleanup(timer.cancel)
                started = time.perf_counter()
                result = solve_joint_optimization(problem, None, ExecutionBudget(2), token)
                self.assertLess(time.perf_counter() - started, 10.0)
                if result.schedule:
                    self.assertTrue(result.coverage.technical_placement_complete)
                    self.assertNotEqual(result.solver.outcome, "infeasible")
                    self.assertEqual(_failing_rules(_validate(Path(temp), problem, result)), [])
                else:
                    self.assertIn(result.solver.outcome, {"no_feasibility_conclusion"})
                    self.assertFalse(result.coverage.technical_placement_complete)

    def test_an_interrupted_run_never_reports_a_proof_it_did_not_get(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            problem = _two_day_problem("decomposed")
            first = solve_joint_optimization(problem)
            saved = {"schedule": list(first.schedule), "room_sessions": list(first.room_sessions)}
            token = CancelToken()
            original = verification.Checker.check_many

            def cancel_after_the_warm_start(self, requests):
                outcome = original(self, requests)
                if any(request.kind == "warm-start" for request in requests):
                    token.cancel()  # the run is stopped right after its warm start was verified
                return outcome

            with mock.patch.object(verification.Checker, "check_many", cancel_after_the_warm_start):
                report = StartReport()
                result = solve_joint_optimization(problem, saved, ExecutionBudget(2), token, report)
            self.assertEqual(report.status, "accepted")
            self.assertEqual(result.solver.outcome, "feasible_not_proven")  # complete, verified, but not proven optimal
            self.assertTrue(result.solver.raw_status.endswith("_cancelled"))
            self.assertEqual(result.costs.comparable_total_cost_ore, first.costs.comparable_total_cost_ore)
            self.assertEqual(_failing_rules(_validate(Path(temp), problem, result)), [])

    def test_a_failing_check_stops_the_run_with_its_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            problem = self._problem(temp)
            calls = {"n": 0}
            original = verification.Checker._solve_one

            def failing(self, request, settings):
                calls["n"] += 1
                if calls["n"] == 3:
                    raise MemoryError("simulated")
                return original(self, request, settings)

            before = threading.active_count()
            with mock.patch.object(verification.Checker, "_solve_one", failing):
                with self.assertRaises(MemoryError):
                    solve_joint_optimization(problem, None, ExecutionBudget(2))
            self.assertEqual(_threads_back_to(before), before)


if __name__ == "__main__":
    unittest.main()
