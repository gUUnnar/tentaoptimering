"""Resource data: the pack contract, how a pack prices rooms and staff in a run, and the reservations built from bookings.

Real and simulated figures use one contract; every record keeps its origin; a room the pack does not price stays marked as a
per-seat proxy; a parameter that the user changed wins over the pack.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_joint_optimization_effects as fx  # noqa: E402
from test_abc_actual import write_underlay  # noqa: E402
from tentaoptimering.joint_contract import CandidateSlot, Room  # noqa: E402
from tentaoptimering.joint_reservations import build_reservations  # noqa: E402
from tentaoptimering.joint_resources import save_pack_snapshot  # noqa: E402
from tentaoptimering.resource_data import ResourceDataError, list_packs, load_pack, pack_directory, resolve_pack  # noqa: E402

BUNDLED = fx.REPO_ROOT / "config" / "resource_data"

PACK = """
schema_version = "resource-data-v1"
[pack]
id = "test_pack"
name = "Testpaket"
origin = "simulated"
valid_from = "2026-01-01"
valid_to = "2026-12-31"

[[cost_object]]
id = "ko-shared"
name = "Delat avtal"
kind = "internal_rent"
annual_cost_ore = 9000
avoidable = "unknown"
origin = "simulated"

[[room]]
id = "uu-r1"
name = "Sal ett"
kind = "internal"
cost_object_id = "ko-shared"
travel_paid_minutes = 10
origin = "simulated"

[[room]]
id = "ext-hall"
name = "Extern hall"
kind = "external"
plan_area = "Uppsala"
building_id = "hall"
capacity = 60
cost_object_id = "ko-shared"
origin = "simulated"
[room.charge]
basis = "per_hour"
price_ore = 1000
min_billed_minutes = 120
assumed_billed_minutes = 300
terms = "test"

