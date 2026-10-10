from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import pandas as pd
import uvicorn

from tentaoptimering.api import create_app
from tentaoptimering.app_storage import AppStorage


class ApiWorkflowTest(unittest.TestCase):
    """Exercise the local HTTP workflow, worker, term engine, and validation."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = AppStorage(Path(self.temporary.name))
        _write_processed_inputs(self.storage.processed_dir)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(create_app(self.storage.root), host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        _wait_for(lambda: self._request("GET", "/api/health")[0] == 200)

    def tearDown(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def _request(self, method: str, path: str, payload: object | None = None) -> tuple[int, dict[str, object]]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, _payload(response.read())
        except HTTPError as error:
            with error:
                return error.code, _payload(error.read())

    def _create_and_update(self, scenario_id: str, room_cost: int) -> dict[str, object]:
        status, created = self._request("POST", "/api/scenarios", {"scenario_id": scenario_id})
        self.assertEqual(status, 200)
        content = created["content"]
        self.assertIsInstance(content, dict)
        content = deepcopy(content)
        content["costs"]["annual_room_cost_ore_per_seat"] = room_cost
        status, saved = self._request("PUT", f"/api/scenarios/{scenario_id}", {"content": content})
        self.assertEqual(status, 200)
        return saved

    def _run(self, scenario_id: str) -> str:
        status, job = self._request("POST", f"/api/simulations?scenario_id={scenario_id}")
        self.assertEqual(status, 200)
        job_id = str(job["job_id"])
        for _ in range(100):
            status, current = self._request("GET", f"/api/jobs/{job_id}")
            self.assertEqual(status, 200)
            if current["status"] == "completed":
                return str(current["result"]["run_id"])
            self.assertNotEqual(current["status"], "failed", current.get("error"))
            time.sleep(0.02)
        self.fail("Terminskörningen slutfördes inte i testets tidsgräns.")

    def test_scenario_to_validated_run_and_comparison_workflow(self) -> None:
        status, parameters = self._request("GET", "/api/parameters")
        self.assertEqual(status, 200)
        self.assertTrue(parameters["parameters"])
        self.assertTrue(any(item["engine_binding"] == "staffing.shift" for item in parameters["term_parameter_bindings"]))
        first = self._create_and_update("workflow-one", 100000)
        content = deepcopy(first["content"])
        del content["calendar"]["passes"]
        status, _ = self._request("PUT", "/api/scenarios/workflow-one", {"content": content})
        self.assertEqual(status, 422)
        status, preserved = self._request("GET", "/api/scenarios/workflow-one")
        self.assertEqual(status, 200)
        self.assertEqual(preserved["content"]["costs"]["annual_room_cost_ore_per_seat"], 100000)
        first_run = self._run("workflow-one")
        self._create_and_update("workflow-two", 200000)
        second_run = self._run("workflow-two")
        status, validation = self._request("GET", f"/api/runs/{first_run}/validation")
        self.assertEqual(status, 200)
        self.assertIn("technical_placement_completeness", validation)
        self.assertIn("business_feasibility", validation)
        status, comparison = self._request("POST", "/api/runs/compare", [first_run, second_run])
        self.assertEqual(status, 200)
        self.assertEqual(len(comparison["runs"]), 2)
        self.assertTrue(any(item["parameter"] == "costs.annual_room_cost_ore_per_seat" for item in comparison["parameter_changes"]))
        for unsafe in ("..%2Foutside", "..%5Coutside"):
            status, _ = self._request("GET", f"/api/runs/{unsafe}")
            self.assertIn(status, (404, 422))

    def test_source_directory_chooser_returns_selection_without_saving(self) -> None:
        selected = str(self.storage.root)
        with patch("tentaoptimering.api.choose_directory", return_value=selected) as picker:
            status, response = self._request("POST", "/api/settings/choose-source-directory")
        self.assertEqual(status, 200)
        self.assertEqual(response["source_dir"], selected)
        self.assertIsNone(self.storage.settings()["source_dir"])
        picker.assert_called_once_with(None)


def _wait_for(predicate: object) -> None:
    for _ in range(100):
        if callable(predicate) and predicate():
            return
        time.sleep(0.02)
    raise AssertionError("HTTP-servern startade inte.")


def _payload(body: bytes) -> dict[str, object]:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body.decode("utf-8", errors="replace")}


def _write_processed_inputs(path: Path) -> None:
    pd.DataFrame([{
        "demand_id": "demand-1", "activity_id": "activity-1", "exam_event_id": "event-1",
        "course_code": "COURSE", "scheduled_time": "08:00-10:00", "demand_value": 12,
        "demand_measure_source_field": "registered_count",
        "demand_input_status": "ready_provisional_ladok_demand", "observed_cities": "Uppsala",
    }]).to_csv(path / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{
        "room_id": "room-1", "capacity_seats": 20, "reference_city": "Uppsala",
        "eligible_for_exploratory_capacity_poc": True,
    }]).to_csv(path / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"activity_id": "activity-1", "scope_status": "included"},
        {"activity_id": "activity-2", "scope_status": "unresolved"},
    ]).to_csv(path / "demand_scope.csv", index=False, encoding="utf-8-sig")
