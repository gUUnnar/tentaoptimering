"""Regression tests for the review of the UX branch.

- A failed finalization never ends the event log as a success.
- A failed job reports its error as text, and the events response carries the run's real elapsed time.
- The summary validates the saved run now, names the changed parameters, and reports no cost for a run that is not verified.
- A comparison never presents a changed price or volume assumption as a scheduling improvement.
- The bundled scenario says which period it covers.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_api import Workspace, _wait_for_end  # noqa: E402
from test_joint_scenarios_api import _run  # noqa: E402
from test_joint_validation_run import CATALOG  # noqa: E402
from tentaoptimering import joint_api, joint_inputs  # noqa: E402
from tentaoptimering.joint_progress import EVENTS_FILE, read_events  # noqa: E402
from tentaoptimering.parameter_catalog import load_parameter_catalog  # noqa: E402
from tentaoptimering.provenance import sha256_file  # noqa: E402

SCENARIOS = Path(__file__).resolve().parents[1] / "config" / "scenarios"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _change_result(directory: Path, update_manifest: bool) -> None:
    """A result that changed after its run: wrong cost, with or without a manifest brought up to date."""
    path = directory / "joint_result.json"
    result = _read(path)
    result["costs"]["annual_room_cost_ore"] += 1
    path.write_text(json.dumps(result), encoding="utf-8")
    if update_manifest:
        manifest = _read(directory / "joint_manifest.json")
        manifest["result_sha256"] = sha256_file(path)
        (directory / "joint_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class FailedFinalizationTests(unittest.TestCase):
    def test_a_failure_after_the_solver_does_not_leave_a_success_as_the_last_event(self) -> None:
        workspace = Workspace(self)
        with mock.patch.object(joint_inputs, "_save_and_validate", side_effect=OSError("disk full")):
            end = _wait_for_end(workspace.jobs, workspace.start()["job_id"])
        self.assertEqual(end["status"], "failed")
        self.assertEqual(end["events"][-1]["type"], "finished")
        self.assertEqual((end["events"][-1]["outcome"], end["events"][-1]["cost_ore"]), ("failed", None))
        self.assertIn("OSError: disk full", end["events"][-1]["error"])
        self.assertEqual([event for event in end["events"] if event["type"] == "finished" and event["outcome"] != "failed"], [])
        self.assertEqual(sum(event["type"] == "finished" for event in end["events"]), 1)
        saved = [path for path in workspace.storage.runs_dir.iterdir() if not path.name.startswith(".")]
        self.assertEqual(len(saved), 1)  # the log of the failed run is kept, and it too ends as failed
        log = read_events(saved[0] / EVENTS_FILE)
        self.assertEqual((log[-1]["type"], log[-1]["outcome"]), ("finished", "failed"))

    def test_a_successful_run_still_ends_with_the_solvers_finished_event_after_the_artifacts(self) -> None:
        workspace = Workspace(self)
        end = _wait_for_end(workspace.jobs, workspace.start()["job_id"])
        self.assertEqual(end["status"], "completed")
        last = end["events"][-1]
        self.assertEqual((last["type"], last["outcome"]), ("finished", "optimal"))
        self.assertTrue((workspace.storage.runs_dir / end["run_id"] / "joint_validation.json").is_file())


class EventsResponseTests(unittest.TestCase):
    def test_the_error_is_text_and_the_elapsed_time_is_the_runs_own(self) -> None:
        workspace = Workspace(self)
        (workspace.storage.processed_dir / "optimization_demands.csv").unlink()
        end = _wait_for_end(workspace.jobs, workspace.start()["job_id"])
        self.assertEqual(end["status"], "failed")
        self.assertIsInstance(end["error"], str)
        self.assertTrue(end["error"].startswith("FileNotFoundError: "))
        self.assertEqual(end["elapsed_seconds"], end["events"][-1]["t"])

    def test_the_elapsed_time_of_a_running_job_grows_and_a_finished_ones_stands_still(self) -> None:
        workspace = Workspace(self)
        job = workspace.start()
        first = joint_api.job_events(workspace.jobs, job["job_id"])["elapsed_seconds"]
        end = _wait_for_end(workspace.jobs, job["job_id"])
        self.assertGreaterEqual(first, 0)
        self.assertEqual(end["elapsed_seconds"], end["events"][-1]["t"])
        self.assertEqual(joint_api.job_events(workspace.jobs, job["job_id"])["elapsed_seconds"], end["elapsed_seconds"])


class SummaryTests(unittest.TestCase):
    def test_changed_parameters_are_listed_by_id(self) -> None:
        workspace = Workspace(self)
        run_id = _run(workspace, parameters={"cost.staff_annual_ore": 3000})
        summary = joint_api.run_summary(workspace.storage, run_id)
        self.assertEqual(summary["parameters_changed_from_default"], sorted(summary["parameters_changed_from_default"]))
        self.assertTrue(all(isinstance(item, str) for item in summary["parameters_changed_from_default"]))
        self.assertIn("cost.staff_annual_ore", summary["parameters_changed_from_default"])
        self.assertEqual(summary["parameters_changed_count"], len(summary["parameters_changed_from_default"]))

    def test_a_verified_run_reports_its_cost_and_says_it_was_validated_now(self) -> None:
        workspace = Workspace(self)
        summary = joint_api.run_summary(workspace.storage, _run(workspace))
        self.assertTrue(summary["has_verified_solution"])
        self.assertIsNone(summary["unverified_reason"])
        self.assertIsInstance(summary["cost_ore"], int)
        self.assertEqual(summary["verdicts"]["source"], "validated_now")

    def test_a_result_that_changed_after_its_run_is_not_verified_and_has_no_cost(self) -> None:
        workspace = Workspace(self)
        run_id = _run(workspace)
        before = joint_api.run_summary(workspace.storage, run_id)
        self.assertTrue(before["has_verified_solution"])
        _change_result(workspace.storage.runs_dir / run_id, update_manifest=False)
        summary = joint_api.run_summary(workspace.storage, run_id)
        self.assertFalse(summary["has_verified_solution"])
        self.assertIn("manifestet", summary["unverified_reason"])
        for field in ("cost_ore", "lower_bound_ore", "gap_ore", "gap_relative", "changed_exams", "staff_pool_size"):
            self.assertIsNone(summary[field], field)
        self.assertFalse(summary["cost_is_proven_optimum"])
        self.assertFalse(summary["verdicts"]["technically_validated"])

    def test_a_stored_pass_is_not_trusted_when_the_validation_fails_now(self) -> None:
        workspace = Workspace(self)
        run_id = _run(workspace)
        directory = workspace.storage.runs_dir / run_id
        self.assertEqual(_read(directory / "joint_validation.json")["summary"]["technical_validation"], "pass")
        _change_result(directory, update_manifest=True)  # the stored joint_validation.json still says pass
        summary = joint_api.run_summary(workspace.storage, run_id)
        self.assertEqual(summary["verdicts"]["technical_validation"], "fail")
        self.assertFalse(summary["has_verified_solution"])
        self.assertIsNone(summary["cost_ore"])
        self.assertIn("eftervalideringen godkänner inte", summary["unverified_reason"])

    def test_such_a_run_is_never_compared(self) -> None:
        workspace = Workspace(self)
        first, second = _run(workspace), _run(workspace)
        _change_result(workspace.storage.runs_dir / first, update_manifest=True)
        result = joint_api.compare_runs(workspace.storage, second, first, load_parameter_catalog(CATALOG))
        self.assertFalse(result["comparable"])
        self.assertIn("verifierad lösning", result["reason"])
        self.assertTrue(all(item["delta"] is None for item in result["metrics"].values()))
        self.assertIsNone(result["interpretable"])


class AssumptionComparisonTests(unittest.TestCase):
    catalog = load_parameter_catalog(CATALOG)

    def _compare(self, **changed):
        workspace = Workspace(self)
        first = _run(workspace)
        second = _run(workspace, parameters=changed)
        return joint_api.compare_runs(workspace.storage, second, first, self.catalog)

    def test_a_cheaper_room_price_is_a_changed_assumption_not_an_efficiency_gain(self) -> None:
        result = self._compare(**{"cost.room_annual_per_seat_ore": 50})
        self.assertTrue(result["comparable"])
        self.assertEqual(result["assumption_changes"]["cost"], ["Årlig lokalkostnad per plats"])
        self.assertIs(result["interpretable"], False)
        self.assertIn("Kostnads- och bemanningsantagandena har ändrats (Årlig lokalkostnad per plats)", result["interpretation"])
        self.assertTrue(all(result["metrics"][name]["delta"] is None for name in ("cost_ore", "lower_bound_ore", "gap_ore")))  # N-5
        self.assertIn("effektivare schemaläggning", result["interpretation"])
        self.assertIn("modellkostnad", result["interpretation"])
        self.assertTrue(result["metrics"]["rooms_used"]["new"] is not None)  # the physical measures are still there

    def test_a_changed_volume_is_named_too(self) -> None:
        result = self._compare(**{"demand.variation_pct": 10})
        self.assertEqual(result["assumption_changes"]["demand"], ["Förändrat antal tentander"])
        self.assertIs(result["interpretable"], False)
        self.assertIn("Efterfrågan har ändrats (Förändrat antal tentander)", result["interpretation"])
        self.assertIsNone(result["metrics"]["cost_ore"]["delta"])  # a changed volume is not a planning effect (N-3)

    def test_both_kinds_at_once_are_named_together(self) -> None:
        result = self._compare(**{"demand.variation_pct": 10, "cost.staff_annual_ore": 3000})
        self.assertIn("Kostnads- och bemanningsantagandena har ändrats", result["interpretation"])
        self.assertIn("och efterfrågan har ändrats", result["interpretation"])

    def test_a_change_of_a_rule_is_not_called_an_assumption(self) -> None:
        result = self._compare(**{"window.later_days": 1})
        self.assertEqual(result["assumption_changes"], {"cost": [], "demand": []})
        self.assertNotIn("antagandena", result["interpretation"])


class BundledScenarioTests(unittest.TestCase):
    def test_the_whole_underlay_scenario_says_which_period_it_covers(self) -> None:
        content = tomllib.loads((SCENARIOS / "joint_underlay_period.toml").read_text(encoding="utf-8"))
        scenario, subset = content["scenario"], content["subset"]
        self.assertNotIn("terminen", scenario["name"].lower())
        self.assertNotIn("VT", scenario["name"])
        self.assertIn("12 jan", scenario["name"])
        self.assertIn("31 mars", scenario["name"])
        self.assertIn("april–juni", scenario["description"])
        self.assertEqual((subset["date_from"], subset["date_to"]), ("2026-01-12", "2026-03-31"))
        self.assertFalse((SCENARIOS / "joint_full_term.toml").exists())


if __name__ == "__main__":
    unittest.main()
