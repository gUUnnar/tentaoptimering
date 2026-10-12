"""The API contract between backend and frontend, as snapshots of real responses.

The files in `frontend/src/lib/testing/contract/` are real responses of the API (from a small synthetic run). This
test builds the same responses again and compares their SHAPE: the names of the fields and the kind of value in each
(text, number, truth value, nothing, list, object). If a backend response changes shape, this test fails until the
snapshot is renewed (`UPDATE_CONTRACT=1`), and the frontend tests, which feed the same files through the client's
adapters, then show what the interface must follow. Values (ids, times, amounts) are not compared.

A test in each part used to check its own idea of the contract, and both passed while the real responses did not
match (a count where a list was expected). This is the shared fact that both sides test against.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_api import Workspace, _wait_for_end  # noqa: E402
from test_joint_review_fixes import _change_result  # noqa: E402
from test_joint_scenarios_api import _run  # noqa: E402
from test_joint_validation_run import CATALOG  # noqa: E402
from tentaoptimering import joint_api, joint_inputs  # noqa: E402
from tentaoptimering.parameter_catalog import load_parameter_catalog  # noqa: E402

CONTRACT_DIR = Path(__file__).resolve().parents[1] / "frontend" / "src" / "lib" / "testing" / "contract"


def shape(value):
    """What a value is, not what it says."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted({json.dumps(shape(item), sort_keys=True) for item in value})
    if value is None:
        return "nothing"
    if isinstance(value, bool):
        return "truth value"
    if isinstance(value, (int, float)):
        return "number"
    return "text"


def one_event_per_type(response: dict) -> dict:
    """The events response with one example of each kind of event, so that the snapshot stays small."""
    seen, events = set(), []
    for event in response["events"]:
        key = (event["type"], event.get("kind"), event.get("status"), event.get("outcome"))
        if key not in seen:
            seen.add(key)
            events.append(event)
    return {**response, "events": events}


def build() -> dict[str, dict]:
    """The responses of the contract, from real runs. A failing and an unverified run are made on purpose."""
    catalog = load_parameter_catalog(CATALOG)
    workspace = Workspace.__new__(Workspace)  # filled in by `fresh` below; kept simple: one workspace per case
    out: dict[str, dict] = {}

    class Case(unittest.TestCase):
        def runTest(self) -> None:  # pragma: no cover - only used as a cleanup owner
            pass

    owner = Case()
    workspace = Workspace(owner)
    first = _run(workspace)
    second = _run(workspace, parameters={"cost.staff_annual_ore": 3000, "window.later_days": 1})
    job = workspace.start()
    done = _wait_for_end(workspace.jobs, job["job_id"])
    out["events_completed"] = one_event_per_type(done)
    out["summary_verified"] = joint_api.run_summary(workspace.storage, second)
    out["compare_assumption_changed"] = joint_api.compare_runs(workspace.storage, second, first, catalog)
    out["compare_no_previous"] = joint_api.compare_runs(workspace.storage, first, "previous", catalog)
    _change_result(workspace.storage.runs_dir / first, update_manifest=True)
    out["summary_unverified"] = joint_api.run_summary(workspace.storage, first)
    out["compare_unverified_base"] = joint_api.compare_runs(workspace.storage, second, first, catalog)
    failing = Workspace(owner)
    with mock.patch.object(joint_inputs, "_save_and_validate", side_effect=OSError("disk full")):
        out["events_failed"] = one_event_per_type(_wait_for_end(failing.jobs, failing.start()["job_id"]))
    owner.doCleanups()
    return out


class ContractSnapshotTests(unittest.TestCase):
    def test_the_responses_of_the_api_keep_the_shape_that_the_frontend_is_tested_against(self) -> None:
        built = build()
        if os.environ.get("UPDATE_CONTRACT") == "1":
            CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
            for name, response in built.items():
                (CONTRACT_DIR / f"{name}.json").write_text(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for name, response in built.items():
            path = CONTRACT_DIR / f"{name}.json"
            self.assertTrue(path.is_file(), f"{path.name} saknas; kör med UPDATE_CONTRACT=1")
            with self.subTest(snapshot=name):
                self.assertEqual(shape(json.loads(path.read_text(encoding="utf-8"))), shape(response),
                                 f"{name}: backendens svar har ändrat form. Förnya ögonblicksbilden (UPDATE_CONTRACT=1) och låt frontend följa.")

    def test_the_snapshots_show_the_cases_the_review_found(self) -> None:
        def load(name: str) -> dict:
            return json.loads((CONTRACT_DIR / f"{name}.json").read_text(encoding="utf-8"))

        verified, unverified = load("summary_verified"), load("summary_unverified")
        self.assertIsInstance(verified["parameters_changed_from_default"], list)  # ids, not a count
        self.assertTrue(verified["parameters_changed_from_default"])
        self.assertTrue(verified["has_verified_solution"])
        self.assertFalse(unverified["has_verified_solution"])
        self.assertIsNone(unverified["cost_ore"])  # no cost without a verified solution
        self.assertIsInstance(load("events_failed")["error"], str)  # text, not an object
        self.assertIn("elapsed_seconds", load("events_completed"))
        compared = load("compare_assumption_changed")
        self.assertIs(compared["interpretable"], False)
        self.assertEqual(compared["assumption_changes"]["cost"], ["Årskostnad per vaktresurs"])
        self.assertIsNone(load("compare_unverified_base")["interpretable"])


if __name__ == "__main__":
    unittest.main()
