"""The pre-check on the synthetic two-exam dataset of `test_joint_validation_run`: it saves nothing and gives an honest verdict."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_api import Workspace  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest, ParameterValidationError, run_config  # noqa: E402
from tentaoptimering.joint_precheck import _days, precheck  # noqa: E402
from tentaoptimering.joint_strategy.resources import CancelToken  # noqa: E402


class PrecheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Workspace(self)

    def _check(self, **parameters) -> dict:
        request = JointRunRequest(scenario="case", parameters=parameters)
        config, snapshot = run_config(self.workspace.storage, request, self.workspace.scenarios)
        return precheck(self.workspace.storage, config, snapshot, CancelToken())

    def test_settings_that_work_are_reported_as_possible_and_nothing_is_saved(self) -> None:
        result = self._check()
        self.assertEqual((result["verdict"], result["exams_total"], result["blocked_exams"]), ("possible", 2, 0))
        self.assertIn("En lösning hittades", " ".join(result["reasons"]))
        self.assertEqual(list(self.workspace.storage.runs_dir.glob("*")), [self.workspace.storage.snapshots_dir])  # no run, no leftover
        self.assertEqual(list(self.workspace.storage.snapshots_dir.glob("*")), [])

    def test_exams_with_no_allowed_occasion_are_named_as_blocking(self) -> None:
        result = self._check(**{"calendar.weekdays": [7], "window.earlier_days": 0, "window.later_days": 0})
        self.assertEqual((result["verdict"], result["blocked_exams"], result["solver_outcome"]), ("blocked", 2, "blocked"))
        self.assertIn("inget tillåtet tillfälle", result["reasons"][0])

    def test_a_bad_value_is_refused_per_parameter_before_anything_is_checked(self) -> None:
        with self.assertRaises(ParameterValidationError):
            self._check(**{"window.earlier_days": "många"})

    def test_days_are_written_in_the_singular_and_plural(self) -> None:
        self.assertEqual((_days(1), _days(2)), ("1 dag", "2 dagar"))


if __name__ == "__main__":
    unittest.main()
