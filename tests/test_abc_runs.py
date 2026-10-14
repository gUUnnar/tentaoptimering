"""B and C runs: they are saved with their name, kind and parameters, are never overwritten, can be repeated or used as a base, and compare with A.

One engine runs both. B is the base scenario run exactly as defined; C is any other parameter set. A saved run keeps what it was
made from (scenario copy, input, result, meta); the next run, with other values, leaves it untouched. A comparison says what it
cannot compare (another underlay, a run without a solution, rooms the booking never named) and never fills the gap.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import socket  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from urllib.error import HTTPError  # noqa: E402
from urllib.parse import urlencode  # noqa: E402
from urllib.request import urlopen  # noqa: E402

import uvicorn  # noqa: E402
from test_joint_api import Workspace, _wait_for_end  # noqa: E402
from wish_cases import wish_row, write_wishes  # noqa: E402
from tentaoptimering import abc_compare, joint_api  # noqa: E402
from tentaoptimering.api import create_app  # noqa: E402
from tentaoptimering.joint_api import JointRunRequest  # noqa: E402
from tentaoptimering.joint_scenarios import scenario_id_for_run  # noqa: E402
from tentaoptimering.run_meta import read_meta  # noqa: E402

ARTIFACTS = ("joint_input.json", "joint_result.json", "joint_manifest.json", "joint_scenario.toml", "joint_run.json")


def _digest(directory: Path) -> dict[str, str]:
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in ARTIFACTS}


class Http:
    """The app served on a free local port, called with plain HTTP (the same way the other route tests do it)."""

    def __init__(self, test: unittest.TestCase, root: Path) -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(create_app(root), host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        end = time.perf_counter() + 10
        while time.perf_counter() < end and self.get("/api/health")[0] != 200:
            time.sleep(0.05)
        test.addCleanup(self.stop)

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)

    def get(self, path: str, **params: object) -> tuple[int, dict]:
        url = f"http://127.0.0.1:{self.port}{path}" + (f"?{urlencode(params)}" if params else "")
        try:
            with urlopen(url, timeout=30) as response:
                return response.status, json.loads(response.read() or b"{}")
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read() or b"{}")
        except OSError:
            return 0, {}


class RunWorkspace(Workspace):
    def __init__(self, test: unittest.TestCase) -> None:
        super().__init__(test)
        shutil.copy(self.scenarios / "case.toml", self.scenarios / "joint_base.toml")  # the base scenario under its real id
        write_wishes(self.storage.processed_dir, [wish_row("X", "2026-01-12", "2026-01-13", booked="2026-01-12"), wish_row("Y", "2026-01-12", booked="2026-01-12")])
        self.write_bookings()

    def write_bookings(self) -> None:
        folder = self.storage.processed_dir
        columns = ["placement_id", "exam_order_id", "course_codes", "course_name", "exam_type", "digital_exam", "scheduled_date", "scheduled_time",
                   "address", "room", "location_key", "booked_places", "status"]
        rows = [("p1", "ox", "C-X", "X", "Ordinarie tenta", "Nej", "2026-01-12", "08:00-12:00", "Adress 1", "Sal 1", "adress-1|sal-1", "50", "Klar"),
                ("p2", "oy", "C-Y", "Y", "Ordinarie tenta", "Nej", "2026-01-12", "08:00-12:00", "Adress 2", "Sal 1", "adress-2|sal-1", "50", "Klar")]
        pd.DataFrame(rows, columns=columns).to_csv(folder / "bookings.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame([("uu-r1", "adress-1|sal-1", "Adress 1", "Sal 1", "60"), ("uu-r2", "adress-2|sal-1", "Adress 2", "Sal 1", "60")],
                     columns=["room_id", "location_key", "reference_address", "reference_room_name", "capacity_seats"]).to_csv(folder / "room_inventory.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(columns=["placement_id", "activity_id", "candidate_status"]).to_csv(folder / "candidate_linkage.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame({"start_date": ["2026-01-01"]}).to_csv(folder / "ladok_activities.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame([("X", "ox", "2026-01-12", "08:00-12:00", "Klar"), ("Y", "oy", "2026-01-12", "08:00-12:00", "Klar")],
                     columns=["exam_event_id", "exam_order_id", "scheduled_date", "scheduled_time", "booking_statuses"]).to_csv(folder / "exam_events.csv", index=False, encoding="utf-8-sig")

    def run(self, scenario: str = "case", **fields) -> str:
        request = JointRunRequest(scenario=scenario, **{"warm_start": "none", "threads": 2, "parallel_day_checks": False, **fields})
        job = joint_api.start_joint_run(self.jobs, self.storage, request, self.scenarios)
        end = _wait_for_end(self.jobs, job["job_id"])
        assert end["status"] == "completed", end
        return end["run_id"]

    def directory(self, run_id: str) -> Path:
        return self.storage.runs_dir / run_id


class RunRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = RunWorkspace(self)

    def test_the_base_scenario_unchanged_is_B_and_anything_else_is_C(self) -> None:
        base = self.workspace.run("joint_base")
        meta = read_meta(self.workspace.directory(base))
        self.assertEqual((meta["kind"], meta["base_run_id"], meta["changes_from_base"]), ("B", None, {}))
        self.assertTrue(meta["name"].startswith("B – Grundoptimering"))
        other = self.workspace.run("case")
        self.assertEqual(read_meta(self.workspace.directory(other))["kind"], "C")  # not the base scenario
        changed = self.workspace.run("joint_base", parameters={"cost.room_annual_per_seat_ore": 777})
        self.assertEqual(read_meta(self.workspace.directory(changed))["kind"], "C")

    def test_a_run_has_the_name_it_was_given_and_says_which_underlay_and_model_it_used(self) -> None:
        run_id = self.workspace.run(name="  Min   körning med  dyrare salar ", parameters={"cost.room_annual_per_seat_ore": 777})
        meta = read_meta(self.workspace.directory(run_id))
        self.assertEqual(meta["name"], "Min körning med dyrare salar")
        self.assertEqual(meta["dataset_hash"], json.loads((self.workspace.directory(run_id) / "joint_input.json").read_text(encoding="utf-8"))["dataset_hash"])
        self.assertEqual(set(meta["model"]), {"engine", "input_schema", "result_schema", "catalog_version", "catalog_sha256"})
        self.assertTrue(meta["created_at"].endswith("Z"))

    def test_without_a_name_the_run_gets_one_that_says_what_was_changed(self) -> None:
        run_id = self.workspace.run(parameters={"cost.room_annual_per_seat_ore": 777})
        self.assertRegex(read_meta(self.workspace.directory(run_id))["name"], r"^C – .*\d\d:\d\d$")

    def test_C_uses_exactly_the_values_the_user_chose_and_nothing_else_changes(self) -> None:
        reference = self.workspace.run()
        run_id = self.workspace.run(parameters={"cost.room_annual_per_seat_ore": 777, "window.later_days": 1})
        params = lambda rid: {item["parameter_id"]: item["value"] for item in json.loads((self.workspace.directory(rid) / "joint_input.json").read_text(encoding="utf-8"))["parameters"]}
        before, after = params(reference), params(run_id)
        self.assertEqual({key for key in before if before[key] != after[key]}, {"cost.room_annual_per_seat_ore", "window.later_days"})
        self.assertEqual((after["cost.room_annual_per_seat_ore"], after["window.later_days"]), (777, 1))
        self.assertEqual(read_meta(self.workspace.directory(run_id))["changes_from_base"], {"cost.room_annual_per_seat_ore": 777, "window.later_days": 1})

    def test_a_saved_run_is_not_changed_by_the_next_run(self) -> None:
        first = self.workspace.run(name="Första")
        saved = _digest(self.workspace.directory(first))
        second = self.workspace.run(name="Andra", parameters={"cost.room_annual_per_seat_ore": 5})
        self.assertNotEqual(first, second)
        self.assertEqual(_digest(self.workspace.directory(first)), saved)
        self.assertEqual({row["run_id"]: row["name"] for row in abc_compare.list_runs(self.workspace.storage)}, {first: "Första", second: "Andra"})

    def test_the_scenario_file_is_never_changed_by_a_run_with_other_values(self) -> None:
        source = (self.workspace.scenarios / "joint_base.toml").read_bytes()
        self.workspace.run("joint_base", parameters={"cost.room_annual_per_seat_ore": 777})
        self.assertEqual((self.workspace.scenarios / "joint_base.toml").read_bytes(), source)

    def test_a_run_can_be_repeated_or_used_as_the_base_of_the_next(self) -> None:
        first = self.workspace.run(name="Grund", parameters={"cost.room_annual_per_seat_ore": 777})
        saved = _digest(self.workspace.directory(first))
        again = self.workspace.run(scenario_id_for_run(first), name="Igen")
        meta = read_meta(self.workspace.directory(again))
        self.assertEqual((meta["base_run_id"], meta["kind"], meta["changes_from_base"]), (first, "C", {}))
        compared = abc_compare.compare(self.workspace.storage, first, again)
        self.assertEqual(compared["parameter_changes"], [])  # same values: nothing differs
        self.assertEqual(compared["left"]["scope"]["exam_count"], compared["right"]["scope"]["exam_count"])
        derived = self.workspace.run(scenario_id_for_run(first), name="Utgår från Grund", parameters={"window.later_days": 1})
        changes = abc_compare.compare(self.workspace.storage, first, derived)["parameter_changes"]
        self.assertEqual([(item["id"], item["old"], item["new"]) for item in changes], [("window.later_days", 0, 1)])
        self.assertEqual(_digest(self.workspace.directory(first)), saved)

    def test_repeating_the_base_run_is_still_B(self) -> None:
        base = self.workspace.run("joint_base")
        again = self.workspace.run(scenario_id_for_run(base))
        self.assertEqual(read_meta(self.workspace.directory(again))["kind"], "B")

    def test_an_old_run_without_meta_is_listed_and_not_called_B(self) -> None:
        run_id = self.workspace.run()
        (self.workspace.directory(run_id) / "joint_run.json").unlink()
        row = abc_compare.list_runs(self.workspace.storage)[0]
        self.assertEqual((row["kind"], row["named"]), ("C", False))


class CompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = RunWorkspace(self)
        self.storage = self.workspace.storage

    def test_A_against_a_run_covers_the_same_exams_and_separates_the_kinds_of_cost(self) -> None:
        run_id = self.workspace.run("joint_base")
        result = abc_compare.compare(self.storage, "actual", run_id)
        self.assertTrue(result["comparable"])
        self.assertEqual((result["left"]["scope"]["exam_count"], result["right"]["scope"]["exam_count"]), (2, 2))
        # One room can serve both exams if one of them moves to the afternoon pass: the run changes one start time and needs one room, A used two.
        self.assertEqual((result["changes"]["compared"], result["changes"]["time_changed"], result["changes"]["rooms_not_comparable"]), (2, 1, 0))
        self.assertGreaterEqual(result["changes"]["room_changed"], 1)  # the exam in the other building now shares a room
        moved = next(item for item in result["changes"]["list"] if item["time_changed"])
        self.assertEqual((moved["left"]["start"], moved["right"]["start"], moved["right"]["date"]), ("08:00", "14:00", "2026-01-12"))
        self.assertEqual({row["key"]: row["right"] for row in result["metrics"]}["rooms_used"], 1)
        self.assertEqual(result["cost"]["left"]["kind"], "historical")
        self.assertFalse(result["cost"]["left"]["available"])
        self.assertEqual(result["cost"]["right"]["kind"], "model")
        self.assertIsNone(result["cost"]["model_difference"])  # no cost difference against A is computed
        self.assertIn("Den faktiska bokningen (A) har inga parametrar", result["parameter_note"])
        self.assertEqual({row["key"]: row["left"] for row in result["metrics"]}["rooms_used"], 2)

    def test_two_runs_show_exactly_the_parameters_that_differ_and_a_model_difference(self) -> None:
        first = self.workspace.run("joint_base", name="B")
        second = self.workspace.run("joint_base", name="C", parameters={"window.later_days": 1})
        result = abc_compare.compare(self.storage, first, second)
        self.assertEqual([item["id"] for item in result["parameter_changes"]], ["window.later_days"])
        self.assertTrue(result["comparable"])
        self.assertEqual(result["cost"]["model_difference"]["ore"], result["cost"]["right"]["total_ore"] - result["cost"]["left"]["total_ore"])

    def test_cost_is_not_compared_when_the_cost_assumptions_differ(self) -> None:
        first = self.workspace.run("joint_base")
        second = self.workspace.run("joint_base", parameters={"cost.room_annual_per_seat_ore": 777})
        result = abc_compare.compare(self.storage, first, second)
        self.assertIsNone(result["cost"]["model_difference"])
        self.assertIs(result["cost"]["interpretable"], False)
        self.assertIn("antagandena", result["cost"]["interpretation"])

    def test_a_run_from_an_older_underlay_is_not_silently_compared_with_current_data(self) -> None:
        run_id = self.workspace.run("joint_base")
        demands = self.storage.processed_dir / "optimization_demands.csv"
        frame = pd.read_csv(demands, encoding="utf-8-sig")
        frame.loc[0, "demand_value"] = 51  # the underlay is updated after the run
        frame.to_csv(demands, index=False, encoding="utf-8-sig")
        row = abc_compare.list_runs(self.storage)[0]
        self.assertIs(row["current_underlay"], False)
        result = abc_compare.compare(self.storage, "actual", run_id)
        self.assertFalse(result["comparable"])
        self.assertTrue(any("annat underlag" in reason for reason in result["reasons"]))
        self.assertEqual(result["right"]["stale"]["current"], False)
        self.assertEqual(json.loads((self.workspace.directory(run_id) / "joint_input.json").read_text(encoding="utf-8"))["dataset_hash"], read_meta(self.workspace.directory(run_id))["dataset_hash"])

    def test_a_run_without_a_solution_is_reported_with_its_reason_and_no_cost_or_partial_placement(self) -> None:
        write_wishes(self.storage.processed_dir, [wish_row("X", "2026-01-17", booked="2026-01-12"), wish_row("Y", "2026-01-12", booked="2026-01-12")])  # 17 January is a Saturday
        run_id = self.workspace.run("joint_base", parameters={"wish.candidate_policy": "wishes", "calendar.weekdays": [1, 2, 3, 4, 5]})
        profile = abc_compare.profile(self.storage, run_id)
        self.assertFalse(profile["available"])
        self.assertEqual(profile["exams"], [])
        self.assertEqual(profile["cost"], {"kind": "model", "available": False})
        self.assertEqual([item["exam_event_id"] for item in profile["unplaced"]], ["exam-X".removeprefix("exam-")])
        self.assertIn("Blockerande", profile["unplaced"][0]["reason"])
        result = abc_compare.compare(self.storage, "actual", run_id)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["changes"])
        self.assertIsNone(result["cost"]["model_difference"])

    def test_the_same_reference_twice_is_refused(self) -> None:
        run_id = self.workspace.run("joint_base")
        with self.assertRaisesRegex(ValueError, "två olika"):
            abc_compare.compare(self.storage, run_id, run_id)
        with self.assertRaisesRegex(ValueError, "två olika"):
            abc_compare.compare(self.storage, "actual", "actual")

    def test_routes_list_runs_profile_compare_and_wishes(self) -> None:
        run_id = self.workspace.run("joint_base", name="Grundkörning")
        http = Http(self, self.storage.root)
        status, body = http.get("/api/abc/runs")
        self.assertEqual((status, [(row["run_id"], row["name"], row["kind"]) for row in body["runs"]]), (200, [(run_id, "Grundkörning", "B")]))
        status, profile = http.get("/api/abc/profile", ref="actual", scope_run=run_id, include_exams="false")
        self.assertEqual(status, 200)
        self.assertNotIn("exams", profile)
        self.assertEqual(profile["scope"]["exam_count"], 2)
        status, compared = http.get("/api/abc/compare", left="actual", right=run_id)
        self.assertEqual((status, compared["comparable"]), (200, True))
        self.assertEqual(http.get("/api/abc/compare", left=run_id, right=run_id)[0], 422)
        self.assertEqual(http.get("/api/abc/compare", left="../x", right=run_id)[0], 422)
        wishes = http.get("/api/abc/wishes")[1]
        self.assertEqual((wishes["available"], wishes["orders"], wishes["status"]["reserves_given"]), (True, 2, 1))
        (self.storage.processed_dir / "exam_wishes.csv").unlink()
        self.assertFalse(http.get("/api/abc/wishes")[1]["available"])


if __name__ == "__main__":
    unittest.main()
