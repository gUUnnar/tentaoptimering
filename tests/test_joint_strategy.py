"""The aggregate-first strategy must never change what is allowed or what is optimal.

- The aggregate relaxation is a lower bound: its optimum never exceeds a proven joint optimum.
- An infeasible relaxation implies an infeasible joint model, never the other way round.
- Every decomposed result passes the independent validator, and a decomposed result that claims
  optimality has exactly the monolithic optimum.
- A result stopped by a gap limit is never reported as proven optimal.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import random
import re
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from test_joint_validation_differential import _random_case  # noqa: E402
from joint_validation_cases import write_run  # noqa: E402
from tentaoptimering.joint_contract import (  # noqa: E402
    INPUT_SCHEMA_VERSION, CandidateSlot, ExamDemand, JointOptimizationInput, ParticipantGroup, Room, ScopeSummary,
    SolverSettings, StaffingCostPolicy, StaffingStep, write_problem, write_result,
)
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_strategy.aggregate import solve_master  # noqa: E402
from tentaoptimering.joint_strategy.verification import peak_staff  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402


def _with(problem: JointOptimizationInput, strategy: str, gap: float = 0.0, limit: float = 20.0) -> JointOptimizationInput:
    return replace(problem, solver=SolverSettings(limit, 5, 4, False, strategy, gap))


def _validate(directory: Path, problem: JointOptimizationInput, result) -> dict:
    run = directory / "run"
    run.mkdir(parents=True, exist_ok=True)
    write_problem(problem, run / "joint_input.json")
    write_result(result, run / "joint_result.json")
    write_run(run, json.loads((run / "joint_input.json").read_text(encoding="utf-8")),
              json.loads((run / "joint_result.json").read_text(encoding="utf-8")))
    return validate_run(run)


class RelaxationAndDecompositionTests(unittest.TestCase):
    SEEDS = range(24)

    def test_relaxation_bounds_and_decomposition_agree_with_the_monolithic_optimum(self) -> None:
        compared = {"optimal": 0, "infeasible": 0}
        for seed in self.SEEDS:
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as temp:
                events, rooms, overrides = _random_case(seed)
                problem, _ = fx._solve(Path(temp), events, rooms, {**overrides, "solver.time_limit_seconds": 1.0})
                exact = solve_joint_optimization(_with(problem, "monolithic"))
                master = solve_master(problem, 20.0, SolverSettings(20, 5, 4))
                decomposed = solve_joint_optimization(_with(problem, "decomposed"))
                if exact.solver.outcome == "optimal":
                    compared["optimal"] += 1
                    self.assertNotEqual(master.status, "infeasible")
                    self.assertLessEqual(master.bound, exact.solver.objective_value_ore, "relaxation above the optimum")
                    self.assertIn(decomposed.solver.outcome, {"optimal", "feasible_not_proven"})
                    self.assertGreaterEqual(decomposed.solver.objective_value_ore, exact.solver.objective_value_ore)
                    self.assertLessEqual(decomposed.solver.best_objective_bound_ore, exact.solver.objective_value_ore)
                    if decomposed.solver.outcome == "optimal":
                        self.assertEqual(decomposed.solver.objective_value_ore, exact.solver.objective_value_ore)
                if master.status == "infeasible":
                    self.assertEqual(exact.solver.outcome, "infeasible", "relaxation infeasible but joint model feasible")
                if exact.solver.outcome == "infeasible":
                    compared["infeasible"] += 1
                    self.assertNotIn(decomposed.solver.outcome, {"optimal", "feasible_not_proven"})
                if decomposed.schedule:
                    payload = _validate(Path(temp), problem, decomposed)
                    failing = [item["rule_id"] for item in payload["rules"] if item["status"] == "fail"]
                    self.assertEqual(failing, [], f"seed {seed}")
        self.assertGreaterEqual(compared["optimal"], 10, compared)
        self.assertGreaterEqual(compared["infeasible"], 1, compared)


def _group(group_id: str, count: int) -> ParticipantGroup:
    return ParticipantGroup(group_id, count, (f"src-{group_id}",), "registered_count")


def _two_day_problem(strategy: str) -> JointOptimizationInput:
    """Hand case: one 80-seat room (800 öre) or two 40-seat rooms (2 x 300 öre); staff 1 000 öre each.

    Day 1 has two 40-person exams at 08:00 that may move to day 2. Day 2 has one 40-person exam.
    Optimum: the 80-seat room is not needed. Move one day-1 exam to day 2 at 14:00 so every slot has
    one exam: one 40-seat room, pool 1 -> 300 + 1 000 = 1 300 öre.
    """
    slots = (
        CandidateSlot("d1-am", date(2026, 1, 12), "08:00", 480, 1200),
        CandidateSlot("d1-pm", date(2026, 1, 12), "14:00", 840, 1200),
        CandidateSlot("d2-am", date(2026, 1, 13), "08:00", 480, 1200),
        CandidateSlot("d2-pm", date(2026, 1, 13), "14:00", 840, 1200),
    )
    all_slots = tuple(slot.slot_id for slot in slots)
    demands = (
        ExamDemand("a", (_group("a", 40),), 240, "Uppsala", all_slots, "d1-am", original_date=date(2026, 1, 12), original_start_minute=480),
        ExamDemand("b", (_group("b", 40),), 240, "Uppsala", all_slots, "d1-am", original_date=date(2026, 1, 12), original_start_minute=480),
        ExamDemand("c", (_group("c", 40),), 240, "Uppsala", ("d2-am", "d2-pm"), "d2-am", original_date=date(2026, 1, 13), original_start_minute=480),
    )
    rooms = (
        Room("big", "b1", "Uppsala", 80, 800),
        Room("small-1", "b2", "Uppsala", 40, 300),
        Room("small-2", "b2", "Uppsala", 40, 300),
    )
    return JointOptimizationInput(
        INPUT_SCHEMA_VERSION, "two-day", "hash", slots, demands, rooms,
        StaffingCostPolicy((StaffingStep(100, 1),), 1000), SolverSettings(20, 1, 4, False, strategy, 0.0), (),
        ScopeSummary(3, 3, 0, 0, 3, 120), 30,
    )


class HandCalculatedStrategyTests(unittest.TestCase):
    def test_both_strategies_find_the_hand_calculated_optimum(self) -> None:
        for strategy in ("monolithic", "decomposed"):
            with self.subTest(strategy=strategy):
                result = solve_joint_optimization(_two_day_problem(strategy))
                self.assertEqual(result.solver.outcome, "optimal")
                self.assertEqual(result.costs.comparable_total_cost_ore, 1300)
                self.assertEqual(result.staff_pool_size, 1)
                self.assertEqual(result.solver.strategy, strategy)
                self.assertEqual(len({row["room_id"] for row in result.room_sessions}), 1)

    def test_aggregate_bound_on_the_hand_case_is_exact(self) -> None:
        master = solve_master(_two_day_problem("decomposed"), 10.0, SolverSettings(10, 1, 4))
        self.assertEqual((master.status, master.bound, master.plans[0].pool), ("optimal", 1300, 1))

    def test_peak_staff_counts_preparation_and_closing_like_the_model(self) -> None:
        problem = replace(_two_day_problem("decomposed"), staffing=StaffingCostPolicy((StaffingStep(100, 1),), 1000, 0, 30, 30))
        sessions = [
            {"room_id": "small-1", "slot_id": "d1-am", "required_staff": 1, "available_again_minute": 480 + 360 + 30},
            {"room_id": "small-2", "slot_id": "d1-pm", "required_staff": 1, "available_again_minute": 840 + 240 + 30},
        ]
        # 08:00-14:00 closes at 14:30; the 14:00 exam is prepared from 13:30, so both are staffed then.
        self.assertEqual(peak_staff(problem, sessions), 2)
        sessions[0]["available_again_minute"] = 480 + 300 + 30  # ends 13:00, closed at 13:30 exactly
        self.assertEqual(peak_staff(problem, sessions), 1)


def _dense_case(seed: int):
    """Many exams in few, tight rooms over a few days, so a day check can fail and a cut is needed."""
    rng = random.Random(seed)
    events = []
    for index in range(rng.randint(16, 24)):
        start, end = rng.choice((("08:00", "13:00"), ("08:00", "14:00"), ("14:00", "18:00"), ("08:00", "11:00")))
        events.append(fx._event(
            f"E{index}", day=f"2026-01-{rng.choice((12, 13, 14)):02d}", start=start, end=end, kind="Ordinarie tenta",
            digital=rng.choice(("Nej", "Nej", "Ja")), count=rng.choice((15, 25, 40, 55, 70, 110, 150)),
        ))
    rooms = [(f"uu-r{i}", f"Adress {rng.randint(1, 2)}", rng.choice((60, 90, 120, 150, 200)),
              rng.choice(("all_places_support_e_exam", "not_stated"))) for i in range(rng.randint(3, 4))]
    overrides = {
        "window.earlier_days": 1, "window.later_days": 1, "calendar.weekdays": [1, 2, 3, 4],
        "calendar.start_times": ["08:00", "14:00"], "staffing.preparation_minutes": 30, "staffing.closing_minutes": 30,
        "staffing.ladder": [{"max_participants": 50, "required_staff": 1}, {"max_participants": 150, "required_staff": 2},
                            {"max_participants": 300, "required_staff": 3}],
        "cost.room_annual_per_seat_ore": 100, "cost.staff_annual_ore": rng.choice((1000, 5000)), "cost.staff_session_ore": 0,
        "solver.time_limit_seconds": 1.0, "rooms.allow_split_across_buildings": rng.random() < 0.5,
    }
    return events, rooms, overrides


class CutPathTests(unittest.TestCase):
    def test_cuts_from_failed_days_keep_the_bound_valid_and_reach_the_optimum(self) -> None:
        """Seed 12: the first relaxed plan fails the exact day check; cuts lead to the proven optimum."""
        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _dense_case(12)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            exact = solve_joint_optimization(_with(problem, "monolithic", limit=60))
            single = replace(problem, solver=SolverSettings(60, 5, 1, False, "decomposed", 0.0))  # one worker: reproducible
            decomposed = solve_joint_optimization(single)
            self.assertEqual(exact.solver.outcome, "optimal")
            self.assertGreater(int(re.search(r"cuts_(\d+)", decomposed.solver.raw_status).group(1)), 0, "the cut path was not used")
            self.assertEqual(decomposed.solver.outcome, "optimal")
            self.assertEqual(decomposed.solver.objective_value_ore, exact.solver.objective_value_ore)
            payload = _validate(Path(temp), problem, decomposed)
            self.assertEqual([item["rule_id"] for item in payload["rules"] if item["status"] == "fail"], [])


def _external_hire_problem(strategy: str, days: int) -> JointOptimizationInput:
    """Hand case: one 50-person exam per day, fixed to its day.

    An owned room costs 1 000 öre per year; an external room costs nothing per year but 400 öre per
    session. Staff 100 öre per pool resource (pool 1 either way). Over two days hire is cheaper
    (2 x 400 = 800 < 1 000); over three days the owned room is (1 200 > 1 000).
    """
    slots = tuple(CandidateSlot(f"d{day}", date(2026, 1, 12 + day), "08:00", 480, 1200) for day in range(days))
    demands = tuple(
        ExamDemand(f"e{day}", (_group(f"e{day}", 50),), 240, "Uppsala", (f"d{day}",), f"d{day}",
                   original_date=date(2026, 1, 12 + day), original_start_minute=480)
        for day in range(days)
    )
    rooms = (Room("owned", "b1", "Uppsala", 60, 1000), Room("hired", "b2", "Uppsala", 60, 0, 400))
    return JointOptimizationInput(
        INPUT_SCHEMA_VERSION, "external", "hash", slots, demands, rooms,
        StaffingCostPolicy((StaffingStep(100, 1),), 100), SolverSettings(20, 1, 4, False, strategy, 0.0), (),
        ScopeSummary(days, days, 0, 0, days, 50 * days), 30,
    )


class ExternalHireTests(unittest.TestCase):
    def test_both_strategies_minimise_the_same_cost_with_external_hire(self) -> None:
        expected = {2: ("hired", 0, 800, 900), 3: ("owned", 1000, 0, 1100)}
        for days, (room, fixed, external, total) in expected.items():
            for strategy in ("monolithic", "decomposed"):
                with self.subTest(days=days, strategy=strategy):
                    result = solve_joint_optimization(_external_hire_problem(strategy, days))
                    self.assertEqual(result.solver.outcome, "optimal")
                    self.assertEqual({row["room_id"] for row in result.room_sessions}, {room})
                    self.assertEqual((result.costs.annual_room_cost_ore, result.costs.external_room_session_cost_ore,
                                      result.costs.comparable_total_cost_ore), (fixed, external, total))

    def test_bound_and_optimum_agree_on_random_cases_with_external_hire(self) -> None:
        checked = 0
        for seed in range(12):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as temp:
                events, rooms, overrides = _random_case(seed)
                problem, _ = fx._solve(Path(temp), events, rooms, {**overrides, "solver.time_limit_seconds": 1.0})
                rng = random.Random(seed)
                problem = replace(problem, rooms=tuple(
                    replace(room, external_session_cost_ore=rng.choice((0, 300, 2000)),
                            annual_fixed_cost_ore=rng.choice((0, room.annual_fixed_cost_ore)))
                    for room in problem.rooms))
                exact = solve_joint_optimization(_with(problem, "monolithic"))
                if exact.solver.outcome != "optimal":
                    continue
                checked += 1
                master = solve_master(problem, 20.0, SolverSettings(20, 5, 4))
                decomposed = solve_joint_optimization(_with(problem, "decomposed"))
                self.assertLessEqual(master.bound, exact.solver.objective_value_ore, "relaxation above the optimum")
                self.assertLessEqual(decomposed.solver.best_objective_bound_ore, exact.solver.objective_value_ore)
                self.assertGreaterEqual(decomposed.solver.objective_value_ore, exact.solver.objective_value_ore)
                if decomposed.solver.outcome == "optimal":
                    self.assertEqual(decomposed.solver.objective_value_ore, exact.solver.objective_value_ore)
        self.assertGreaterEqual(checked, 5)

    def test_relaxation_bound_with_external_hire_is_valid_and_exact_here(self) -> None:
        for days, total in ((2, 900), (3, 1100)):
            with self.subTest(days=days):
                master = solve_master(_external_hire_problem("decomposed", days), 10.0, SolverSettings(10, 1, 4))
                self.assertEqual((master.status, master.bound), ("optimal", total))


class WarmStartAndTimeTests(unittest.TestCase):
    def _saved(self, result) -> dict:
        return json.loads(json.dumps({"schedule": list(result.schedule), "room_sessions": list(result.room_sessions)}))

    def test_an_earlier_verified_placement_seeds_a_more_flexible_instance(self) -> None:
        narrow = _two_day_problem("decomposed")
        narrow = replace(narrow, demands=tuple(replace(item, candidate_slot_ids=(item.original_slot_id,)) for item in narrow.demands))
        earlier = solve_joint_optimization(narrow)
        self.assertEqual(earlier.solver.outcome, "optimal")  # all fixed: two exams share d1-am
        wide = _two_day_problem("decomposed")
        result = solve_joint_optimization(wide, self._saved(earlier))
        self.assertLessEqual(result.costs.comparable_total_cost_ore, earlier.costs.comparable_total_cost_ore)
        self.assertEqual(result.costs.comparable_total_cost_ore, 1300)
        with tempfile.TemporaryDirectory() as temp:
            payload = _validate(Path(temp), wide, result)
            self.assertEqual([item["rule_id"] for item in payload["rules"] if item["status"] == "fail"], [])

    def test_a_placement_the_instance_no_longer_allows_is_ignored_not_trusted(self) -> None:
        from tentaoptimering.joint_strategy.verification import Checker
        from tentaoptimering.joint_strategy.warm_start import warm_start
        problem = _two_day_problem("decomposed")
        checker = Checker(problem, time.perf_counter() + 20)
        allowed = {"a": "d1-am", "b": "d1-pm", "c": "d2-am"}
        usable = lambda schedule, rooms: warm_start(checker, schedule, rooms)[0]  # noqa: E731
        self.assertIsNotNone(usable(allowed, {"small-1"}))
        self.assertIsNone(usable({**allowed, "c": "d1-am"}, {"small-1"}))  # c may not be on day 1
        self.assertIsNone(usable({"a": "d1-am", "b": "d1-pm"}, {"small-1"}))  # c missing
        self.assertIsNone(usable(allowed, {"gone"}))  # room no longer exists

    def test_the_time_limit_covers_builds_and_repairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _dense_case(12)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            for limit in (1.0, 3.0):
                with self.subTest(limit=limit):
                    started = time.perf_counter()
                    solve_joint_optimization(_with(problem, "decomposed", limit=limit))
                    self.assertLess(time.perf_counter() - started, limit + 1.5)


class GapLimitTests(unittest.TestCase):
    def test_a_gap_limited_result_is_never_reported_as_proven(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            events, rooms, overrides = _random_case(3)
            problem, _ = fx._solve(Path(temp), events, rooms, overrides)
            for strategy in ("monolithic", "decomposed"):
                with self.subTest(strategy=strategy):
                    result = solve_joint_optimization(_with(problem, strategy, gap=0.5))
                    if result.solver.outcome == "optimal":
                        self.assertEqual(result.solver.best_objective_bound_ore, result.solver.objective_value_ore)
                        self.assertEqual(result.solver.relative_gap, 0.0)
                    elif result.solver.outcome == "feasible_not_proven":
                        self.assertLessEqual(result.solver.best_objective_bound_ore, result.solver.objective_value_ore)

    def test_unknown_strategy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            solve_joint_optimization(_two_day_problem("guess"))


if __name__ == "__main__":
    unittest.main()
