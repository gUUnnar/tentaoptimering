"""A warm start is a starting point, never an answer.

- An earlier placement is reused only where the current instance still allows it, and every day is
  checked exactly against the current rules; cost, pool and rooms are recomputed under the current prices.
- Reasons for accepting and rejecting are reported. Rejecting costs no correctness: the run is the same
  optimization as without a start.
- Earlier runs are found through their saved artifacts and run ids. A candidate must be intact and pass the
  independent validation now; its stored verdict is not evidence.
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_strategy import _group, _two_day_problem, _validate  # noqa: E402
from test_joint_validation_run import CATALOG, PAIR_SCENARIO, _write_pair_dataset  # noqa: E402
from tentaoptimering.cli import main  # noqa: E402
from tentaoptimering.joint_contract import ScopeSummary  # noqa: E402
from tentaoptimering.joint_inputs import run_real_subset  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_strategy.resources import ExecutionBudget  # noqa: E402
from tentaoptimering.joint_strategy.warm_start import StartReport  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402
from tentaoptimering.joint_warm_start import (  # noqa: E402
    WARM_START_FILE, find_start, inspect_run,
)
from tentaoptimering.provenance import sha256_file  # noqa: E402


def _failing(payload: dict) -> list[str]:
    return [item["rule_id"] for item in payload["rules"] if item["status"] == "fail"]


def _saved(result) -> dict:
    return json.loads(json.dumps({"schedule": list(result.schedule), "room_sessions": list(result.room_sessions)}))


def _solve(problem, saved=None):
    report = StartReport()
    return solve_joint_optimization(problem, saved, ExecutionBudget(2), None, report), report


class SolverWarmStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.problem = _two_day_problem("decomposed")
        self.earlier = solve_joint_optimization(self.problem)
        self.assertEqual(self.earlier.costs.comparable_total_cost_ore, 1300)
        self.saved = _saved(self.earlier)

    def _same_as_cold(self, problem, result) -> None:
        cold = solve_joint_optimization(problem)
        self.assertEqual(result.solver.outcome, "optimal")
        self.assertEqual(result.costs, cold.costs, "a warm start changed the optimum")

    def test_a_compatible_placement_is_rechecked_and_becomes_the_first_verified_solution(self) -> None:
        result, report = _solve(self.problem, self.saved)
        self.assertEqual(report.status, "accepted")
        self.assertEqual((report.first_solution_source, report.verified_cost_ore), ("warm start", 1300))
        self.assertEqual((report.exams_reused, report.exams_without_start, report.exams_not_allowed), (3, 0, 0))
        self.assertEqual(report.days_checked, 2)
        self._same_as_cold(self.problem, result)
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(_failing(_validate(Path(temp), self.problem, result)), [])

    def test_the_old_placement_is_costed_with_the_new_prices(self) -> None:
        """Small rooms become dear: the old placement costs 900 + 1 000, the big room 800 + 1 000 is better."""
        dearer = replace(self.problem, rooms=tuple(replace(room, annual_fixed_cost_ore=900) if room.room_id.startswith("small") else room
                                                   for room in self.problem.rooms))
        result, report = _solve(dearer, self.saved)
        self.assertEqual((report.status, report.verified_cost_ore), ("accepted", 1900))
        self.assertEqual(result.costs.comparable_total_cost_ore, 1800)
        self.assertNotEqual(report.final_source, "warm start")
        self._same_as_cold(dearer, result)

    def test_an_earlier_slot_the_instance_no_longer_allows_is_rejected_and_used_as_a_hint(self) -> None:
        narrowed = replace(self.problem, demands=tuple(
            replace(item, candidate_slot_ids=("d2-pm",)) if item.exam_demand_id == "c" else item for item in self.problem.demands))
        result, report = _solve(narrowed, self.saved)
        self.assertEqual(report.status, "rejected")
        self.assertIn("tillåts inte", " ".join(report.reasons))
        self.assertEqual((report.exams_not_allowed, report.hint_exams), (1, 2))
        self._same_as_cold(narrowed, result)

    def test_an_exam_without_an_earlier_placement_makes_the_start_incomplete(self) -> None:
        partial = {**self.saved, "schedule": [row for row in self.saved["schedule"] if row["exam_demand_id"] != "b"]}
        result, report = _solve(self.problem, partial)
        self.assertEqual((report.status, report.exams_without_start), ("rejected", 1))
        self.assertIn("saknar tidigare placering", " ".join(report.reasons))
        self._same_as_cold(self.problem, result)

    def test_exams_that_left_the_instance_do_not_block_the_start(self) -> None:
        smaller = replace(self.problem, demands=tuple(item for item in self.problem.demands if item.exam_demand_id != "c"),
                          scope=ScopeSummary(3, 3, 0, 0, 2, 80))
        result, report = _solve(smaller, self.saved)
        self.assertEqual((report.status, report.exams_outside_instance), ("accepted", 1))
        self.assertEqual(result.solver.outcome, "optimal")

    def test_a_day_that_no_longer_fits_under_the_new_rules_is_rejected_by_the_exact_check(self) -> None:
        """The old placement used only a 40-seat room. With 60 participants per exam it cannot work any more."""
        bigger = replace(self.problem, demands=tuple(replace(item, participant_groups=(_group(item.exam_demand_id, 60),))
                                                     for item in self.problem.demands), scope=ScopeSummary(3, 3, 0, 0, 3, 180))
        result, report = _solve(bigger, self.saved)
        self.assertEqual(report.status, "rejected")
        self.assertGreater(report.days_failed, 0)
        self.assertIn("ryms inte", " ".join(report.reasons))
        self.assertNotEqual(report.first_solution_source, "warm start")
        self._same_as_cold(bigger, result)
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(_failing(_validate(Path(temp), bigger, result)), [])

    def test_a_placement_that_was_never_valid_is_not_accepted(self) -> None:
        bogus = {"schedule": [{"exam_demand_id": name, "slot_id": "d1-am"} for name in ("a", "b", "c")], "room_sessions": [{"room_id": "small-1"}]}
        result, report = _solve(self.problem, bogus)
        self.assertEqual(report.status, "rejected")  # c may not sit on day 1, and two 40-seat exams do not share one room
        self._same_as_cold(self.problem, result)

    def test_a_removed_room_is_noted_and_the_check_uses_the_rooms_that_remain(self) -> None:
        two_rooms = {**self.saved, "room_sessions": [{"room_id": "small-1"}, {"room_id": "gone"}]}
        result, report = _solve(self.problem, two_rooms)
        self.assertEqual((report.status, report.rooms_missing), ("accepted", ["gone"]))
        self.assertTrue(any("gone" in note for note in report.notes))
        gone = {**self.saved, "room_sessions": [{"room_id": "gone"}]}
        _, report = _solve(self.problem, gone)
        self.assertEqual(report.status, "rejected")
        self.assertIn("Ingen av de tidigare använda salarna", " ".join(report.reasons))

    def test_no_start_leaves_the_report_empty_and_the_result_unchanged(self) -> None:
        result, report = _solve(self.problem, None)
        self.assertEqual((report.status, report.hint_exams), ("not_provided", 0))
        self.assertEqual(result.costs, self.earlier.costs)

    def test_the_monolithic_strategy_only_takes_the_placement_as_a_hint(self) -> None:
        problem = _two_day_problem("monolithic")
        result, report = _solve(problem, self.saved)
        self.assertEqual(report.status, "hint_only")
        self.assertEqual(result.costs.comparable_total_cost_ore, 1300)


class RunLevelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.scenario = _write_pair_dataset(self.dir)
        self.runs = self.dir / "runs"

    def _run(self, warm_start="auto", scenario=None) -> dict:
        time.sleep(1.05)  # run ids carry the time in seconds
        return run_real_subset(scenario or self.scenario, self.dir, CATALOG, self.runs, warm_start=warm_start)

    def _problem(self):
        from tentaoptimering.joint_inputs import build_real_subset_problem
        return build_real_subset_problem(self.scenario, self.dir, CATALOG)

    def test_the_second_run_starts_from_the_first_and_says_so_everywhere(self) -> None:
        first = self._run()
        self.assertEqual(first["warm_start"]["decision"], "not_used")
        second = self._run()
        decision = second["warm_start"]
        self.assertEqual((decision["decision"], decision["source"]["run_id"]), ("accepted", first["run_id"]))
        self.assertEqual(second["result"]["costs"], first["result"]["costs"])
        self.assertEqual(second["validation"]["technical_validation"], "pass")
        directory = self.runs / second["run_id"]
        sidecar = json.loads((directory / WARM_START_FILE).read_text(encoding="utf-8"))
        self.assertEqual(sidecar["source"]["result_sha256"], sha256_file(self.runs / first["run_id"] / "joint_result.json"))
        manifest = json.loads((directory / "joint_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["warm_start_source_run_id"], first["run_id"])
        report = (directory / "joint_report.md").read_text(encoding="utf-8")
        self.assertIn("Varmstart och beräkningsresurser", report)
        self.assertIn("kontrolleras alltid mot de nya reglerna", report)

    def test_a_changed_parameter_is_listed_and_the_optimum_is_the_same_as_without_a_start(self) -> None:
        first = self._run()
        changed = self.dir / "scenario_changed.toml"
        changed.write_text(PAIR_SCENARIO.replace('"cost.staff_annual_ore" = 1000', '"cost.staff_annual_ore" = 3000'), encoding="utf-8")
        warm = self._run(scenario=changed)
        cold = self._run("none", scenario=changed)
        self.assertEqual(warm["warm_start"]["decision"], "accepted")
        self.assertIn("cost.staff_annual_ore", warm["warm_start"]["changed_parameters"])
        self.assertEqual(cold["warm_start"]["decision"], "not_used")
        self.assertEqual(warm["result"]["costs"], cold["result"]["costs"])
        self.assertNotEqual(warm["result"]["costs"], first["result"]["costs"])
        self.assertEqual(warm["validation"]["technical_validation"], "pass")

    def test_none_disables_and_a_named_run_is_used_even_if_it_is_not_the_newest(self) -> None:
        first = self._run()
        self._run()
        self.assertEqual(self._run("none")["warm_start"]["decision"], "not_used")
        named = self._run(first["run_id"])
        self.assertEqual(named["warm_start"]["source"]["run_id"], first["run_id"])

    def test_unknown_or_unsafe_run_ids_fall_back_to_normal_optimization(self) -> None:
        self._run()
        for name in ("no-such-run", "..", "../x", "a\\b", ""):
            with self.subTest(name=name):
                run = self._run(name) if name else self._run("")
                self.assertEqual(run["warm_start"]["decision"], "not_used")
                self.assertEqual(run["validation"]["technical_validation"], "pass")
                self.assertEqual(run["result"]["solver"]["outcome"], "optimal")
        explanation = self._run("no-such-run")["warm_start"]["explanation"]
        self.assertIn("no-such-run", explanation)

    def test_a_file_changed_after_the_run_is_not_a_candidate(self) -> None:
        first = self._run()
        path = self.runs / first["run_id"] / "joint_result.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"annual_room_cost_ore"', '"annual_room_cost_ore" ', 1), encoding="utf-8")
        source, reasons = inspect_run(self.runs, first["run_id"])
        self.assertIsNone(source)
        self.assertIn("SHA-256", " ".join(reasons))
        self.assertEqual(self._run()["warm_start"]["decision"], "not_used")

    def test_a_stored_pass_is_not_trusted_when_the_validator_fails_now(self) -> None:
        first = self._run()
        directory = self.runs / first["run_id"]
        stored = json.loads((directory / "joint_validation.json").read_text(encoding="utf-8"))
        self.assertTrue(stored["summary"]["technically_validated"])
        result = json.loads((directory / "joint_result.json").read_text(encoding="utf-8"))
        result["costs"]["annual_room_cost_ore"] += 1  # a wrong cost, with the manifest brought up to date
        (directory / "joint_result.json").write_text(json.dumps(result), encoding="utf-8")
        manifest = json.loads((directory / "joint_manifest.json").read_text(encoding="utf-8"))
        manifest["result_sha256"] = sha256_file(directory / "joint_result.json")
        (directory / "joint_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertFalse(validate_run(directory)["summary"]["technically_validated"])
        source, reasons = inspect_run(self.runs, first["run_id"])
        self.assertIsNone(source)
        self.assertIn("godkänner den inte nu", " ".join(reasons))

    def test_a_stored_failure_makes_the_run_unusable_even_if_the_files_look_fine(self) -> None:
        first = self._run()
        path = self.runs / first["run_id"] / "joint_validation.json"
        stored = json.loads(path.read_text(encoding="utf-8"))
        stored["summary"]["technical_validation"] = "fail"
        path.write_text(json.dumps(stored), encoding="utf-8")
        self.assertIn("underkänd", " ".join(inspect_run(self.runs, first["run_id"])[1]))

    def test_a_run_without_a_placement_is_not_a_candidate(self) -> None:
        first = self._run()
        directory = self.runs / first["run_id"]
        result = json.loads((directory / "joint_result.json").read_text(encoding="utf-8"))
        result.update(schedule=[], assignments=[], room_sessions=[])
        result["solver"]["outcome"] = "no_feasibility_conclusion"
        (directory / "joint_result.json").write_text(json.dumps(result), encoding="utf-8")
        manifest = json.loads((directory / "joint_manifest.json").read_text(encoding="utf-8"))
        manifest["result_sha256"] = sha256_file(directory / "joint_result.json")
        (directory / "joint_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn("ingen fullständig placering", " ".join(inspect_run(self.runs, first["run_id"])[1]))

    def test_automatic_choice_takes_the_newest_usable_run_of_the_same_problem(self) -> None:
        older, newer = self._run(), self._run()
        self.assertEqual(find_start(self.runs, self._problem()).source.run_id, newer["run_id"])
        path = self.runs / newer["run_id"] / "joint_result.json"
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")  # now corrupt
        choice = find_start(self.runs, self._problem())
        self.assertEqual(choice.source.run_id, older["run_id"])
        self.assertFalse(choice.considered[0]["usable_candidate"])
        other = replace(self._problem(), problem_id="something-else")
        self.assertIsNone(find_start(self.runs, other).source)

    def test_runs_of_other_problems_and_an_empty_directory_give_no_start(self) -> None:
        self.assertIsNone(find_start(self.runs, self._problem()).source)  # runs directory does not exist yet
        self._run()
        self.assertIsNone(find_start(self.runs, replace(self._problem(), problem_id="other")).source)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.scenario = _write_pair_dataset(self.dir)
        self.runs = self.dir / "runs"

    def _main(self, *args: str) -> tuple[int, dict]:
        time.sleep(1.05)
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["optimize-joint", "--config", str(self.scenario), "--processed-dir", str(self.dir),
                         "--runs-dir", str(self.runs), *args])
        return code, json.loads(stdout.getvalue())

    def test_warm_start_is_the_default_and_the_options_control_it(self) -> None:
        code, first = self._main()
        self.assertEqual((code, first["run"]["warm_start"]["decision"]), (0, "not_used"))
        code, second = self._main("--threads", "2", "--memory-mb", "512")
        self.assertEqual((code, second["run"]["warm_start"]["decision"]), (0, "accepted"))
        self.assertEqual(second["run"]["warm_start"]["execution"], {"threads": 2, "memory_mb": 512, "parallel_day_checks": True, "workers_per_check": 0})
        code, third = self._main("--warm-start", "none", "--sequential-day-checks")
        self.assertEqual((code, third["run"]["warm_start"]["decision"]), (0, "not_used"))
        self.assertFalse(third["run"]["warm_start"]["execution"]["parallel_day_checks"])
        code, named = self._main("--warm-start", first["run"]["run_id"])
        self.assertEqual(named["run"]["warm_start"]["source"]["run_id"], first["run"]["run_id"])
        costs = {item["run"]["result"]["costs"]["comparable_total_cost_ore"] for item in (first, second, third, named)}
        self.assertEqual(len(costs), 1)

    def test_a_rejected_start_still_gives_a_validated_result_and_says_why(self) -> None:
        _code, first = self._main()
        self.assertEqual(len({row["slot_id"] for row in first["run"]["result"]["schedule"]}), 2)  # one room, one exam per slot
        # The user removes the 14:00 start time. A start that used it can no longer be reused whole.
        self.scenario.write_text(PAIR_SCENARIO.replace('["08:00", "14:00"]', '["08:00"]'), encoding="utf-8")
        code, second = self._main()
        decision = second["run"]["warm_start"]
        self.assertEqual(code, 0)
        self.assertEqual(decision["decision"], "rejected")
        self.assertIn("tillåts inte", decision["explanation"])
        self.assertEqual(decision["recheck"]["hint_exams"], 1)
        self.assertIn("calendar.start_times", decision["changed_parameters"])
        self.assertEqual(second["run"]["validation"]["technical_validation"], "pass")
        self.assertEqual(second["run"]["result"]["solver"]["outcome"], "optimal")
        _code, cold = self._main("--warm-start", "none")
        self.assertEqual(second["run"]["result"]["costs"], cold["run"]["result"]["costs"])


if __name__ == "__main__":
    unittest.main()
