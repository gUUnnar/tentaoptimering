"""The choices behind `GET /api/joint-runs/options` and the check of `rooms.selection`.

Synthetic data (the two-exam set of `test_joint_validation_run`, widened here with more rooms and exam types) gives
exact expected lists; a test against the real prepared data compares the counts with an independent pandas count.
"""

from __future__ import annotations

import json
from pathlib import Path
import socket
import sys
import threading
import time
import tomllib
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_api import Workspace, _wait_for_end  # noqa: E402
from test_joint_validation_run import CATALOG, PROCESSED, REPO_ROOT  # noqa: E402
from tentaoptimering import joint_api  # noqa: E402
from tentaoptimering.api import create_app  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest, ParameterValidationError, ScenarioCreate  # noqa: E402
from tentaoptimering.joint_inputs import build_real_subset_problem  # noqa: E402
from tentaoptimering.joint_options import digital_level, options_payload  # noqa: E402
from tentaoptimering.joint_scenarios import read_scenario  # noqa: E402

READY = "ready_provisional_ladok_demand"
UNDERLAY = REPO_ROOT / "config" / "scenarios" / "joint_underlay_period.toml"

# event id -> (observed exam types, city, demand status); X and Y are the exams of the "case" scenario
EVENTS = {
    "X": ("Ordinarie tenta", "Uppsala", READY),
    "Y": ("Omtenta", "Uppsala", READY),
    "Z": ("Ordinarie tenta", "Uppsala", READY),
    "W": ("Hemtenta", "Uppsala", READY),
    "T": ("Hybridtenta", "Uppsala", READY),
    "M": ("Ordinarie tenta | Omtenta", "Uppsala", READY),
    "V": ("Dugga", "Visby", READY),
    "N": ("Dugga", "Uppsala", "not_ready"),
}
# room id -> (address, city, seats, digital status, eligible)
ROOMS = {
    "uu-r1": ("Adress 1", "Uppsala", 60, "all_places_support_e_exam", True),
    "uu-big": ("Adress 1", "Uppsala", 120, "supports_e_exam_some_places", True),
    "uu-r2": ("Adress 2", "Uppsala", 60, "not_inferred_from_exam_booking", True),
    "uu-r3": ("Adress 3", "Uppsala", 30, "no_e_exam_support", True),
    "uu-off": ("Adress 4", "Uppsala", 200, "all_places_support_e_exam", False),
    "vi-r1": ("Campus Gotland", "Visby", 80, "all_places_support_e_exam", True),
}