[staff]
paid_minute_cost_ore = 7
min_paid_shift_minutes = 90
pool_annual_cost_ore = 0
origin = "simulated"
"""


def _config(root: Path, text: str = PACK) -> Path:
    """A copy of the catalog with a `resource_data` folder next to it holding the test pack."""
    catalog = root / "joint_parameter_catalog.toml"
    shutil.copyfile(fx.CATALOG, catalog)
    (root / "resource_data").mkdir()
    (root / "resource_data" / "test_pack.toml").write_text(text, encoding="utf-8")
    return catalog


def _build(root: Path, overrides: dict[str, object], rooms: list[tuple] | None = None):
    """Build (not solve) a problem for two exams and the given rooms with the test catalog copy."""
    from tentaoptimering import joint_inputs

    catalog = _config(root)
    original = fx.CATALOG
    fx.CATALOG = catalog
    joint_inputs_catalog = joint_inputs.build_real_subset_problem
    try:
        return _problem_only(root, overrides, rooms, catalog, joint_inputs_catalog)
    finally:
        fx.CATALOG = original


def _problem_only(root: Path, overrides, rooms, catalog: Path, builder):
    import pandas as pd

    events = fx.PAIR
    pd.DataFrame(events).to_csv(root / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"room_id": room, "reference_address": address, "reference_city": "Uppsala", "capacity_seats": cap, "digital_capability_status": status,
                   "eligible_for_exploratory_capacity_poc": True, "eligible_for_operational_scheduling": False, "available_from": None, "available_to": None}
                  for room, address, cap, status in (rooms or fx.TWO_ROOMS)]).to_csv(root / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"activity_id": [item["activity_id"] for item in events], "scope_status": ["included"] * len(events)}).to_csv(root / "demand_scope.csv", index=False, encoding="utf-8-sig")
    parameters = {**fx.BASE, **overrides}
    ids = ", ".join(json.dumps(item["exam_event_id"]) for item in events)
    scenario = root / "scenario.toml"
    scenario.write_text('schema_version = "joint-real-subset-v1"\n[scenario]\nid = "res"\ndescription = "d"\n'
                        f'[subset]\nplan_area = "Uppsala"\nexam_event_ids = [{ids}]\n[parameters]\n'
                        + "\n".join(f"{json.dumps(key)} = {fx._toml(value)}" for key, value in parameters.items()) + "\n", encoding="utf-8")
    return builder(scenario, root, catalog)


class PackContractTests(unittest.TestCase):
    def test_the_bundled_simulated_pack_loads_and_is_marked_simulated(self) -> None:
        pack = resolve_pack("simulated_dev_2026", BUNDLED)
        self.assertEqual(pack.origin, "simulated")
        self.assertTrue(all(item.provenance.origin == "simulated" for item in pack.rooms + pack.cost_objects))
        self.assertEqual(pack.staff.provenance.origin, "simulated")
        self.assertTrue(all(item.provenance.origin == "simulated" for item in pack.actual_staffing))  # never presented as observed
        self.assertIn("simulated_dev_2026", {item["id"] for item in list_packs(BUNDLED)})
        self.assertEqual(len(pack.sha256), 64)

    def test_external_charge_is_a_priced_session(self) -> None:
        pack = resolve_pack("simulated_dev_2026", BUNDLED)
        hall_d, hall_f = pack.room("uu-fyrishov-hall-d"), pack.room("uu-fyrishov-hall-f")
        self.assertEqual(hall_d.charge.session_cost_ore, 300000 * 300 // 60)  # 3 000 kr per hour, a pass billed as 5 hours
        self.assertEqual(hall_f.charge.session_cost_ore, 1200000)  # a flat price per session

    def test_malformed_packs_are_refused_with_the_record_named(self) -> None:
        cases = {
            "okänt ursprung": PACK.replace('origin = "simulated"\nvalid_from', 'origin = "påhittad"\nvalid_from'),
            "extern sal utan debitering": PACK.replace("[room.charge]\nbasis", "[room.xcharge]\nbasis"),
            "okänt avtalsobjekt": PACK.replace('cost_object_id = "ko-shared"\ntravel', 'cost_object_id = "ko-saknas"\ntravel'),
        }
        for name, text in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "p.toml"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ResourceDataError):
                    load_pack(path)

    def test_a_missing_pack_is_an_error_never_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ResourceDataError):
                resolve_pack("finns_inte", Path(temp))


class PackInRunTests(unittest.TestCase):
    def test_pack_prices_rooms_adds_external_hire_and_keeps_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            problem = _build(Path(temp), {"resources.pack": "test_pack"})
        rooms = {room.room_id: room for room in problem.rooms}
        # uu-r1 shares a 9 000 contract with ext-hall (two rooms of the object): an even share of 4 500 (model calculated)
        self.assertEqual((rooms["uu-r1"].annual_fixed_cost_ore, rooms["uu-r1"].cost_origin, rooms["uu-r1"].name), (4500, "model_calculated", "Sal ett"))
        self.assertEqual(rooms["uu-r1"].travel_paid_minutes, 10)
        # uu-r2 is not in the pack: the per-seat parameter prices it and says so
        self.assertEqual((rooms["uu-r2"].annual_fixed_cost_ore, rooms["uu-r2"].cost_origin), (6000, "parameter_proxy"))
        hall = rooms["ext-hall"]
        self.assertEqual((hall.kind, hall.annual_fixed_cost_ore, hall.external_session_cost_ore, hall.capacity), ("external", 0, 1000 * 300 // 60, 60))
        self.assertEqual(problem.resource_basis["pack"]["pack_id"], "test_pack")
        self.assertTrue(any("uu-r2" in text for text in problem.resource_basis["warnings"]))

    def test_staff_values_come_from_the_pack_unless_the_user_changed_the_parameter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            packed = _build(Path(temp), {"resources.pack": "test_pack", "cost.staff_annual_ore": 0})
        self.assertEqual((packed.staffing.paid_minute_cost_ore, packed.staffing.min_paid_minutes), (7, 90))
        self.assertEqual(packed.resource_basis["staff"]["paid_minute_cost_ore"]["source"], "resource_data")
        with tempfile.TemporaryDirectory() as temp:
            changed = _build(Path(temp), {"resources.pack": "test_pack", "cost.staff_paid_minute_ore": 11})
        self.assertEqual(changed.staffing.paid_minute_cost_ore, 11)
        self.assertEqual(changed.resource_basis["staff"]["paid_minute_cost_ore"]["source"], "parameter")
        with tempfile.TemporaryDirectory() as temp:
            none = _build(Path(temp), {})
        self.assertEqual((none.staffing.paid_minute_cost_ore, none.resource_basis["pack"]), (0, None))
        self.assertNotIn("ext-hall", {room.room_id for room in none.rooms})

    def test_excluded_rooms_leave_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            problem = _build(Path(temp), {"resources.pack": "test_pack", "rooms.exclude": ["uu-r2", "ext-hall"]})
        self.assertEqual({room.room_id for room in problem.rooms}, {"uu-r1"})
        self.assertEqual(problem.resource_basis["excluded_rooms"], ["ext-hall", "uu-r2"])
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "Okänd sal i rooms.exclude: uu-saknas"):
            _build(Path(temp), {"resources.pack": "test_pack", "rooms.exclude": ["uu-saknas"]})  # an exclusion is never silently ignored

    def test_the_run_freezes_the_pack_it_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            problem = _build(root, {"resources.pack": "test_pack"})
            run = root / "run"
            run.mkdir()
            digest = save_pack_snapshot(problem.resource_basis, root / "joint_parameter_catalog.toml", run)
            snapshot = json.loads((run / "resource_pack.json").read_text(encoding="utf-8"))
            self.assertEqual((snapshot["pack_id"], snapshot["sha256"]), ("test_pack", problem.resource_basis["pack"]["pack_sha256"]))
            self.assertEqual(len(digest), 64)
            (pack_directory(root / "joint_parameter_catalog.toml") / "test_pack.toml").write_text(PACK + "\n# changed\n", encoding="utf-8")
            with self.assertRaises(ResourceDataError):
                save_pack_snapshot(problem.resource_basis, root / "joint_parameter_catalog.toml", run)


class ReservationBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)
        write_underlay(self.dir)
        self.rooms = (Room("uu-g1-s1", "gata-1", "Uppsala", 120, 0), Room("uu-g1-s2", "gata-1", "Uppsala", 50, 0))
        self.slots = (CandidateSlot("a", date(2026, 2, 9), "08:00", 480, 1200), CandidateSlot("b", date(2026, 2, 10), "08:00", 480, 1200))

    def test_other_exams_in_identified_rooms_block_and_the_rest_is_reported_unidentified(self) -> None:
        reservations, basis = build_reservations(self.dir, {"ev-2"}, self.rooms, self.slots, "block_identified")
        # ev-1 (two rooms, 08:00-12:00 on 2026-02-09) blocks both; ev-4 names only an address; ev-3 is cancelled and has no date
        self.assertEqual([(item.room_id, item.start_minute, item.end_minute, item.exam_event_id) for item in reservations],
                         [("uu-g1-s1", 480, 720, "ev-1"), ("uu-g1-s2", 480, 720, "ev-1")])
        self.assertEqual((basis["blocking"], basis["unidentified_bookings"], basis["unidentified_booked_places"]), (2, 1, 25))
        self.assertEqual(basis["status"], "read")

    def test_other_bookings_are_grouped_by_why_they_are_not_exams_and_each_group_has_an_explicit_action(self) -> None:
        import pandas as pd

        demands = pd.read_csv(self.dir / "optimization_demands.csv", encoding="utf-8-sig", dtype=str)
        demands.loc[demands["exam_event_id"] == "ev-1", "demand_input_status"] = "not_ready_missing_demand"  # ev-1 has no participant count
        demands.to_csv(self.dir / "optimization_demands.csv", index=False, encoding="utf-8-sig")
        reservations, basis = build_reservations(self.dir, {"ev-2"}, self.rooms, self.slots, "block_identified")
        groups = {item["group"]: item for item in basis["groups"]}
        self.assertEqual((groups["no_participant_count"]["bookings"], groups["no_participant_count"]["action"], groups["outside_selection"]["bookings"]), (2, "keep_fixed", 0))
        self.assertEqual(sorted(groups["no_participant_count"]["rooms"]), ["uu-g1-s1", "uu-g1-s2"])
        self.assertEqual({item.group for item in reservations}, {"no_participant_count"})  # careful default: kept fixed
        self.assertEqual(len(basis["bookings"]), 2)
        self.assertEqual(basis["actions"], {"no_participant_count": "keep_fixed", "outside_selection": "keep_fixed", "not_in_ladok": "keep_fixed"})
        reservations, basis = build_reservations(self.dir, {"ev-2"}, self.rooms, self.slots, "block_identified", {"no_participant_count": "remove"})
        self.assertEqual((reservations, basis["blocking"], basis["removed"]), ((), 0, 2))  # removed by choice, still listed
        self.assertEqual({item["action"] for item in basis["bookings"]}, {"remove"})
        # a booking whose exam is not in the demand file at all is its own group
        demands[demands["exam_event_id"] != "ev-1"].to_csv(self.dir / "optimization_demands.csv", index=False, encoding="utf-8-sig")
        _, basis = build_reservations(self.dir, {"ev-2"}, self.rooms, self.slots, "block_identified")
        self.assertEqual({item["group"]: item["bookings"] for item in basis["groups"]}["not_in_ladok"], 2)

    def test_the_exams_of_the_selection_are_not_reservations(self) -> None:
        reservations, _ = build_reservations(self.dir, {"ev-1", "ev-2", "ev-4"}, self.rooms, self.slots, "block_identified")
        self.assertEqual(reservations, ())

    def test_dates_outside_the_calendar_and_rooms_outside_the_model_block_nothing(self) -> None:
        only_tuesday = (self.slots[1],)
        reservations, _ = build_reservations(self.dir, {"ev-2"}, self.rooms, only_tuesday, "block_identified")
        self.assertEqual(reservations, ())
        reservations, basis = build_reservations(self.dir, {"ev-2"}, (self.rooms[0],), self.slots, "block_identified")
        self.assertEqual([item.room_id for item in reservations], ["uu-g1-s1"])  # the booking in the room the model lacks is not a reservation

    def test_ignoring_is_explicit_and_missing_bookings_are_stated(self) -> None:
        reservations, basis = build_reservations(self.dir, {"ev-2"}, self.rooms, self.slots, "none")
        self.assertEqual((reservations, basis["status"]), ((), "ignored_by_parameter"))
        with tempfile.TemporaryDirectory() as empty:
            reservations, basis = build_reservations(Path(empty), set(), self.rooms, self.slots, "block_identified")
            self.assertEqual((reservations, basis["status"]), ((), "bookings_unavailable"))


if __name__ == "__main__":
    unittest.main()
