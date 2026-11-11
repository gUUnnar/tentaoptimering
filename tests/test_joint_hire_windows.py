"""Whole-facility hire (Fyrishov): one cost per hire window, however many halls and sessions are used in it.

Hand-worked answers: the window cost is paid once if any of its rooms is used in the window, never per room, and is avoided
when the exams fit elsewhere. The cost is booked with the external hire cost and the independent validator recomputes it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from joint_validation_cases import write_run  # noqa: E402
from tentaoptimering.joint_contract import (  # noqa: E402
    INPUT_SCHEMA_VERSION, CandidateSlot, ExamDemand, HireWindow, JointOptimizationInput, ParticipantGroup, Room, ScopeSummary,
    SolverSettings, StaffingCostPolicy, StaffingStep, read_problem, write_problem, write_result,
)
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402

DAY1, DAY2 = date(2026, 6, 1), date(2026, 6, 2)
SLOTS = (CandidateSlot("d1", DAY1, "08:00", 480, 1200), CandidateSlot("d2", DAY2, "08:00", 480, 1200))
WINDOW_COST = 10_000


def _demand(demand_id: str, count: int, slot: str = "d1") -> ExamDemand:
    return ExamDemand(demand_id, (ParticipantGroup(f"{demand_id}-g", count, (f"{demand_id}-a",), "registered_count"),), 120, "Uppsala",
                      (slot,), slot, original_date=DAY1, original_start_minute=480, movable=False)


def _problem(demands, rooms, windows) -> JointOptimizationInput:
    return JointOptimizationInput(
        INPUT_SCHEMA_VERSION, "hire", "hash", SLOTS, tuple(demands), tuple(rooms),
        StaffingCostPolicy((StaffingStep(100, 1),), 0, 0, 30, 30, 0, 0), SolverSettings(20, 1, 1, False, "monolithic"), (),
        ScopeSummary(len(demands), len(demands), 0, 0, len(demands), sum(item.participant_count for item in demands)), 30,
        hire_windows=tuple(windows),
    )


def _halls() -> tuple[Room, Room]:
    return (Room("hall-a", "fy", "Uppsala", 100, 0, kind="external"), Room("hall-b", "fy", "Uppsala", 100, 0, kind="external"))


def _window(room_ids=("hall-a", "hall-b"), start=DAY1, end=DAY2) -> HireWindow:
    return HireWindow("fy-1", "Fyrishov vecka", tuple(room_ids), start, end, WINDOW_COST, "simulated")


class HireWindowCostTests(unittest.TestCase):
    def test_the_window_is_paid_once_however_many_halls_are_used(self) -> None:
        demands = (_demand("e1", 80), _demand("e2", 80))  # same slot, both halls are needed
        result = solve_joint_optimization(_problem(demands, _halls(), (_window(),)))
        self.assertEqual(result.solver.outcome, "optimal")
        self.assertEqual({row["room_id"] for row in result.room_sessions}, {"hall-a", "hall-b"})
        self.assertEqual(result.costs.external_room_session_cost_kr, WINDOW_COST)
        self.assertEqual(result.costs.comparable_total_cost_kr, WINDOW_COST)

    def test_the_window_is_paid_once_for_sessions_on_several_days(self) -> None:
        demands = (_demand("e1", 80, "d1"), _demand("e2", 80, "d2"))
        result = solve_joint_optimization(_problem(demands, _halls(), (_window(),)))
        self.assertEqual(result.costs.external_room_session_cost_kr, WINDOW_COST)

    def test_a_cheaper_own_room_avoids_the_hire(self) -> None:
        own = Room("own", "main", "Uppsala", 100, 50)
        result = solve_joint_optimization(_problem((_demand("e1", 80),), (own, *_halls()), (_window(),)))
        self.assertEqual({row["room_id"] for row in result.room_sessions}, {"own"})
        self.assertEqual(result.costs.external_room_session_cost_kr, 0)
        self.assertEqual(result.costs.comparable_total_cost_kr, 50)

    def test_a_hire_is_used_when_it_is_cheaper_than_owning_more_rooms(self) -> None:
        own = Room("own", "main", "Uppsala", 100, 50000)
        result = solve_joint_optimization(_problem((_demand("e1", 80),), (own, *_halls()), (_window(),)))
        self.assertEqual(result.costs.external_room_session_cost_kr, WINDOW_COST)
        self.assertEqual(result.costs.annual_room_cost_kr, 0)

    def test_a_window_outside_the_exam_days_costs_nothing(self) -> None:
        later = _window(start=DAY2 + timedelta(days=30), end=DAY2 + timedelta(days=34))
        own = Room("own", "main", "Uppsala", 100, 50)
        result = solve_joint_optimization(_problem((_demand("e1", 80),), (own, *_halls()), (later,)))
        self.assertEqual(result.costs.external_room_session_cost_kr, 0)

    def test_the_decomposed_strategy_falls_back_to_one_model(self) -> None:
        problem = replace(_problem((_demand("e1", 80),), _halls(), (_window(),)), solver=SolverSettings(20, 1, 1, False, "decomposed"))
        result = solve_joint_optimization(problem)
        self.assertEqual(result.solver.outcome, "optimal")
        self.assertEqual(result.solver.strategy, "monolithic")
        self.assertEqual(result.costs.external_room_session_cost_kr, WINDOW_COST)


class HireWindowValidationTests(unittest.TestCase):
    def test_the_validator_recomputes_the_window_cost_and_rejects_a_missing_one(self) -> None:
        problem = _problem((_demand("e1", 80), _demand("e2", 80)), _halls(), (_window(),))
        result = solve_joint_optimization(problem)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir()
            write_problem(problem, run / "joint_input.json")
            write_result(result, run / "joint_result.json")
            self.assertEqual(read_problem(run / "joint_input.json").hire_windows, problem.hire_windows)  # the window survives the file
            problem_json = json.loads((run / "joint_input.json").read_text(encoding="utf-8"))
            result_json = json.loads((run / "joint_result.json").read_text(encoding="utf-8"))
            write_run(run, problem_json, result_json)
            rules = {item["rule_id"]: item for item in validate_run(run)["rules"]}
            self.assertEqual(rules["costs_recomputed"]["status"], "pass")
            result_json["costs"]["external_room_session_cost_kr"] -= WINDOW_COST  # a plan that forgets the hire is not accepted
            result_json["costs"]["comparable_total_cost_kr"] -= WINDOW_COST
            write_run(run, problem_json, result_json)
            rules = {item["rule_id"]: item for item in validate_run(run)["rules"]}
            self.assertEqual(rules["costs_recomputed"]["status"], "fail")


class HirePackTests(unittest.TestCase):
    def test_the_simulated_pack_hires_fyrishov_in_two_weeks_and_removes_the_per_session_charge(self) -> None:
        from tentaoptimering.joint_resources import apply_hire_windows
        from tentaoptimering.resource_data import load_pack

        pack = load_pack(Path(__file__).resolve().parents[1] / "config" / "resource_data" / "simulated_dev_2026.toml")
        self.assertEqual([item.window_id for item in pack.hire_windows], ["hw-fyrishov-2026-01", "hw-fyrishov-2026-06"])
        slots = tuple(CandidateSlot(f"s{index}", day, "08:00", 480, 1200) for index, day in enumerate(
            (date(2026, 1, 13), date(2026, 3, 10), date(2026, 6, 2))))
        halls = tuple(Room(f"uu-fyrishov-hall-{letter}", "fyrishov", "Uppsala", 300, 0, external_session_cost_kr=9, kind="external")
                      for letter in "def")
        rooms, windows = apply_hire_windows(pack, halls, slots)
        self.assertEqual([w.window_id for w in windows], ["hw-fyrishov-2026-01", "hw-fyrishov-2026-06"])
        for room in rooms:
            self.assertEqual(room.external_session_cost_kr, 0)
            self.assertEqual(room.available_slot_ids, ("s0", "s2"))  # usable only inside the hire weeks, not on 10 March
        only_june = tuple(slot for slot in slots if slot.scheduled_date >= date(2026, 6, 1))
        _, june = apply_hire_windows(pack, halls, only_june)
        self.assertEqual([w.window_id for w in june], ["hw-fyrishov-2026-06"])  # a period without the January week does not pay for it

    def test_a_malformed_window_is_refused(self) -> None:
        from tentaoptimering.resource_data import ResourceDataError, _hire_window

        with self.assertRaises(ResourceDataError):
            _hire_window({"id": "x", "name": "x", "room_ids": [], "start": "2026-01-12", "end": "2026-01-16", "cost_kr": 0.01}, "simulated")
        with self.assertRaises(ResourceDataError):
            _hire_window({"id": "x", "name": "x", "room_ids": ["a"], "start": "2026-01-16", "end": "2026-01-12", "cost_kr": 0.01}, "simulated")

    def test_a_window_cost_is_split_into_an_observed_rent_and_a_derived_rest_that_sum_to_the_whole(self) -> None:
        from tentaoptimering.joint_resources import apply_hire_windows
        from tentaoptimering.resource_data import load_pack

        pack = load_pack(Path(__file__).resolve().parents[1] / "config" / "resource_data" / "simulated_dev_2026.toml")
        window = pack.hire_windows[0]
        self.assertEqual([(part["cost_kr"], part["origin"]) for part in window.parts], [(303026, "observed"), (296974, "model_calculated")])
        self.assertEqual(sum(part["cost_kr"] for part in window.parts), window.cost_kr)  # 2.4 Mkr - 1.2 Mkr - 2 x 303 026 = 593 948, half each
        self.assertEqual(window.provenance.origin, "model_calculated")  # a sum with a derived part is not observed
        halls = tuple(Room(f"uu-fyrishov-hall-{letter}", "fyrishov", "Uppsala", 300, 0, kind="external") for letter in "def")
        slots = (CandidateSlot("s0", date(2026, 1, 13), "08:00", 480, 1200),)
        _, windows = apply_hire_windows(pack, halls, slots)
        self.assertEqual(windows[0].parts, window.parts)  # the split follows the window into the problem
        # 300 seats per hall is Fyrishov's figure; the record stays "simulated" because its per-session charge is invented
        self.assertEqual({room.room_id: (room.capacity, room.provenance.origin) for room in pack.rooms if "fyrishov" in room.room_id},
                         {f"uu-fyrishov-hall-{letter}": (300, "simulated") for letter in "def"})

    def test_parts_that_do_not_add_up_to_the_cost_are_refused(self) -> None:
        from tentaoptimering.resource_data import ResourceDataError, _hire_window

        item = {"id": "x", "name": "x", "room_ids": ["a"], "start": "2026-01-12", "end": "2026-01-16", "cost_kr": 600000,
                "part": [{"label": "Hyra", "cost_kr": 303026, "origin": "observed"}, {"label": "Rest", "cost_kr": 1, "origin": "model_calculated"}]}
        with self.assertRaisesRegex(ResourceDataError, "delposterna summerar"):
            _hire_window(item, "simulated")


if __name__ == "__main__":
    unittest.main()
