"""The whole chain on real files: resource data and bookings in, optimised runs, independent validation, explained comparison.

Three exams on 2026-01-12: X (120, 08:00-12:00) and Y (120, 08:00-12:00) booked in two small rooms, Z (200, 14:00-17:00) booked in
the external hall D. Two more exams, W and W2, are outside the optimised selection: W holds room 1 on the afternoon and W2 the big
room on the morning. The pack prices rooms (rent 100 000 for room 1, 120 000 for room 2, 150 000 for the big room), the external
hall at 500 000 per session, staff at 10 öre per paid minute (shortest pass 120), preparation and closing 30. The expected
figures are worked out by hand in the tests.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from tentaoptimering import abc_compare  # noqa: E402
from tentaoptimering.app_storage import AppStorage  # noqa: E402
from tentaoptimering.joint_inputs import run_real_subset  # noqa: E402
from tentaoptimering.joint_validation import validate_run  # noqa: E402

PACK = """
schema_version = "resource-data-v1"
[pack]
id = "chain_pack"
name = "Kedjepaket"
origin = "simulated"
valid_from = "2026-01-01"
valid_to = "2026-12-31"

[[cost_object]]
id = "ko-r1"
name = "Avtal sal 1"
kind = "internal_rent"
annual_cost_ore = 100000
avoidable = "yes"
notice_months = 6
earliest_release_date = "2027-07-01"
one_off_cost_ore = 5000
origin = "simulated"
[[cost_object]]
id = "ko-r2"
name = "Avtal sal 2"
kind = "internal_rent"
annual_cost_ore = 120000
avoidable = "yes"
notice_months = 6
earliest_release_date = "2027-07-01"
one_off_cost_ore = 5000
origin = "simulated"
[[cost_object]]
id = "ko-big"
name = "Avtal stora salen"
kind = "internal_rent"
annual_cost_ore = 150000
avoidable = "unknown"
origin = "simulated"
[[cost_object]]
id = "ko-ext"
name = "Externhyra Fyrishov"
kind = "external_hire"
annual_cost_ore = 0
avoidable = "yes"
origin = "simulated"

[[room]]
id = "uu-r1"
name = "Sal 1 (liten)"
kind = "internal"
annual_cost_ore = 100000
cost_object_id = "ko-r1"
origin = "simulated"
[[room]]
id = "uu-r2"
name = "Sal 2 (liten)"
kind = "internal"
annual_cost_ore = 120000
cost_object_id = "ko-r2"
origin = "simulated"
[[room]]
id = "uu-big"
name = "Stora salen"
kind = "internal"
annual_cost_ore = 150000
cost_object_id = "ko-big"
origin = "simulated"
[[room]]
id = "uu-fyrishov-hall-d"
name = "Fyrishov, Sal D"
kind = "external"
plan_area = "Uppsala"
building_id = "fyrishov"
capacity = 300
cost_object_id = "ko-ext"
travel_paid_minutes = 30
origin = "simulated"
[room.charge]
basis = "per_session"
price_ore = 500000
terms = "5 000 kr per tillfälle"

