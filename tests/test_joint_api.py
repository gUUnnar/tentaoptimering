"""Starting, observing, cancelling and summarising a joint run through the API layer.

The helper functions in `joint_api` carry the logic of the routes, so most tests call them directly with a real
job manager and real runs on a tiny dataset; the HTTP tests check the routes, status codes and id validation.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import uvicorn
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from test_joint_strategy import _dense_case  # noqa: E402
from test_joint_validation_run import _write_pair_dataset  # noqa: E402
from tentaoptimering import joint_api  # noqa: E402
from tentaoptimering.api import create_app  # noqa: E402
from tentaoptimering.app_storage import AppStorage  # noqa: E402
from tentaoptimering.job_manager import LocalJobManager  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest  # noqa: E402
from tentaoptimering.joint_progress import EVENTS_FILE, read_events  # noqa: E402


def _wait_for_end(jobs: LocalJobManager, job_id: str, seconds: float = 120.0) -> dict:
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        payload = joint_api.job_events(jobs, job_id)
        if payload["status"] != "running":
            return payload
        time.sleep(0.05)
    raise AssertionError("the job did not end in time")


class Workspace:
    """An app data directory with processed data and one joint scenario ('case') to run."""

    def __init__(self, test: unittest.TestCase, dense: bool = False) -> None:
        temp = tempfile.TemporaryDirectory()
        test.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.storage = AppStorage(self.root / "app")
        self.scenarios = self.root / "scenarios"
        self.scenarios.mkdir()
        if dense:
            events, rooms, overrides = _dense_case(12)
            fx._solve(self.storage.processed_dir, events, rooms, {**overrides, "solver.time_limit_seconds": 60.0, "solver.workers": 2})
            source = self.storage.processed_dir / "scenario.toml"
        else:
            source = _write_pair_dataset(self.storage.processed_dir)
        shutil.copy(source, self.scenarios / "case.toml")
        self.jobs = LocalJobManager()
        test.addCleanup(self.jobs.shutdown)

    def start(self, **fields) -> dict:
        request = JointRunRequest(scenario="case", **{"warm_start": "none", "threads": 2, **fields})
        return joint_api.start_joint_run(self.jobs, self.storage, request, self.scenarios)


class StartAndObserveTests(unittest.TestCase):
    def test_the_bundled_joint_scenarios_are_listed_and_other_engines_are_not(self) -> None:
        ids = {row["id"] for row in joint_api.list_scenarios()}
        self.assertIn("joint_real_subset", ids)
        self.assertNotIn("reference", ids)
        self.assertNotIn("integrated_term_exploratory", ids)
        row = next(item for item in joint_api.list_scenarios() if item["id"] == "joint_real_subset")
        self.assertEqual(row["schema_version"], "joint-real-subset-v1")
        self.assertEqual({row["id"] for row in joint_api.list_scenarios(Workspace(self).scenarios)}, {"case"})

    def test_ids_that_could_leave_their_directory_are_refused(self) -> None:
        workspace = Workspace(self)
        for bad in ("../case", "case/../case", "Case", "", "a" * 100, "case.toml"):
            with self.subTest(scenario=bad):
                with self.assertRaises(ValueError):
                    joint_api.scenario_path(bad, workspace.scenarios)
                with self.assertRaises(ValidationError):
                    JointRunRequest(scenario=bad)
        with self.assertRaises(FileNotFoundError):
            joint_api.scenario_path("missing", workspace.scenarios)
        for bad in ("../x", "a b", "x/y", "", "."):
            with self.subTest(warm_start=bad), self.assertRaises(ValidationError):
                JointRunRequest(scenario="case", warm_start=bad)
        for fields in ({"threads": -1}, {"memory_mb": 0}):
            with self.assertRaises(ValidationError):
                JointRunRequest(scenario="case", **fields)
        self.assertEqual(JointRunRequest(scenario="case").warm_start, "auto")
        for bad in ("../x", "..", "a/b", "a\\b"):
            with self.subTest(run=bad):
                for call in (joint_api.run_events, joint_api.run_summary):
                    with self.assertRaises(ValueError):
                        call(workspace.storage, bad)

    def test_a_job_is_observed_from_start_to_end_and_the_run_is_summarised_from_its_artifacts(self) -> None:
        workspace = Workspace(self)
        job = workspace.start(parallel_day_checks=False, memory_mb=2048)
        self.assertEqual((job["status"] in {"queued", "running", "completed"}, job["run_id"]), (True, None))
        end = _wait_for_end(workspace.jobs, job["job_id"])
        self.assertEqual(end["status"], "completed")
        run_id = end["run_id"]
        self.assertTrue(run_id)
        events = end["events"]
        self.assertEqual(end["last_seq"], events[-1]["seq"])
        self.assertEqual([event["seq"] for event in events], list(range(1, len(events) + 1)))
        resources = next(event for event in events if event["type"] == "resources")
        self.assertEqual((resources["threads"], resources["memory_mb"], resources["parallel_checks"]), (2, 2048, 1))
        middle = events[len(events) // 2]["seq"]
        later = joint_api.job_events(workspace.jobs, job["job_id"], after=middle)
        self.assertEqual([event["seq"] for event in later["events"]], list(range(middle + 1, end["last_seq"] + 1)))
        self.assertEqual(joint_api.job_events(workspace.jobs, job["job_id"], after=end["last_seq"])["events"], [])
        self.assertEqual(workspace.jobs.public(job["job_id"])["result"]["run_id"], run_id)
        self.assertNotIn("progress", workspace.jobs.public(job["job_id"]))

        saved = joint_api.run_events(workspace.storage, run_id)  # replay of the finished run
        self.assertEqual(saved["events"], events)
        self.assertEqual(saved["last_seq"], end["last_seq"])
        directory = workspace.storage.runs_dir / run_id
        self.assertEqual(read_events(directory / EVENTS_FILE), events)

        summary = joint_api.run_summary(workspace.storage, run_id)
        result = json.loads((directory / "joint_result.json").read_text(encoding="utf-8"))
        validation = json.loads((directory / "joint_validation.json").read_text(encoding="utf-8"))["summary"]
        self.assertEqual(summary["cost_ore"], result["solver"]["objective_value_ore"])
        self.assertEqual(summary["lower_bound_ore"], result["solver"]["best_objective_bound_ore"])
        self.assertEqual(summary["gap_ore"], summary["cost_ore"] - summary["lower_bound_ore"])
        self.assertEqual(summary["changed_exams"], result["changed_exam_demands"])
        self.assertEqual(summary["solver_outcome"], "optimal")
        self.assertTrue(summary["cost_is_proven_optimum"])
        self.assertTrue(summary["has_verified_solution"])
        self.assertIsNotNone(summary["first_solution_seconds"])
        self.assertFalse(summary["cancelled"])
        self.assertEqual(summary["verdicts"], {
            "technical_validation": validation["technical_validation"], "business_verification": validation["business_verification"],
            "provenance": validation["provenance"], "technically_validated": validation["technically_validated"],
            "source": "joint_validation.json",
        })
        self.assertEqual(summary["verdicts"]["technical_validation"], "pass")
        self.assertEqual(summary["verdicts"]["business_verification"], "not_evaluated")  # technically fine is not business-verified

    def test_a_second_job_waits_for_the_first_and_a_finished_job_cannot_be_cancelled(self) -> None:
        workspace = Workspace(self)
        job = workspace.start()
        with self.assertRaises(RuntimeError):
            workspace.start()
        _wait_for_end(workspace.jobs, job["job_id"])
        self.assertEqual(joint_api.cancel_job(workspace.jobs, job["job_id"])["cancel_requested"], False)
        with self.assertRaises(KeyError):
            joint_api.job_events(workspace.jobs, "nope")
        with self.assertRaises(KeyError):
            joint_api.cancel_job(workspace.jobs, "nope")
        other = workspace.jobs.start(lambda: {"kind": "other"})  # a job that is not a joint run
        with self.assertRaises(RuntimeError):
            joint_api.cancel_job(workspace.jobs, other["job_id"])
        with self.assertRaises(ValueError):
            joint_api.job_events(workspace.jobs, other["job_id"])

    def test_a_run_without_a_log_or_result_is_reported_as_missing(self) -> None:
        workspace = Workspace(self)
        (workspace.storage.runs_dir / "old-run").mkdir()
        with self.assertRaises(FileNotFoundError):
            joint_api.run_events(workspace.storage, "old-run")
        with self.assertRaises(FileNotFoundError):
            joint_api.run_summary(workspace.storage, "old-run")

    def test_a_failing_job_ends_with_a_finished_event_and_its_error(self) -> None:
        workspace = Workspace(self)
        for name in ("optimization_demands.csv",):
            (workspace.storage.processed_dir / name).unlink()  # the run cannot be built
        end = _wait_for_end(workspace.jobs, workspace.start()["job_id"])
        self.assertEqual(end["status"], "failed")
        self.assertEqual(end["error"]["type"], "FileNotFoundError")
        self.assertEqual(end["events"][-1]["type"], "finished")
        self.assertEqual((end["events"][-1]["outcome"], end["events"][-1]["cost_ore"]), ("failed", None))


class CancelTests(unittest.TestCase):
    def test_a_cancelled_job_leaves_a_complete_verified_result_or_none(self) -> None:
        workspace = Workspace(self, dense=True)
        for delay in (0.0, 0.5):
            with self.subTest(delay=delay):
                time.sleep(1.05)  # run ids carry the time in seconds
                job = workspace.start()
                time.sleep(delay)
                reply = joint_api.cancel_job(workspace.jobs, job["job_id"])
                end = _wait_for_end(workspace.jobs, job["job_id"])
                self.assertIn(end["status"], {"cancelled", "completed"})
                self.assertEqual(end["status"] == "cancelled", reply["cancel_requested"] and end["events"][-1]["cancelled"])
                self.assertEqual(end["events"][-1]["type"], "finished")
                summary = joint_api.run_summary(workspace.storage, end["run_id"])
                if summary["solver_outcome"] in ("optimal", "feasible_not_proven"):
                    # a placement exists: it is complete and the independent validation accepts it
                    self.assertTrue(summary["technical_placement_complete"])
                    self.assertTrue(summary["has_verified_solution"])
                    self.assertEqual(summary["verdicts"]["technical_validation"], "pass")
                    self.assertEqual(summary["exams_total"], json.loads(
                        (workspace.storage.runs_dir / end["run_id"] / "joint_result.json").read_text(encoding="utf-8"))["coverage"]["exam_demands_scheduled"])
                    self.assertEqual(summary["cancelled"], end["status"] == "cancelled")
                else:
                    # nothing is better than a partial placement: no cost, no schedule, and never a pass
                    self.assertEqual(summary["solver_outcome"], "no_feasibility_conclusion")
                    self.assertIsNone(summary["cost_ore"])
                    self.assertFalse(summary["technical_placement_complete"])
                    self.assertFalse(summary["has_verified_solution"])  # "pass" of an empty result is not a solution
                    self.assertTrue(summary["cancelled"])
                    result = json.loads((workspace.storage.runs_dir / end["run_id"] / "joint_result.json").read_text(encoding="utf-8"))
                    self.assertEqual(result["schedule"], [])


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = AppStorage(Path(self.temp.name))
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(create_app(self.storage.root), host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        end = time.perf_counter() + 10
        while time.perf_counter() < end and self._request("GET", "/api/health")[0] != 200:
            time.sleep(0.05)
        self.addCleanup(self._stop)

    def _stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)

    def _request(self, method: str, path: str, payload: object | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read() or b"{}")
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read() or b"{}")
        except OSError:
            return 0, {}

    def test_routes_validate_input_and_report_missing_things(self) -> None:
        status, scenarios = self._request("GET", "/api/joint-runs/scenarios")
        self.assertEqual(status, 200)
        self.assertIn("joint_real_subset", {row["id"] for row in scenarios["scenarios"]})
        self.assertEqual(self._request("GET", "/api/joint-runs/warm-start-candidates")[0], 200)  # the existing routes remain
        self.assertEqual(self._request("POST", "/api/joint-runs", {"scenario": "../x"})[0], 422)
        self.assertEqual(self._request("POST", "/api/joint-runs", {"scenario": "joint_real_subset", "warm_start": "../x"})[0], 422)
        self.assertEqual(self._request("POST", "/api/joint-runs", {"scenario": "joint_real_subset", "threads": -2})[0], 422)
        self.assertEqual(self._request("POST", "/api/joint-runs", {"scenario": "reference"})[0], 404)  # not a joint scenario
        self.assertEqual(self._request("GET", "/api/joint-runs/nope/events")[0], 404)
        self.assertEqual(self._request("GET", "/api/joint-runs/nope/events?after=-1")[0], 422)
        self.assertEqual(self._request("POST", "/api/joint-runs/nope/cancel")[0], 404)
        self.assertEqual(self._request("GET", "/api/runs/nope/events")[0], 404)
        self.assertEqual(self._request("GET", "/api/joint-runs/nope/summary")[0], 404)
        self.assertEqual(self._request("GET", "/api/joint-runs/..bad/summary")[0], 422)
        self.assertEqual(self._request("GET", "/api/runs/..bad/events")[0], 422)

    def test_a_job_started_over_http_can_be_followed_and_ends_with_its_error_when_the_data_is_missing(self) -> None:
        status, job = self._request("POST", "/api/joint-runs", {"scenario": "joint_real_subset", "warm_start": "none"})
        self.assertEqual(status, 200)
        self.assertEqual(self._request("POST", "/api/joint-runs", {"scenario": "joint_real_subset"})[0] in (200, 409), True)
        for _ in range(200):
            status, payload = self._request("GET", f"/api/joint-runs/{job['job_id']}/events?after=0")
            self.assertEqual(status, 200)
            if payload["status"] != "running":
                break
            time.sleep(0.05)
        self.assertEqual(payload["status"], "failed")  # the processed data is not in the empty test directory
        self.assertEqual(payload["events"][-1]["type"], "finished")
        self.assertEqual(set(payload), {"status", "events", "last_seq", "run_id", "error"})


if __name__ == "__main__":
    unittest.main()