def _widen(path: Path) -> None:
    """Replace the demands and rooms of the pair data set by the wider set above (same columns)."""
    demands = pd.read_csv(path / "optimization_demands.csv", encoding="utf-8-sig")
    template = demands.iloc[0].to_dict()
    rows = [{**template, "exam_event_id": event, "activity_id": f"act-{event}", "course_code": f"C-{event}",
             "observed_exam_types": types, "observed_cities": city, "demand_input_status": status}
            for event, (types, city, status) in EVENTS.items()]
    pd.DataFrame(rows).to_csv(path / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    rooms = pd.read_csv(path / "optimization_rooms.csv", encoding="utf-8-sig")
    base = rooms.iloc[0].to_dict()
    pd.DataFrame([
        {**base, "room_id": room, "reference_address": address, "reference_city": city, "capacity_seats": seats,
         "digital_capability_status": status, "eligible_for_exploratory_capacity_poc": eligible}
        for room, (address, city, seats, status, eligible) in ROOMS.items()
    ]).to_csv(path / "optimization_rooms.csv", index=False, encoding="utf-8-sig")


class OptionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Workspace(self)
        self.storage = self.workspace.storage
        _widen(self.storage.processed_dir)

    def _options(self, scenario: str = "case") -> dict:
        return joint_api.options_payload_for(self.storage, scenario, self.workspace.scenarios)

    def test_rooms_are_those_the_engine_considers_sorted_by_building_then_capacity(self) -> None:
        payload = self._options()
        self.assertEqual((payload["scenario_id"], payload["plan_area"], payload["data_available"]), ("case", "Uppsala", True))
        self.assertEqual([item["room_id"] for item in payload["rooms"]], ["uu-big", "uu-r1", "uu-r2", "uu-r3"])  # no Visby, no ineligible
        big = payload["rooms"][0]
        self.assertEqual(big, {"room_id": "uu-big", "label": "Adress 1 – uu-big (120 platser)", "building_id": "adress-1",
                               "address": "Adress 1", "capacity": 120, "digital": "partial"})
        self.assertEqual([item["digital"] for item in payload["rooms"]], ["partial", "all", "unknown", "none"])
        problem = build_real_subset_problem(self.workspace.scenarios / "case.toml", self.storage.processed_dir, CATALOG)
        self.assertEqual({item["room_id"] for item in payload["rooms"]}, {room.room_id for room in problem.rooms})
        self.assertEqual({item["building_id"] for item in payload["rooms"]}, {room.building_id for room in problem.rooms})

    def test_exam_types_count_the_exams_of_the_scenario_and_match_by_lower_case_value(self) -> None:
        self.assertEqual(self._options()["exam_types"], [
            {"value": "omtenta", "label": "Omtenta", "count": 1}, {"value": "ordinarie tenta", "label": "Ordinarie tenta", "count": 1}])
        rule = self.workspace.scenarios / "alla.toml"  # all ready exams in Uppsala: a rule instead of a list
        text = (self.workspace.scenarios / "case.toml").read_text(encoding="utf-8")
        rule.write_text(text.replace('exam_event_ids = ["X", "Y"]', 'selection = "all_ready"'), encoding="utf-8")
        types = self._options("alla")["exam_types"]
        self.assertEqual({item["value"]: item["count"] for item in types},
                         {"ordinarie tenta": 3, "omtenta": 2, "hemtenta": 1, "hybridtenta": 1})  # M counts once per type; V, N excluded
        self.assertEqual([item["count"] for item in types], sorted((item["count"] for item in types), reverse=True))
        self.assertEqual({item["label"] for item in types}, {"Ordinarie tenta", "Omtenta", "Hemtenta", "Hybridtenta"})
        for item in types:  # `value` is usable as a movable-type part: it matches the type text as the engine reads it
            self.assertEqual(item["value"], item["label"].lower())

    def test_without_prepared_data_the_lists_are_empty_and_nothing_fails(self) -> None:
        for name in ("optimization_demands.csv", "optimization_rooms.csv"):
            (self.storage.processed_dir / name).unlink()
        self.assertEqual(self._options(), {"scenario_id": "case", "data_available": False, "rooms": [], "exam_types": [], "plan_area": "Uppsala"})
        (self.storage.processed_dir / "optimization_demands.csv").write_text("not,a,demand\n", encoding="utf-8")
        self.assertFalse(self._options()["data_available"])  # one file is not enough

    def test_a_scenario_whose_events_are_missing_still_lists_rooms_and_no_types(self) -> None:
        text = (self.workspace.scenarios / "case.toml").read_text(encoding="utf-8").replace('["X", "Y"]', '["X", "NEJ"]')
        (self.workspace.scenarios / "trasig.toml").write_text(text, encoding="utf-8")
        payload = self._options("trasig")
        self.assertEqual((len(payload["rooms"]), payload["exam_types"], payload["data_available"]), (4, [], True))

    def test_scenario_ids_are_validated_and_unknown_scenarios_refused(self) -> None:
        for bad in ("../case", "Case", "", "case.toml", "a" * 100):
            with self.subTest(scenario=bad), self.assertRaises(ValueError):
                joint_api.options_payload_for(self.storage, bad, self.workspace.scenarios)
        with self.assertRaises(FileNotFoundError):
            joint_api.options_payload_for(self.storage, "saknas", self.workspace.scenarios)

    def test_digital_levels(self) -> None:
        cases = {"all_places_support_e_exam": "all", "supports_e_exam_some_places": "partial", "no_e_exam_support": "none",
                 "not_inferred_from_exam_booking": "unknown", "": "unknown"}
        self.assertEqual({status: digital_level(status) for status in cases}, cases)

    def test_options_do_not_change_the_prepared_data(self) -> None:
        before = {path.name: path.read_bytes() for path in self.storage.processed_dir.glob("*.csv")}
        self._options()
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.storage.processed_dir.glob("*.csv")})


class RoomSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Workspace(self)
        self.storage = self.workspace.storage
        _widen(self.storage.processed_dir)
        self.scenario = self.workspace.scenarios / "case.toml"

    def _problem_with(self, selection: list[str]):
        text = self.scenario.read_text(encoding="utf-8") + f"\n\"rooms.selection\" = {json.dumps(selection)}\n"
        path = self.workspace.scenarios / "val.toml"
        path.write_text(text, encoding="utf-8")
        return build_real_subset_problem(path, self.storage.processed_dir, CATALOG)

    def test_valid_selections_behave_as_before(self) -> None:
        everything = build_real_subset_problem(self.scenario, self.storage.processed_dir, CATALOG)
        self.assertEqual([room.room_id for room in everything.rooms], ["uu-r1", "uu-big", "uu-r2", "uu-r3"])  # an empty selection means all
        self.assertEqual([room.room_id for room in self._problem_with(["uu-r2", "uu-r1"]).rooms], ["uu-r1", "uu-r2"])  # file order kept
        listed = self._problem_with(["uu-r1", "uu-big", "uu-r2", "uu-r3"])
        self.assertEqual(listed.rooms, everything.rooms)
        one = self._problem_with(["uu-r1"]).rooms
        self.assertEqual((len(one), one[0].capacity), (1, 60))
        self.assertEqual(len(self._problem_with(["uu-r1", "uu-r1"]).rooms), 1)  # a repeated id is not a second room

    def test_an_unknown_room_is_an_error_with_a_swedish_message_not_silently_ignored(self) -> None:
        for selection in (["uu-finns-inte"], ["uu-r1", "uu-finns-inte"], ["vi-r1"], ["uu-off"]):  # unknown, mixed, other area, ineligible
            with self.subTest(selection=selection), self.assertRaises(ValueError) as caught:
                self._problem_with(selection)
            self.assertIn("Okänd sal: ", str(caught.exception))
            self.assertIn("Uppsala", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self._problem_with(["uu-a", "uu-b"])
        self.assertIn("Okänd sal: uu-a, uu-b.", str(caught.exception))
        self.assertIn("Urvalet lämnar inga salar", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self._problem_with(["uu-r1", "uu-nej"])
        self.assertNotIn("lämnar inga salar", str(caught.exception))  # some rooms would remain: only the unknown id is named

    def test_the_run_request_with_an_unknown_room_is_refused_before_anything_starts(self) -> None:
        request = JointRunRequest(scenario="case", warm_start="none", parameters={"rooms.selection": ["uu-r1", "uu-finns-inte"]})
        with self.assertRaises(ParameterValidationError) as caught:
            joint_api.start_joint_run(self.workspace.jobs, self.storage, request, self.workspace.scenarios)
        self.assertEqual(caught.exception.errors, [{"id": "rooms.selection", "message": caught.exception.errors[0]["message"]}])
        self.assertTrue(caught.exception.errors[0]["message"].startswith("Okänd sal: uu-finns-inte"))
        self.assertEqual(list(self.storage.snapshots_dir.glob("*.toml")), [])
        self.assertFalse(self.workspace.jobs.has_active_job())

    def test_a_known_selection_starts_a_run_and_a_type_error_comes_first(self) -> None:
        job = self.workspace.start(parameters={"rooms.selection": ["uu-r1", "uu-big"]})
        self.assertEqual(_wait_for_end(self.workspace.jobs, job["job_id"])["status"], "completed")
        with self.assertRaises(ParameterValidationError) as caught:
            joint_api.start_joint_run(self.workspace.jobs, self.storage,
                                      JointRunRequest(scenario="case", parameters={"rooms.selection": "uu-r1"}), self.workspace.scenarios)
        self.assertIn("lista", caught.exception.errors[0]["message"])  # a text instead of a list: the type error, not "Okänd sal"

    def test_saving_a_scenario_with_an_unknown_room_is_refused_and_a_known_one_saved(self) -> None:
        bad = ScenarioCreate(name="eget", base="case", parameters={"rooms.selection": ["uu-nej"]})
        with self.assertRaises(ParameterValidationError) as caught:
            joint_api.create_scenario(self.storage, bad, self.workspace.scenarios, CATALOG)
        self.assertEqual([item["id"] for item in caught.exception.errors], ["rooms.selection"])
        self.assertNotIn("eget", {row["id"] for row in joint_api.list_scenarios(self.workspace.scenarios, self.storage)})
        self.assertFalse((self.storage.root / "joint_scenarios" / "eget.toml").exists())
        good = ScenarioCreate(name="eget", base="case", parameters={"rooms.selection": ["uu-r1"], "flex.movable_types": ["omtenta"]})
        row = joint_api.create_scenario(self.storage, good, self.workspace.scenarios, CATALOG)
        self.assertEqual(row["id"], "eget")
        saved = tomllib.loads((self.storage.root / "joint_scenarios" / "eget.toml").read_text(encoding="utf-8"))
        self.assertEqual(saved["parameters"]["rooms.selection"], ["uu-r1"])
        self.assertEqual(read_scenario(self.storage.root / "joint_scenarios" / "eget.toml")["scenario"]["id"], "eget")

    def test_without_prepared_data_the_selection_cannot_be_checked_and_is_accepted(self) -> None:
        (self.storage.processed_dir / "optimization_rooms.csv").unlink()
        request = ScenarioCreate(name="utan-data", base="case", parameters={"rooms.selection": ["uu-nej"]})
        self.assertEqual(joint_api.create_scenario(self.storage, request, self.workspace.scenarios, CATALOG)["id"], "utan-data")


class RouteTests(unittest.TestCase):
    """The routes over HTTP, on the bundled scenarios and the widened synthetic data."""

    def setUp(self) -> None:
        workspace = Workspace(self)
        self.storage = workspace.storage
        _widen(self.storage.processed_dir)
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

    def test_options_route(self) -> None:
        status, payload = self._request("GET", "/api/joint-runs/options?scenario=joint_underlay_period")
        self.assertEqual(status, 200)
        self.assertEqual(set(payload), {"scenario_id", "data_available", "rooms", "exam_types", "plan_area"})
        self.assertEqual((payload["scenario_id"], payload["plan_area"], len(payload["rooms"])), ("joint_underlay_period", "Uppsala", 4))
        self.assertEqual({item["value"]: item["count"] for item in payload["exam_types"]},
                         {"ordinarie tenta": 3, "omtenta": 2, "hemtenta": 1, "hybridtenta": 1})
        self.assertEqual(set(payload["rooms"][0]), {"room_id", "label", "building_id", "address", "capacity", "digital"})
        self.assertEqual(self._request("GET", "/api/joint-runs/options?scenario=finns-inte")[0], 404)
        self.assertEqual(self._request("GET", "/api/joint-runs/options?scenario=../x")[0], 422)
        self.assertEqual(self._request("GET", "/api/joint-runs/options?scenario=Stor")[0], 422)
        self.assertEqual(self._request("GET", "/api/joint-runs/options")[0], 422)
        (self.storage.processed_dir / "optimization_rooms.csv").unlink()
        status, payload = self._request("GET", "/api/joint-runs/options?scenario=joint_underlay_period")
        self.assertEqual((status, payload["data_available"], payload["rooms"], payload["exam_types"]), (200, False, [], []))

    def test_unknown_room_gives_422_with_the_error_in_detail_on_both_routes(self) -> None:
        run = {"scenario": "joint_underlay_period", "warm_start": "none", "parameters": {"rooms.selection": ["uu-r1", "uu-finns-inte"]}}
        status, error = self._request("POST", "/api/joint-runs", run)
        self.assertEqual(status, 422)
        self.assertEqual([item["id"] for item in error["detail"]["errors"]], ["rooms.selection"])
        self.assertTrue(error["detail"]["errors"][0]["message"].startswith("Okänd sal: uu-finns-inte"))
        save = {"name": "med-sal", "base": "joint_underlay_period", "parameters": {"rooms.selection": ["uu-finns-inte"]}}
        status, error = self._request("POST", "/api/joint-runs/scenarios", save)
        self.assertEqual((status, error["detail"]["errors"][0]["id"]), (422, "rooms.selection"))
        status, row = self._request("POST", "/api/joint-runs/scenarios", {**save, "parameters": {"rooms.selection": ["uu-r1"]}})
        self.assertEqual((status, row["id"]), (200, "med-sal"))
        status, payload = self._request("GET", "/api/joint-runs/options?scenario=med-sal")  # a saved scenario has options too
        self.assertEqual((status, payload["scenario_id"], len(payload["rooms"])), (200, "med-sal", 4))  # all rooms: the choice list is not narrowed


@unittest.skipUnless((PROCESSED / "optimization_demands.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class RealDataTests(unittest.TestCase):
    """The counts of the whole-term scenario against an independent pandas count of the prepared data."""

    def test_counts_for_the_underlay_period_match_pandas(self) -> None:
        payload = options_payload(PROCESSED, "joint_underlay_period", read_scenario(UNDERLAY))
        demands = pd.read_csv(PROCESSED / "optimization_demands.csv", encoding="utf-8-sig")
        days = demands["scheduled_date"].astype(str)
        ready = demands[(demands["demand_input_status"] == READY) & (demands["observed_cities"] == "Uppsala")
                        & (days >= "2026-01-12") & (days <= "2026-03-31")]
        self.assertTrue(payload["data_available"])
        self.assertEqual(ready["exam_event_id"].nunique(), 1172)
        expected = ready.groupby(ready["observed_exam_types"].str.lower())["exam_event_id"].nunique().to_dict()
        self.assertEqual({item["value"]: item["count"] for item in payload["exam_types"]}, expected)
        self.assertTrue({"ordinarie tenta", "omtenta", "dugga", "hybridtenta", "hemtenta"} <= set(expected))
        self.assertEqual(sum(item["count"] for item in payload["exam_types"]), 1172)  # no exam has two types in this data
        rooms = pd.read_csv(PROCESSED / "optimization_rooms.csv", encoding="utf-8-sig")
        eligible = rooms[rooms["eligible_for_exploratory_capacity_poc"].astype(bool) & (rooms["reference_city"] == "Uppsala")]
        self.assertEqual({item["room_id"] for item in payload["rooms"]}, set(eligible["room_id"]))
        self.assertEqual({item["room_id"]: item["capacity"] for item in payload["rooms"]}, dict(zip(eligible["room_id"], eligible["capacity_seats"])))
        keys = [(item["building_id"], -item["capacity"]) for item in payload["rooms"]]
        self.assertEqual(keys, sorted(keys))
        problem = build_real_subset_problem(UNDERLAY, PROCESSED, CATALOG)
        self.assertEqual({room.room_id for room in problem.rooms}, set(eligible["room_id"]))


if __name__ == "__main__":
    unittest.main()
