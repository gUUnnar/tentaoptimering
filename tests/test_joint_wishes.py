"""The business's wishes steer the calendar and the tie-break, and the independent validation agrees.

Hand-made cases: one exam of 50 people, booked on 12 January, whose business wished 13 January first and 12 January as reserve 1.
The room costs the same on any day, so the choice between the days is only the tie-break.

* `window` (the original behaviour) never looks at the wishes;
* `wishes` allows only the wished dates; the booked date is allowed only when it is also a wish;
* `wishes_and_window` allows both;
* the cost comes first: the tie-break (`fewest_changes` or `wish_priority`) never makes a plan more expensive;
* a policy that needs the wishes refuses to run when the underlay has none, instead of running without them.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wish_cases import wish_row, write_wishes  # noqa: E402
from tentaoptimering.joint_inputs import build_real_subset_problem, run_real_subset  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_preference import penalty_weights, slot_penalty  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402
from test_joint_validation_run import CATALOG, _write_pair_dataset  # noqa: E402

SCENARIO = """schema_version = "joint-real-subset-v1"
[scenario]
id = "wishcase"
description = "d"
[subset]
plan_area = "Uppsala"
exam_event_ids = ["X"]
[parameters]
"calendar.start_times" = ["08:00"]
"calendar.weekdays" = [1, 2, 3, 4, 5]
"staffing.ladder" = [{max_participants = 60, required_staff = 1}]
"cost.room_annual_per_seat_ore" = 100
"cost.staff_annual_ore" = 1000
"solver.time_limit_seconds" = 10.0
"solver.workers" = 1
"solver.strategy" = "monolithic"
"""


class WishPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)
        _write_pair_dataset(self.dir)  # X and Y, both booked 2026-01-12 08:00-12:00 with 50 people
        write_wishes(self.dir, [wish_row("X", "2026-01-13", "2026-01-12", None, booked="2026-01-12"), wish_row("Y", "2026-01-12", booked="2026-01-12")])

    def _problem(self, extra: str = "", starts: str = '["08:00"]'):
        path = self.dir / "wish.toml"
        path.write_text(SCENARIO.replace('["08:00"]', starts) + extra, encoding="utf-8")
        return build_real_subset_problem(path, self.dir, CATALOG)

    def _days(self, problem) -> list[date]:
        slots = {slot.slot_id: slot for slot in problem.slots}
        return sorted({slots[slot_id].scheduled_date for slot_id in problem.demands[0].candidate_slot_ids})

    def test_the_wishes_are_carried_into_the_input_as_written(self) -> None:
        demand = self._problem().demands[0]
        self.assertEqual((demand.wish_dates, demand.wish_status), (("2026-01-13", "2026-01-12", None), "reserves_given"))

    def test_window_policy_ignores_the_wishes_exactly_as_before(self) -> None:
        self.assertEqual(self._days(self._problem()), [date(2026, 1, 12)])  # a window of zero days: only the booked date

    def test_wishes_policy_allows_only_the_wished_dates(self) -> None:
        self.assertEqual(self._days(self._problem('"wish.candidate_policy" = "wishes"\n')), [date(2026, 1, 12), date(2026, 1, 13)])

    def test_the_booked_date_is_not_a_candidate_when_it_is_not_a_wish(self) -> None:
        write_wishes(self.dir, [wish_row("X", "2026-01-13", None, None, "ingen annan dag", booked="2026-01-12"), wish_row("Y", "2026-01-12")])
        self.assertEqual(self._days(self._problem('"wish.candidate_policy" = "wishes"\n')), [date(2026, 1, 13)])

    def test_wishes_and_window_allows_both(self) -> None:
        problem = self._problem('"wish.candidate_policy" = "wishes_and_window"\n"window.later_days" = 2\n')
        self.assertEqual(self._days(problem), [date(2026, 1, 12), date(2026, 1, 13), date(2026, 1, 14)])

    def test_a_wished_date_the_calendar_does_not_allow_is_dropped_not_forced(self) -> None:
        write_wishes(self.dir, [wish_row("X", "2026-01-17", "2026-01-13", booked="2026-01-12"), wish_row("Y", "2026-01-12")])  # 17 January is a Saturday
        self.assertEqual(self._days(self._problem('"wish.candidate_policy" = "wishes"\n')), [date(2026, 1, 13)])

    def test_booked_start_time_keeps_the_booked_start_on_a_wished_date(self) -> None:
        extra = '"wish.candidate_policy" = "wishes"\n'
        problem = self._problem(extra, '["08:00", "14:00"]')
        slots = {slot.slot_id: slot for slot in problem.slots}
        starts = {slots[slot_id].start_minute for slot_id in problem.demands[0].candidate_slot_ids}
        self.assertEqual(starts, {8 * 60, 14 * 60})  # any allowed pass by default
        problem = self._problem(extra + '"wish.time_policy" = "booked_start"\n', '["08:00", "14:00"]')
        slots = {slot.slot_id: slot for slot in problem.slots}
        self.assertEqual({slots[slot_id].start_minute for slot_id in problem.demands[0].candidate_slot_ids}, {8 * 60})

    def test_a_policy_that_needs_the_wishes_refuses_to_run_without_them(self) -> None:
        (self.dir / "exam_wishes.csv").unlink()
        with self.assertRaisesRegex(ValueError, "önskemål"):
            self._problem('"wish.candidate_policy" = "wishes"\n')
        with self.assertRaisesRegex(ValueError, "önskemål"):
            self._problem('"wish.tiebreak" = "wish_priority"\n')
        self.assertEqual(self._problem().demands[0].wish_status, "not_loaded")  # the original behaviour needs no wishes


class TieBreakTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)
        _write_pair_dataset(self.dir)
        write_wishes(self.dir, [wish_row("X", "2026-01-13", "2026-01-12", None, booked="2026-01-12"), wish_row("Y", "2026-01-12", booked="2026-01-12")])

    def _solve(self, extra: str):
        path = self.dir / "wish.toml"
        path.write_text(SCENARIO + '"wish.candidate_policy" = "wishes"\n' + extra, encoding="utf-8")
        problem = build_real_subset_problem(path, self.dir, CATALOG)
        result = solve_joint_optimization(problem)
        slots = {slot.slot_id: slot for slot in problem.slots}
        return problem, result, slots[result.schedule[0]["slot_id"]].scheduled_date

    def test_fewest_changes_stays_on_the_booked_date_when_the_cost_is_the_same(self) -> None:
        _, result, day = self._solve('"wish.tiebreak" = "fewest_changes"\n')
        self.assertEqual((day, result.changed_exam_demands), (date(2026, 1, 12), 0))

    def test_wish_priority_takes_the_requested_date_at_the_same_cost(self) -> None:
        keep, kept, _ = self._solve('"wish.tiebreak" = "fewest_changes"\n')
        problem, moved, day = self._solve('"wish.tiebreak" = "wish_priority"\n')
        self.assertEqual((day, moved.changed_exam_demands), (date(2026, 1, 13), 1))
        self.assertEqual(moved.solver.objective_value_ore, kept.solver.objective_value_ore)  # the tie-break never changes the cost
        self.assertEqual(problem.preference, "wish_priority")

    def test_penalties_put_the_wish_order_before_the_booked_occasion(self) -> None:
        problem, _, _ = self._solve('"wish.tiebreak" = "wish_priority"\n')
        demand = problem.demands[0]
        slots = {slot.slot_id: slot for slot in problem.slots}
        by_day = {slots[slot_id].scheduled_date: slot_penalty(problem, demand, slot_id, slots[slot_id].scheduled_date.isoformat()) for slot_id in demand.candidate_slot_ids}
        self.assertEqual(by_day, {date(2026, 1, 13): 1, date(2026, 1, 12): 2})  # requested (rank 0, moved: 1) before reserve 1 (rank 1, booked: 2)
        self.assertEqual(sorted(penalty_weights(problem).values()), [1, 2])

    def test_without_wishes_the_original_tiebreak_is_unchanged(self) -> None:
        path = self.dir / "plain.toml"
        path.write_text(SCENARIO + '"window.later_days" = 1\n"wish.tiebreak" = "wish_priority"\n', encoding="utf-8")
        write_wishes(self.dir, [wish_row("X", None, booked="2026-01-12"), wish_row("Y", None)])  # no requested date: nothing to prefer
        problem = build_real_subset_problem(path, self.dir, CATALOG)
        result = solve_joint_optimization(problem)
        self.assertEqual(result.changed_exam_demands, 0)

    def test_the_independent_validation_accepts_a_run_made_from_the_wishes(self) -> None:
        path = self.dir / "run.toml"
        path.write_text(SCENARIO + '"wish.candidate_policy" = "wishes"\n"wish.tiebreak" = "wish_priority"\n', encoding="utf-8")
        runs = self.dir / "runs"
        saved = run_real_subset(path, self.dir, CATALOG, runs, warm_start="none")
        summary = validate_run(runs / saved["run_id"], processed_dir=self.dir, config_path=runs / saved["run_id"] / "joint_scenario.toml", catalog_path=CATALOG)["summary"]
        self.assertEqual(summary["technical_validation"], "pass")

    def test_the_validation_rejects_a_placement_on_a_date_nobody_wished(self) -> None:
        path = self.dir / "run.toml"
        path.write_text(SCENARIO + '"wish.candidate_policy" = "wishes"\n', encoding="utf-8")
        runs = self.dir / "runs"
        saved = run_real_subset(path, self.dir, CATALOG, runs, warm_start="none")
        directory = runs / saved["run_id"]
        import json
        problem = json.loads((directory / "joint_input.json").read_text(encoding="utf-8"))
        problem["parameters"] = [{**item, "value": "window"} if item["parameter_id"] == "wish.candidate_policy" else item for item in problem["parameters"]]
        problem["demands"][0]["wish_dates"] = ["2026-01-20", None, None]  # the exam was placed on 12 or 13 January, neither is wished any more
        (directory / "joint_input.json").write_text(json.dumps(problem), encoding="utf-8")
        summary = validate_run(directory)["summary"]
        self.assertNotEqual(summary["provenance"], "pass")  # the changed input no longer matches its manifest
        problem["parameters"] = [{**item, "value": "wishes"} if item["parameter_id"] == "wish.candidate_policy" else item for item in problem["parameters"]]
        (directory / "joint_input.json").write_text(json.dumps(problem), encoding="utf-8")
        report = validate_run(directory)
        failed = {item["rule_id"] for item in report["rules"] if item["status"] == "fail"}
        self.assertIn("movable_exams_follow_calendar", failed)


if __name__ == "__main__":
    unittest.main()
