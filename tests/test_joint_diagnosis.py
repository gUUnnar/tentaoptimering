from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tentaoptimering.app_storage import AppStorage
from tentaoptimering.joint_diagnosis import SCENARIO_COPY, _classify, _with_change, diagnose_run, run_changes
from tentaoptimering.joint_scenarios import read_scenario
from tentaoptimering.joint_strategy.resources import CancelToken

BUNDLED = Path(__file__).resolve().parents[1] / "config" / "scenarios" / "joint_underlay_period.toml"


class DiagnosisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = AppStorage(Path(self.temporary.name))
        self.baseline = BUNDLED.read_text(encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _run(self, text: str, run_id: str = "20261013T000000Z-joint_underlay_period_2026") -> str:
        directory = self.storage.runs_dir / run_id
        directory.mkdir()
        (directory / SCENARIO_COPY).write_text(text, encoding="utf-8")
        return run_id

    def test_a_run_that_changed_nothing_has_no_changes(self) -> None:
        found = run_changes(self.storage, self._run(self.baseline))
        self.assertEqual((found["changes"], found["scenario_id"]), ([], "joint_underlay_period"))

    def test_changed_parameters_and_period_are_listed_with_old_and_new_values(self) -> None:
        text = self.baseline.replace('"calendar.weekdays" = [1, 2, 3, 4, 5, 6, 7]', '"calendar.weekdays" = [1, 2, 3, 4, 5]')
        text = text.replace('date_to = "2026-03-31"', 'date_to = "2026-02-27"')
        changes = {item["id"]: item for item in run_changes(self.storage, self._run(text))["changes"]}
        self.assertEqual(set(changes), {"calendar.weekdays", "subset.date_to"})
        self.assertEqual((changes["calendar.weekdays"]["baseline"], changes["calendar.weekdays"]["run"]), ([1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5]))
        self.assertEqual(changes["subset.date_to"]["run"], "2026-02-27")

    def test_a_run_without_a_saved_scenario_copy_cannot_be_investigated(self) -> None:
        (self.storage.runs_dir / "tom").mkdir()
        with self.assertRaises(FileNotFoundError):
            run_changes(self.storage, "tom")

    def test_a_probe_applies_exactly_one_change_to_the_original_and_shortens_the_time_limit(self) -> None:
        text = self.baseline.replace('"calendar.weekdays" = [1, 2, 3, 4, 5, 6, 7]', '"calendar.weekdays" = [1, 2, 3, 4, 5]')
        found = run_changes(self.storage, self._run(text))
        baseline_content = read_scenario(BUNDLED)
        probe = _with_change(found["_baseline"], found["changes"][0])
        self.assertEqual(probe["parameters"]["calendar.weekdays"], [1, 2, 3, 4, 5])
        self.assertEqual(probe["parameters"]["solver.time_limit_seconds"], 30.0)
        untouched = _with_change(found["_baseline"], None)
        self.assertEqual(untouched["parameters"]["calendar.weekdays"], baseline_content["parameters"]["calendar.weekdays"])
        self.assertEqual(found["_baseline"]["parameters"]["solver.time_limit_seconds"], baseline_content["parameters"]["solver.time_limit_seconds"])

    def test_only_proven_infeasibility_counts_as_a_cause(self) -> None:
        self.assertEqual([_classify(name) for name in ("infeasible", "optimal", "feasible_not_proven", "no_feasibility_conclusion", "x")],
                         ["infeasible", "solution", "solution", "inconclusive", "inconclusive"])

    def test_a_cancelled_diagnosis_is_saved_as_incomplete(self) -> None:
        text = self.baseline.replace('"calendar.weekdays" = [1, 2, 3, 4, 5, 6, 7]', '"calendar.weekdays" = [1, 2, 3, 4, 5]')
        run_id = self._run(text)
        cancel = CancelToken()
        cancel.cancel()
        result = diagnose_run(self.storage, run_id, None, cancel)
        self.assertEqual((result["complete"], result["probes"], result["culprits"]), (False, [], []))


if __name__ == "__main__":
    unittest.main()