[staff]
paid_minute_cost_ore = 10
min_paid_shift_minutes = 120
pool_annual_cost_ore = 0
origin = "simulated"
"""

PARAMETERS = {
    **fx.BASE, "staffing.ladder": [{"max_participants": 150, "required_staff": 1}, {"max_participants": 300, "required_staff": 2}],
    "staffing.preparation_minutes": 30, "staffing.closing_minutes": 30, "cost.room_annual_per_seat_ore": 0, "cost.staff_annual_ore": 0,
    "resources.pack": "chain_pack", "solver.strategy": "monolithic", "solver.time_limit_seconds": 30.0,
}
BOOKING_COLUMNS = ["placement_id", "exam_order_id", "course_codes", "course_name", "exam_type", "digital_exam", "scheduled_date", "scheduled_time",
                   "address", "room", "location_key", "booked_places", "status"]


def write_case(root: Path) -> tuple[AppStorage, Path, Path]:
    """Processed data, a catalog copy with the test pack, and the scenario file; returns storage, catalog and scenario."""
    storage = AppStorage(root / "app")
    folder = storage.processed_dir
    events = [fx._event("X", count=120), fx._event("Y", count=120), fx._event("Z", start="14:00", end="17:00", count=200)]
    pd.DataFrame(events).to_csv(folder / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    rooms = [("uu-r1", "Adress 1", 130), ("uu-r2", "Adress 2", 130), ("uu-big", "Adress 3", 220)]
    pd.DataFrame([{"room_id": room, "reference_address": address, "reference_city": "Uppsala", "capacity_seats": cap, "digital_capability_status": "all_places_support_e_exam",
                   "eligible_for_exploratory_capacity_poc": True, "eligible_for_operational_scheduling": False, "available_from": None, "available_to": None}
                  for room, address, cap in rooms]).to_csv(folder / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"activity_id": [f"act-{name}" for name in "XYZ"], "scope_status": ["included"] * 3}).to_csv(folder / "demand_scope.csv", index=False, encoding="utf-8-sig")
    inventory = [("uu-r1", "adress-1|sal-1", "Adress 1", "Sal 1", "130"), ("uu-r2", "adress-2|sal-1", "Adress 2", "Sal 1", "130"), ("uu-big", "adress-3|sal-1", "Adress 3", "Sal 1", "220"),
                 ("uu-fyrishov-hall-d", "fyrishov|sal-d", "Fyrishov", "Sal D", "")]
    pd.DataFrame(inventory, columns=["room_id", "location_key", "reference_address", "reference_room_name", "capacity_seats"]).to_csv(folder / "room_inventory.csv", index=False, encoding="utf-8-sig")
    bookings = [("p1", "ox", "C-X", "X", "Ordinarie tenta", "Nej", "2026-01-12", "08:00-12:00", "Adress 1", "Sal 1", "adress-1|sal-1", "120", "Klar"),
                ("p2", "oy", "C-Y", "Y", "Ordinarie tenta", "Nej", "2026-01-12", "08:00-12:00", "Adress 2", "Sal 1", "adress-2|sal-1", "120", "Klar"),
                ("p3", "oz", "C-Z", "Z", "Ordinarie tenta", "Nej", "2026-01-12", "14:00-17:00", "Fyrishov", "Sal D", "fyrishov|sal-d", "200", "Klar"),
                ("p4", "ow", "C-W", "W", "Ordinarie tenta", "Nej", "2026-01-12", "14:00-17:00", "Adress 1", "Sal 1", "adress-1|sal-1", "30", "Klar"),
                ("p5", "ow2", "C-W2", "W2", "Ordinarie tenta", "Nej", "2026-01-12", "08:00-12:00", "Adress 3", "Sal 1", "adress-3|sal-1", "30", "Klar")]
    pd.DataFrame(bookings, columns=BOOKING_COLUMNS).to_csv(folder / "bookings.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["placement_id", "activity_id", "candidate_status"]).to_csv(folder / "candidate_linkage.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"start_date": ["2026-01-01"]}).to_csv(folder / "ladok_activities.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([("X", "ox", "2026-01-12", "08:00-12:00", "Klar"), ("Y", "oy", "2026-01-12", "08:00-12:00", "Klar"), ("Z", "oz", "2026-01-12", "14:00-17:00", "Klar"),
                  ("W", "ow", "2026-01-12", "14:00-17:00", "Klar"), ("W2", "ow2", "2026-01-12", "08:00-12:00", "Klar")], columns=["exam_event_id", "exam_order_id", "scheduled_date", "scheduled_time", "booking_statuses"]
                 ).to_csv(folder / "exam_events.csv", index=False, encoding="utf-8-sig")
    config = root / "config"
    (config / "resource_data").mkdir(parents=True)
    catalog = config / "joint_parameter_catalog.toml"
    shutil.copyfile(fx.CATALOG, catalog)
    (config / "resource_data" / "chain_pack.toml").write_text(PACK, encoding="utf-8")
    return storage, catalog, folder / "scenario.toml"


def write_scenario(path: Path, overrides: dict[str, object], scenario_id: str) -> Path:
    parameters = {**PARAMETERS, **overrides}
    path.write_text('schema_version = "joint-real-subset-v1"\n[scenario]\n' + f'id = "{scenario_id}"\ndescription = "d"\n[subset]\nplan_area = "Uppsala"\n'
                    'exam_event_ids = ["X", "Y", "Z"]\n[parameters]\n' + "\n".join(f"{json.dumps(key)} = {fx._toml(value)}" for key, value in parameters.items()) + "\n", encoding="utf-8")
    return path


class ChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.storage, cls.catalog, scenario = write_case(root)
        cls.processed = cls.storage.processed_dir

        def run(overrides: dict[str, object], name: str) -> str:
            path = write_scenario(scenario, overrides, name)
            return run_real_subset(path, cls.processed, cls.catalog, cls.storage.runs_dir, warm_start="none")["run_id"]

        cls.free = run({"reservations.policy": "none"}, "chain_free")
        cls.blocked = run({}, "chain_blocked")
        cls.no_room = run({"reservations.policy": "none", "rooms.exclude": ["uu-big"]}, "chain_nobig")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def _validated(self, run_id: str) -> dict[str, dict]:
        payload = validate_run(self.storage.run_directory(run_id))
        return {item["rule_id"]: item for item in payload["rules"]}

    def test_every_run_is_technically_valid_and_records_its_resource_basis(self) -> None:
        for run_id in (self.free, self.blocked):
            rules = self._validated(run_id)
            self.assertEqual([name for name, item in rules.items() if item["status"] == "fail"], [], run_id)
            self.assertEqual(rules["paid_time_recomputed"]["status"], "pass")
            self.assertEqual(rules["resource_pack_hash"]["status"], "pass")
            self.assertEqual(rules["resource_data_verified"]["status"], "not_evaluated")  # simulated data is never verified
            self.assertEqual(rules["reservations_coverage_verified"]["status"], "not_evaluated")
        self.assertEqual(self._validated(self.free)["reservations_respected"]["status"], "not_applicable")
        self.assertEqual(self._validated(self.blocked)["reservations_respected"]["status"], "pass")
        basis = json.loads((self.storage.run_directory(self.blocked) / "joint_input.json").read_text(encoding="utf-8"))["resource_basis"]
        self.assertEqual((basis["pack"]["pack_id"], basis["pack"]["pack_origin"], basis["reservations"]["blocking"]), ("chain_pack", "simulated", 2))
        self.assertTrue((self.storage.run_directory(self.blocked) / "resource_pack.json").is_file())

    def test_the_actual_booking_against_an_optimised_run_is_explained_in_rooms_bookings_and_paid_hours(self) -> None:
        result = abc_compare.compare(self.storage, "actual", self.free)
        explained = result["explained"]
        self.assertTrue(explained["available"], explained["reasons"])
        # A priced by the rules of the run: rooms 1 and 2 (220 000), the external hall once (500 000), paid time (300 + 300 + 2 x 270) x 10
        # The run: room 1 and the big room (250 000), no external hall, paid time (300 + 300 + 2 x 240) x 10
        self.assertEqual((explained["total"]["left_ore"], explained["total"]["right_ore"]), (731_400, 260_800))
        self.assertEqual(explained["total"]["difference_ore"], -470_600)
        items = {item["key"]: item["difference_ore"] for item in explained["items"]}
        self.assertEqual(items, {"rooms": 30_000, "external": -500_000, "staff": -600})
        self.assertEqual(sum(items.values()), explained["total"]["difference_ore"])
        self.assertEqual(explained["basis"]["left"]["cost_kind"], "model_calculated_for_historical_bookings")
        self.assertEqual(explained["basis"]["left"]["staffing_origin"], "model_calculated_from_booked_places")
        rooms = {row["room_id"]: row for row in explained["rooms"]}
        self.assertEqual((rooms["uu-r2"]["status"], rooms["uu-big"]["status"], rooms["uu-r1"]["status"]), ("avoidable", "added", "kept"))
        self.assertEqual((rooms["uu-r2"]["name"], rooms["uu-r2"]["fixed_difference_ore"]), ("Sal 2 (liten)", -120_000))
        self.assertEqual(explained["sessions"]["external"]["avoided_ore"], 500_000)
        self.assertEqual(explained["sessions"]["external"]["avoided"][0]["exams"], ["Z"])
        self.assertEqual((explained["staffing"]["left"]["paid_minutes"], explained["staffing"]["right"]["paid_minutes"]), (1140, 1080))
        changed = {row["exam_event_id"]: row for row in explained["exams"]["changed"]}
        self.assertIn("external_avoided", changed["Z"]["tags"])
        self.assertIn("room_freed:uu-r2", changed["Y"]["tags"])
        self.assertEqual(explained["split"]["assumption_ore"], 0)

    def test_a_freed_room_is_a_conditional_saving_and_nothing_is_verified_from_simulated_terms(self) -> None:
        explained = abc_compare.compare(self.storage, "actual", self.free)["explained"]
        by_room = {item["room_id"]: item for item in explained["realization"]["items"]}
        self.assertEqual(by_room["uu-r2"]["realization"]["status"], "possible_unverified")
        self.assertEqual(by_room["uu-fyrishov-hall-d"]["realization"]["status"], "possible_unverified")
        self.assertEqual(explained["realization"]["summary"]["verified_ore"], 0)
        self.assertEqual(explained["realization"]["summary"]["modelled_saving_ore"], 620_000)
        self.assertFalse(explained["savings_kinds"]["verified_realisable"]["available"])
        self.assertTrue(explained["data_quality"]["simulated"])

    def test_existing_bookings_block_the_attractive_placement(self) -> None:
        free = json.loads((self.storage.run_directory(self.free) / "joint_result.json").read_text(encoding="utf-8"))
        blocked = json.loads((self.storage.run_directory(self.blocked) / "joint_result.json").read_text(encoding="utf-8"))
        # Without the other bookings the big room and room 1 are enough (250 000). Room 1 is booked on the afternoon and the big room
        # on the morning, so the second exam of room 1 has nowhere to go but room 2 (120 000 more).
        self.assertEqual({row["room_id"] for row in free["room_sessions"]}, {"uu-r1", "uu-big"})
        self.assertEqual({row["room_id"] for row in blocked["room_sessions"]}, {"uu-r1", "uu-big", "uu-r2"})
        self.assertEqual((free["costs"]["comparable_total_cost_ore"], blocked["costs"]["comparable_total_cost_ore"]), (260_800, 380_800))
        for row in blocked["room_sessions"]:
            if row["room_id"] == "uu-big":
                self.assertEqual(row["slot_id"], "2026-01-12T14:00")  # only the afternoon is free
        explained = abc_compare.compare(self.storage, self.free, self.blocked)["explained"]
        self.assertTrue(explained["available"], explained["reasons"])
        self.assertEqual(explained["total"]["difference_ore"], 120_000)
        self.assertEqual(explained["added_rooms"], ["uu-r2"])
        self.assertEqual(sum(item["difference_ore"] for item in explained["items"]), explained["total"]["difference_ore"])
        self.assertTrue(any("fasta bokningar" in flag["text"].lower() or "ignorerades" in flag["text"] for flag in explained["data_quality"]["flags"]))

    def test_excluding_a_room_shows_the_consequence_in_money_and_bookings(self) -> None:
        explained = abc_compare.compare(self.storage, self.free, self.no_room)["explained"]
        self.assertTrue(explained["available"], explained["reasons"])
        # without the big room the 200 participants must go to the external hall: rent 150 000 is replaced by 500 000 per session
        items = {item["key"]: item["difference_ore"] for item in explained["items"]}
        self.assertEqual((items["rooms"], items["external"], items["staff"]), (-150_000, 500_000, 600))
        rooms = {row["room_id"]: row for row in explained["rooms"]}
        self.assertEqual(rooms["uu-big"]["status"], "avoidable")
        self.assertEqual(explained["sessions"]["external"]["added_ore"], 500_000)
        self.assertGreater(explained["total"]["difference_ore"], 0)

    def test_prices_changed_between_two_runs_are_separated_from_changed_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            storage, catalog, scenario = write_case(root)
            pack = root / "config" / "resource_data" / "chain_pack.toml"
            ids = []
            for name, minute_cost in (("price_before", 10), ("price_after", 20)):
                pack.write_text(PACK.replace("paid_minute_cost_ore = 10", f"paid_minute_cost_ore = {minute_cost}"), encoding="utf-8")
                path = write_scenario(scenario, {"reservations.policy": "none"}, name)
                ids.append(run_real_subset(path, storage.processed_dir, catalog, storage.runs_dir, warm_start="none")["run_id"])
            explained = abc_compare.compare(storage, ids[0], ids[1])["explained"]
            self.assertTrue(explained["available"], explained["reasons"])
            self.assertFalse(explained["split"]["same_prices"])
            self.assertEqual(explained["split"]["usage_ore"] + explained["split"]["assumption_ore"], explained["total"]["difference_ore"])
            # the same plan (1 080 paid minutes) costs 10 öre more per minute: 10 800 more, and nothing changed in how the resources are used
            self.assertEqual((explained["split"]["usage_ore"], explained["split"]["assumption_ore"]), (0, 10_800))
            staff = next(item for item in explained["items"] if item["key"] == "staff")
            self.assertEqual((staff["usage_ore"], staff["assumption_ore"]), (0, 10_800))

    def test_a_run_without_a_verified_solution_blocks_the_explanation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            storage, catalog, scenario = write_case(root)

            def run(overrides: dict[str, object], name: str) -> str:
                return run_real_subset(write_scenario(scenario, overrides, name), storage.processed_dir, catalog, storage.runs_dir, warm_start="none")["run_id"]

            ok = run({"reservations.policy": "none"}, "chain_ok")
            bad = run({"reservations.policy": "none", "rooms.selection": ["uu-r1"]}, "chain_none")  # only a small room: 200 participants cannot be placed
            explained = abc_compare.compare(storage, ok, bad)["explained"]
            self.assertFalse(explained["available"])
            self.assertTrue(explained["reasons"])
            self.assertNotIn("items", explained)


if __name__ == "__main__":
    unittest.main()
