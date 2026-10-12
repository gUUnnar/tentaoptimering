"""Scenarios, parameter changes and run comparison through the API layer and the HTTP routes.

Real (tiny) runs on the synthetic two-exam dataset of `test_joint_validation_run`; comparison cases that need a
particular cost or gap are made by copying a real run and changing the numbers in the copy.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import socket
import sys
import threading
import time
import tomllib
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import uvicorn
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_api import Workspace, _wait_for_end  # noqa: E402
from test_joint_strategy import _two_day_problem  # noqa: E402
from test_joint_validation_run import CATALOG  # noqa: E402
from tentaoptimering import joint_api  # noqa: E402
from tentaoptimering.api import create_app  # noqa: E402
from tentaoptimering.app_storage import AppStorage  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest  # noqa: E402
from tentaoptimering.joint_compare import NO_PREVIOUS, interpret  # noqa: E402
from tentaoptimering.joint_optimizer import solve_joint_optimization  # noqa: E402
from tentaoptimering.joint_progress import ProgressSink  # noqa: E402
from tentaoptimering.joint_scenarios import (  # noqa: E402
    CHANGED_IN_UI, ParameterValidationError, ScenarioConflictError, ScenarioCreate, user_scenarios_dir,
)
from tentaoptimering.joint_strategy.resources import ExecutionBudget  # noqa: E402
from tentaoptimering.parameter_catalog import load_parameter_catalog  # noqa: E402
from tentaoptimering.provenance import sha256_file  # noqa: E402

PROBLEM = "pair"  # the scenario id inside the synthetic scenario file


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(workspace: Workspace, scenario: str = "case", **fields) -> str:
    """Start a run, wait for it, and make sure that the next run gets another second-resolution run id."""
    request = JointRunRequest(scenario=scenario, **{"warm_start": "none", "threads": 2, **fields})
    job = joint_api.start_joint_run(workspace.jobs, workspace.storage, request, workspace.scenarios)
    end = _wait_for_end(workspace.jobs, job["job_id"])
    assert end["status"] == "completed", end
    time.sleep(1.05)
    return end["run_id"]


def _crafted():
    """Runs with hand-made numbers cannot pass the independent validation. These tests are about the comparison,
    so the validation is replaced by one that accepts every complete run."""
    from tentaoptimering import joint_summary
    return mock.patch.object(joint_summary, "validated_now", lambda directory: {
        "technical_validation": "pass", "business_verification": "not_evaluated", "provenance": "not_evaluated",
        "technically_validated": True})


def _clone(storage: AppStorage, run_id: str, new_id: str, result: dict | None = None, problem: dict | None = None) -> str:
    """A copy of a saved run under another id, with changes to its result or input (for comparison cases)."""
    shutil.copytree(storage.runs_dir / run_id, storage.runs_dir / new_id)
    for name, changes in (("joint_result.json", result), ("joint_input.json", problem)):
        if changes:
            path = storage.runs_dir / new_id / name
            content = _read(path)
            for key, value in changes.items():
                if isinstance(value, dict):
                    content[key].update(value)
                else:
                    content[key] = value
            path.write_text(json.dumps(content), encoding="utf-8")
    return new_id


class ScenarioListTests(unittest.TestCase):
    def test_bundled_scenarios_describe_their_selection_and_count_exams_from_the_data(self) -> None:
        workspace = Workspace(self)
        rows = {row["id"]: row for row in joint_api.list_scenarios(storage=workspace.storage, processed_dir=workspace.storage.processed_dir)}
        term = rows["joint_underlay_period"]
        self.assertEqual((term["origin"], term["problem_id"], term["subset"]["selection"], term["subset"]["plan_area"]),
                         ("bundled", "joint_underlay_period_2026", "rule", "Uppsala"))
        self.assertEqual(term["subset"]["exam_count"], 2)  # counted in the (synthetic) prepared data: the two events of 12 January
        self.assertIn("Uppsala", term["subset"]["description"])
        small = rows["joint_real_subset"]
        self.assertEqual((small["subset"]["selection"], small["subset"]["exam_count"], small["problem_id"]), ("event_list", 12, "joint_real_subset_2026"))
        without_data = {row["id"]: row for row in joint_api.list_scenarios(storage=workspace.storage)}
        self.assertIsNone(without_data["joint_underlay_period"]["subset"]["exam_count"])
        self.assertEqual(set(term), {"id", "name", "description", "problem_id", "origin", "subset", "schema_version"})
        self.assertEqual(set(term["subset"]), {"plan_area", "selection", "exam_count", "description"})

    def test_a_saved_scenario_is_listed_as_the_users_own(self) -> None:
        workspace = Workspace(self)
        row = joint_api.create_scenario(workspace.storage, ScenarioCreate(
            name="mitt-test", description="Dyrare vakter", base="case", parameters={"cost.staff_annual_ore": 2000}),
            workspace.scenarios, CATALOG)
        self.assertEqual((row["id"], row["origin"], row["problem_id"], row["description"]), ("mitt-test", "user", "mitt-test", "Dyrare vakter"))
        path = user_scenarios_dir(workspace.storage) / "mitt-test.toml"
        self.assertEqual(path.parent, workspace.storage.root / "joint_scenarios")
        saved = tomllib.loads(path.read_text(encoding="utf-8"))
        base = tomllib.loads((workspace.scenarios / "case.toml").read_text(encoding="utf-8"))
        self.assertEqual(saved["schema_version"], "joint-real-subset-v1")
        self.assertEqual(saved["subset"], base["subset"])
        self.assertEqual(saved["parameters"], {**base["parameters"], "cost.staff_annual_ore": 2000})
        self.assertEqual(saved["rationales"]["cost.staff_annual_ore"], CHANGED_IN_UI)
        listed = {item["id"]: item for item in joint_api.list_scenarios(workspace.scenarios, workspace.storage)}
        self.assertEqual(listed["mitt-test"]["origin"], "user")
        self.assertEqual(listed["case"]["origin"], "bundled")
        self.assertEqual(tomllib.loads((workspace.scenarios / "case.toml").read_text(encoding="utf-8")), base)  # the base is untouched

    def test_names_that_are_taken_or_bad_and_values_that_are_wrong_are_refused(self) -> None:
        workspace = Workspace(self)
        make = lambda **fields: joint_api.create_scenario(  # noqa: E731
            workspace.storage, ScenarioCreate(**{"name": "ny", "base": "case", "parameters": {}, **fields}), workspace.scenarios, CATALOG)
        make()
        with self.assertRaises(ScenarioConflictError):
            make()  # taken
        with self.assertRaises(ScenarioConflictError):
            make(name="case")  # a bundled id
        with self.assertRaises(ScenarioConflictError):
            make(name=PROBLEM)  # a bundled problem id would make runs ambiguous
        with self.assertRaises(FileNotFoundError):
            make(name="annat", base="finns-inte")
        with self.assertRaises(ParameterValidationError) as caught:
            make(name="annat", parameters={"rules.student_conflicts": True, "window.earlier_days": -2, "nope": 1})
        self.assertEqual(sorted(item["id"] for item in caught.exception.errors), ["nope", "rules.student_conflicts", "window.earlier_days"])
        self.assertFalse((user_scenarios_dir(workspace.storage) / "annat.toml").exists())
        for bad in ("Bad Name", "../x", "", "a" * 90, "-x"):
            with self.assertRaises(ValidationError):
                ScenarioCreate(name=bad, base="case")
        self.assertEqual([path.name for path in user_scenarios_dir(workspace.storage).glob("*.toml")], ["ny.toml"])

    def test_a_scenario_can_be_made_from_a_saved_one(self) -> None:
        workspace = Workspace(self)
        for name, base, parameters in (("forst", "case", {"window.earlier_days": 2}), ("sedan", "forst", {"window.later_days": 2})):
            joint_api.create_scenario(workspace.storage, ScenarioCreate(name=name, base=base, parameters=parameters), workspace.scenarios, CATALOG)
        saved = tomllib.loads((user_scenarios_dir(workspace.storage) / "sedan.toml").read_text(encoding="utf-8"))
        self.assertEqual((saved["parameters"]["window.earlier_days"], saved["parameters"]["window.later_days"]), (2, 2))
        self.assertEqual((saved["scenario"]["id"], saved["scenario"]["base"]), ("sedan", "forst"))


class ParameterPayloadTests(unittest.TestCase):
    def test_the_payload_follows_the_scenario_it_is_asked_for(self) -> None:
        workspace = Workspace(self)
        payload = joint_api.parameters_payload(workspace.storage, "case", workspace.scenarios)
        rows = {row["id"]: row for row in payload["parameters"]}
        self.assertEqual((payload["scenario_id"], rows["cost.staff_annual_ore"]["scenario_value"], rows["cost.staff_annual_ore"]["value"]), ("case", 1000, 1000))
        self.assertEqual(rows["window.earlier_days"]["scenario_value"], None)
        joint_api.create_scenario(workspace.storage, ScenarioCreate(name="eget", base="case", parameters={"cost.staff_annual_ore": 7}),
                                  workspace.scenarios, CATALOG)
        own = {row["id"]: row for row in joint_api.parameters_payload(workspace.storage, "eget", workspace.scenarios)["parameters"]}
        self.assertEqual((own["cost.staff_annual_ore"]["value"], own["cost.staff_annual_ore"]["default"]), (7, 0))
        with self.assertRaises(FileNotFoundError):
            joint_api.parameters_payload(workspace.storage, "finns-inte", workspace.scenarios)
        with self.assertRaises(ValueError):
            joint_api.parameters_payload(workspace.storage, "../x", workspace.scenarios)


class ChangedParameterRunTests(unittest.TestCase):
    def test_a_run_with_changed_parameters_uses_a_snapshot_and_leaves_the_scenario_alone(self) -> None:
        workspace = Workspace(self)
        original = (workspace.scenarios / "case.toml").read_bytes()
        run_id = _run(workspace, parameters={"cost.staff_annual_ore": 4000, "window.earlier_days": 1})
        self.assertEqual((workspace.scenarios / "case.toml").read_bytes(), original)
        self.assertEqual(list(workspace.storage.snapshots_dir.glob("joint-*.toml")), [])  # the snapshot is removed after the run
        directory = workspace.storage.runs_dir / run_id
        used = tomllib.loads((directory / "joint_scenario.toml").read_text(encoding="utf-8"))
        base = tomllib.loads(original.decode("utf-8"))
        self.assertEqual(used["scenario"]["id"], base["scenario"]["id"])  # the same problem: warm start and comparison still work
        self.assertEqual(used["parameters"], {**base["parameters"], "cost.staff_annual_ore": 4000, "window.earlier_days": 1})
        self.assertEqual({key: used["rationales"][key] for key in ("cost.staff_annual_ore", "window.earlier_days")}, {
            "cost.staff_annual_ore": CHANGED_IN_UI, "window.earlier_days": CHANGED_IN_UI})
        self.assertEqual(used["subset"], base["subset"])
        values = {item["parameter_id"]: item for item in _read(directory / "joint_input.json")["parameters"]}
        self.assertEqual((values["cost.staff_annual_ore"]["value"], values["cost.staff_annual_ore"]["changed_from_default"]), (4000, True))
        self.assertTrue(values["cost.staff_annual_ore"]["rationale"].startswith("Ändrat"))
        manifest = _read(directory / "joint_manifest.json")
        self.assertEqual(manifest["config_sha256"], sha256_file(directory / "joint_scenario.toml"))
        validation = _read(directory / "joint_validation.json")["summary"]
        self.assertEqual(validation["technical_validation"], "pass")
        summary = joint_api.run_summary(workspace.storage, run_id)
        self.assertEqual((summary["scenario_id"], summary["problem_id"]), (PROBLEM, PROBLEM))  # no bundled scenario of that problem here
        self.assertEqual(joint_api.run_summary(workspace.storage, run_id, workspace.scenarios)["scenario_id"], "case")
        self.assertRegex(summary["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(summary["parameters_changed_from_default"], sorted(key for key, item in values.items() if item["changed_from_default"]))
        self.assertEqual(summary["parameters_changed_count"], len(summary["parameters_changed_from_default"]))

    def test_a_run_without_changes_runs_the_scenario_file_itself_and_keeps_a_copy(self) -> None:
        workspace = Workspace(self)
        original = (workspace.scenarios / "case.toml").read_bytes()
        run_id = _run(workspace, parameters={"cost.staff_annual_ore": 1000})  # already the scenario's value: no change
        self.assertEqual((workspace.storage.runs_dir / run_id / "joint_scenario.toml").read_bytes(), original)
        self.assertEqual(list(workspace.storage.snapshots_dir.glob("*.toml")), [])

    def test_a_bad_value_stops_the_run_before_anything_is_queued_and_says_which_parameter(self) -> None:
        workspace = Workspace(self)
        for parameters, ids in (({"rules.student_conflicts": True}, ["rules.student_conflicts"]),
                                ({"window.earlier_days": "1", "x.y": 1, "rooms.allow_split": 3}, ["rooms.allow_split", "window.earlier_days", "x.y"])):
            with self.subTest(parameters=parameters):
                with self.assertRaises(ParameterValidationError) as caught:
                    joint_api.start_joint_run(workspace.jobs, workspace.storage, JointRunRequest(scenario="case", parameters=parameters), workspace.scenarios)
                self.assertEqual(sorted(item["id"] for item in caught.exception.errors), ids)
        self.assertFalse(workspace.jobs.has_active_job())
        self.assertEqual(list(workspace.storage.runs_dir.glob("2*")), [])
        self.assertEqual(list(workspace.storage.snapshots_dir.glob("*.toml")), [])

    def test_changing_parameters_gives_the_same_result_as_editing_the_scenario_file(self) -> None:
        workspace = Workspace(self)
        changes = {"cost.staff_annual_ore": 2500, "cost.room_annual_per_seat_ore": 300}
        via_api = _run(workspace, parameters=changes)
        edited = (workspace.scenarios / "case.toml").read_text(encoding="utf-8")
        edited = edited.replace('"cost.room_annual_per_seat_ore" = 100', '"cost.room_annual_per_seat_ore" = 300')
        edited = edited.replace('"cost.staff_annual_ore" = 1000', '"cost.staff_annual_ore" = 2500')
        (workspace.scenarios / "by_hand.toml").write_text(edited, encoding="utf-8")
        by_hand = _run(workspace, scenario="by_hand")
        results = [_read(workspace.storage.runs_dir / run / "joint_result.json") for run in (via_api, by_hand)]
        for key in ("costs", "schedule", "staff_pool_size", "changed_exam_demands", "coverage"):
            self.assertEqual(results[0][key], results[1][key], key)
        self.assertEqual(results[0]["solver"]["objective_value_ore"], results[1]["solver"]["objective_value_ore"])
        inputs = [{item["parameter_id"]: item["value"] for item in _read(workspace.storage.runs_dir / run / "joint_input.json")["parameters"]}
                  for run in (via_api, by_hand)]
        self.assertEqual(inputs[0], inputs[1])

    def test_a_saved_scenario_can_be_run(self) -> None:
        workspace = Workspace(self)
        joint_api.create_scenario(workspace.storage, ScenarioCreate(name="eget", base="case", parameters={"cost.staff_annual_ore": 3000}),
                                  workspace.scenarios, CATALOG)
        run_id = _run(workspace, scenario="eget")
        self.assertTrue(run_id.endswith("-eget"))
        saved = (user_scenarios_dir(workspace.storage) / "eget.toml").read_bytes()
        self.assertEqual((workspace.storage.runs_dir / run_id / "joint_scenario.toml").read_bytes(), saved)
        self.assertEqual(joint_api.run_summary(workspace.storage, run_id)["scenario_id"], "eget")
        self.assertEqual(joint_api.run_summary(workspace.storage, run_id)["verdicts"]["technical_validation"], "pass")


class CompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_parameter_catalog(CATALOG)

    def test_two_runs_differ_in_one_parameter_and_the_cost_follows(self) -> None:
        workspace = Workspace(self)
        first = _run(workspace)
        second = _run(workspace, parameters={"cost.staff_annual_ore": 3000})
        result = joint_api.compare_runs(workspace.storage, second, "previous", self.catalog)
        self.assertEqual((result["run"]["run_id"], result["base"]["run_id"], result["comparable"], result["reason"]), (second, first, True, None))
        self.assertEqual(result["run"]["scenario_id"], PROBLEM)
        self.assertEqual(result["parameter_changes"], [{
            "id": "cost.staff_annual_ore", "label": "Årskostnad per vaktresurs", "group": "kostnad", "unit": "ore_per_year",
            "old": 1000, "new": 3000}])
        cost = result["metrics"]["cost_ore"]
        self.assertGreater(cost["new"], cost["old"])  # the amounts are shown, but no difference is reported (N-5)
        self.assertIsNone(cost["delta"])
        self.assertTrue(all(result["metrics"][name]["delta"] is None for name in ("cost_ore", "lower_bound_ore", "gap_ore")))
        self.assertEqual(set(result["metrics"]), {"cost_ore", "lower_bound_ore", "gap_ore", "changed_exams", "staff_pool_size", "rooms_used",
                                                  "wall_time_seconds", "first_solution_seconds"})
        self.assertTrue(all(set(item) == {"old", "new", "delta"} for item in result["metrics"].values()))
        self.assertGreaterEqual(result["metrics"]["rooms_used"]["new"], 1)
        self.assertEqual(result["uncertainty_ore"], 0)  # both runs proved their optimum
        # A changed price is a changed assumption: the difference is shown, but never called an efficiency gain.
        self.assertIs(result["interpretable"], False)
        self.assertEqual(result["assumption_changes"], {"cost": ["Årskostnad per vaktresurs"], "demand": []})
        self.assertIn("Kostnads- och bemanningsantagandena har ändrats (Årskostnad per vaktresurs)", result["interpretation"])
        self.assertIn("Ingen kostnadsskillnad redovisas", result["interpretation"])
        self.assertNotIn("Kostnaden ökade", result["interpretation"])
        self.assertIn("modellkostnad", result["interpretation"])
        self.assertEqual(joint_api.compare_runs(workspace.storage, second, first, self.catalog), result)  # an explicit base gives the same
        reverse = joint_api.compare_runs(workspace.storage, first, second, self.catalog)
        self.assertEqual(reverse["parameter_changes"][0]["old"], 3000)
        self.assertNotIn("sjönk", reverse["interpretation"])  # reversed or not, no cost difference is reported
        self.assertIsNone(reverse["metrics"]["cost_ore"]["delta"])

    def test_previous_is_the_closest_older_verified_run_of_the_same_problem(self) -> None:
        workspace = Workspace(self)
        current = _run(workspace)
        storage = workspace.storage
        newest_first = [
            _clone(storage, current, "29990101T000000Z-pair"),                       # newer: never the previous
            _clone(storage, current, "20250103T000000Z-other", result={"problem_id": "other"}),  # another problem
            _clone(storage, current, "20250102T000000Z-pair", result={"coverage": {"technical_placement_complete": False}}),  # not verified
            _clone(storage, current, "20250101T000000Z-pair"),
            _clone(storage, current, "20240101T000000Z-pair"),
        ]
        result = joint_api.compare_runs(storage, current, "previous", self.catalog)
        self.assertEqual(result["base"]["run_id"], "20250101T000000Z-pair")
        self.assertEqual(result["base"]["created_at"], "2025-01-01T00:00:00Z")
        self.assertTrue(result["comparable"])
        self.assertEqual(result["parameter_changes"], [])
        self.assertEqual(len(newest_first), 5)
        first_only = joint_api.compare_runs(storage, "20240101T000000Z-pair", "previous", self.catalog)
        self.assertIsNone(first_only["base"])
        self.assertEqual((first_only["comparable"], first_only["reason"]), (False, NO_PREVIOUS))
        self.assertEqual(NO_PREVIOUS, "Ingen tidigare körning av samma scenario")
        self.assertEqual(first_only["metrics"], {})
        self.assertIsNone(first_only["interpretable"])
        self.assertTrue(first_only["interpretation"])
        # an explicit base that is not verified is still shown, but cost is not compared
        explicit = joint_api.compare_runs(storage, current, "20250102T000000Z-pair", self.catalog)
        self.assertEqual((explicit["comparable"], explicit["base"]["has_verified_solution"]), (False, False))
        self.assertIsNone(explicit["metrics"]["cost_ore"]["delta"])

    def test_the_uncertainty_is_the_larger_gap_and_decides_what_may_be_read_into_a_difference(self) -> None:
        self.enterContext(_crafted())
        workspace = Workspace(self)
        current = _run(workspace)
        storage = workspace.storage
        cost = joint_api.run_summary(storage, current)["cost_ore"]
        close = _clone(storage, current, "20250101T000000Z-pair", result={"solver": {
            "outcome": "feasible_not_proven", "objective_value_ore": cost + 30_000, "best_objective_bound_ore": cost - 20_000}})
        result = joint_api.compare_runs(storage, current, close, self.catalog)
        self.assertEqual((result["uncertainty_ore"], result["metrics"]["cost_ore"]["delta"], result["metrics"]["gap_ore"]["delta"]), (50_000, -30_000, -50_000))
        self.assertIs(result["interpretable"], False)
        self.assertIn("mindre än osäkerheten (500 kr)", result["interpretation"])
        self.assertIn("går inte att skilja från sökningens slump", result["interpretation"])
        far = _clone(storage, current, "20250102T000000Z-pair", result={"solver": {
            "outcome": "feasible_not_proven", "objective_value_ore": cost + 18_300_000, "best_objective_bound_ore": cost + 13_300_000}})
        result = joint_api.compare_runs(storage, current, far, self.catalog)
        self.assertEqual((result["uncertainty_ore"], result["interpretable"]), (5_000_000, True))
        self.assertTrue(result["interpretation"].startswith("Kostnaden sjönk med 183 000 kr. Skillnaden är större än osäkerheten (50 000 kr) och kan därför tolkas."))

    def test_runs_on_different_data_or_exams_are_never_compared(self) -> None:
        self.enterContext(_crafted())
        workspace = Workspace(self)
        current = _run(workspace)
        storage = workspace.storage
        other_data = _clone(storage, current, "20250101T000000Z-pair", problem={"dataset_hash": "0" * 64})
        result = joint_api.compare_runs(storage, current, other_data, self.catalog)
        self.assertFalse(result["comparable"])
        self.assertIn("dataset_hash", result["reason"])
        self.assertTrue(all(item["delta"] is None for item in result["metrics"].values()))
        self.assertIsNone(result["uncertainty_ore"])
        self.assertIsNone(result["interpretable"])
        self.assertEqual(result["interpretation"], result["reason"])
        other_exams = _clone(storage, current, "20250102T000000Z-pair", problem={"demands": []})
        self.assertIn("olika uppsättningar tentor", joint_api.compare_runs(storage, current, other_exams, self.catalog)["reason"])
        previous = joint_api.compare_runs(storage, current, "previous", self.catalog)  # the closest older run is the exam-less clone
        self.assertEqual(previous["base"]["run_id"], "20250102T000000Z-pair")
        self.assertFalse(previous["comparable"])

    def test_unknown_or_malformed_runs_are_reported(self) -> None:
        workspace = Workspace(self)
        current = _run(workspace)
        with self.assertRaises(FileNotFoundError):
            joint_api.compare_runs(workspace.storage, "20250101T000000Z-nope", "previous", self.catalog)
        with self.assertRaises(FileNotFoundError):
            joint_api.compare_runs(workspace.storage, current, "20250101T000000Z-nope", self.catalog)
        for bad in ("../x", "a/b", ".."):
            with self.assertRaises(ValueError):
                joint_api.compare_runs(workspace.storage, current, bad, self.catalog)

    def test_the_wording_is_plain_and_always_says_that_the_amounts_are_model_cost(self) -> None:
        interpretable, text = interpret(-18_300_000, 5_000_000)
        self.assertTrue(interpretable)
        self.assertTrue(text.startswith("Kostnaden sjönk med 183 000 kr. Skillnaden är större än osäkerheten (50 000 kr) och kan därför tolkas."))
        self.assertIn("inte faktisk kostnad", text)
        self.assertEqual(interpret(1_000_000, 1_000_000)[0], False)
        self.assertIn("lika stor som", interpret(1_000_000, 1_000_000)[1])
        self.assertEqual(interpret(0, 0)[0], False)
        self.assertIn("oförändrad", interpret(0, 0)[1])
        self.assertIsNone(interpret(500, None)[0])
        self.assertIsNone(interpret(None, 0)[0])


class DayStartedTests(unittest.TestCase):
    def test_a_check_is_reported_as_started_before_it_is_reported_as_finished(self) -> None:
        for budget in (ExecutionBudget(4), ExecutionBudget(4, None, False)):
            with self.subTest(parallel=budget.parallel_day_checks):
                sink = ProgressSink()
                solve_joint_optimization(_two_day_problem("decomposed"), budget=budget, progress=sink)
                events = sink.events()
                started = [event for event in events if event["type"] == "day_started"]
                finished = [event for event in events if event["type"] == "day"]
                self.assertTrue(started)
                self.assertTrue(all(set(event) >= {"seq", "t", "type", "date", "kind"} for event in started))
                for event in finished:  # each finished check has an earlier start with the same day and kind
                    self.assertTrue(any(item["date"] == event["date"] and item["kind"] == event["kind"] and item["seq"] < event["seq"] for item in started), event)
                self.assertGreaterEqual(len(started), len(finished))
                if not budget.parallel_day_checks:  # one at a time: start, finish, start, finish
                    order = [event["type"] for event in events if event["type"] in {"day_started", "day"}]
                    self.assertEqual(order, ["day_started", "day"] * (len(order) // 2))


class RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace = Workspace(self)
        self.workspace, self.storage = workspace, workspace.storage
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
            with urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read() or b"{}")
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read() or b"{}")
        except OSError:
            return 0, {}

    def test_parameters_scenarios_runs_and_comparison_over_http(self) -> None:
        status, listing = self._request("GET", "/api/joint-runs/scenarios")
        self.assertEqual(status, 200)
        term = next(row for row in listing["scenarios"] if row["id"] == "joint_underlay_period")
        self.assertEqual((term["origin"], term["subset"]["selection"], term["subset"]["exam_count"]), ("bundled", "rule", 2))

        status, payload = self._request("GET", "/api/joint-runs/parameters?scenario=joint_underlay_period")
        self.assertEqual((status, payload["catalog_version"], payload["scenario_id"], len(payload["parameters"])), (200, "2.3.0", "joint_underlay_period", 55))
        self.assertEqual(self._request("GET", "/api/joint-runs/parameters?scenario=finns-inte")[0], 404)
        self.assertEqual(self._request("GET", "/api/joint-runs/parameters?scenario=../x")[0], 422)
        self.assertEqual(self._request("GET", "/api/joint-runs/parameters")[0], 422)

        body = {"name": "snabb-termin", "description": "Kort tid", "base": "joint_underlay_period",
                "parameters": {"solver.time_limit_seconds": 20.0, "solver.workers": 2, "cost.staff_annual_ore": 4000}}
        status, row = self._request("POST", "/api/joint-runs/scenarios", body)
        self.assertEqual((status, row["id"], row["origin"], row["problem_id"]), (200, "snabb-termin", "user", "snabb-termin"))
        self.assertEqual(self._request("POST", "/api/joint-runs/scenarios", body)[0], 409)
        self.assertEqual(self._request("POST", "/api/joint-runs/scenarios", {**body, "name": "joint_underlay_period"})[0], 409)
        self.assertEqual(self._request("POST", "/api/joint-runs/scenarios", {**body, "name": "annat", "base": "finns-inte"})[0], 404)
        self.assertEqual(self._request("POST", "/api/joint-runs/scenarios", {**body, "name": "Fel Namn"})[0], 422)
        status, error = self._request("POST", "/api/joint-runs/scenarios", {**body, "name": "annat", "parameters": {"rules.student_conflicts": True}})
        self.assertEqual(status, 422)
        self.assertEqual([item["id"] for item in error["detail"]["errors"]], ["rules.student_conflicts"])
        self.assertTrue(error["detail"]["errors"][0]["message"])

        status, error = self._request("POST", "/api/joint-runs", {"scenario": "snabb-termin", "parameters": {"window.earlier_days": -1, "q": 1}})
        self.assertEqual(status, 422)
        self.assertEqual(sorted(item["id"] for item in error["detail"]["errors"]), ["q", "window.earlier_days"])
        self.assertEqual(self._request("POST", "/api/joint-runs", {"scenario": "finns-inte", "parameters": {}})[0], 404)
        self.assertIsInstance(self._request("POST", "/api/joint-runs", {"scenario": "reference"})[1]["detail"], str)  # other errors keep their form

        status, job = self._request("POST", "/api/joint-runs", {"scenario": "snabb-termin", "warm_start": "none", "parameters": {"window.later_days": 2}})
        self.assertEqual(status, 200)
        for _ in range(600):
            status, events = self._request("GET", f"/api/joint-runs/{job['job_id']}/events?after=0")
            if events["status"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(events["status"], "completed", events)
        run_id = events["run_id"]
        self.assertTrue(any(event["type"] == "day_started" for event in events["events"]))
        status, summary = self._request("GET", f"/api/joint-runs/{run_id}/summary")
        self.assertEqual((status, summary["scenario_id"], summary["problem_id"], summary["has_verified_solution"]), (200, "snabb-termin", "snabb-termin", True))
        self.assertGreaterEqual(len(summary["parameters_changed_from_default"]), 1)
        status, comparison = self._request("GET", f"/api/joint-runs/{run_id}/compare")
        self.assertEqual((status, comparison["base"], comparison["comparable"], comparison["reason"]), (200, None, False, NO_PREVIOUS))
        self.assertEqual(self._request("GET", f"/api/joint-runs/{run_id}/compare?base=20250101T000000Z-x")[0], 404)
        self.assertEqual(self._request("GET", f"/api/joint-runs/{run_id}/compare?base=../x")[0], 422)
        self.assertEqual(self._request("GET", "/api/joint-runs/20250101T000000Z-x/compare")[0], 404)
        self.assertTrue((self.storage.runs_dir / run_id / "joint_scenario.toml").is_file())
        used = tomllib.loads((self.storage.runs_dir / run_id / "joint_scenario.toml").read_text(encoding="utf-8"))
        self.assertEqual(used["parameters"]["window.later_days"], 2)
        self.assertEqual(used["parameters"]["cost.staff_annual_ore"], 4000)  # from the saved scenario
        self.assertEqual(used["subset"]["selection"], "all_ready")


if __name__ == "__main__":
    unittest.main()
