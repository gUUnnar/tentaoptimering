"""A – the actual booking is reproduced as booked, with no optimisation, and its gaps are stated.

Synthetic bookings with exact expectations: an exam booked in two rooms is one exam with two places; a booking that names only an
address is never a room; a room that the optimisation model does not know is still shown and counted; a cancelled booking is
reported as not booked with its reason; the wish rank is the rank of the booked date among the wished dates. The module that
builds A must not depend on the optimiser.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wish_cases import wish_row, write_wishes  # noqa: E402
from tentaoptimering import profile_actual  # noqa: E402
from tentaoptimering.profile_actual import actual_profile, scope_event_ids  # noqa: E402

COLUMNS = ["placement_id", "exam_order_id", "course_codes", "course_name", "exam_type", "digital_exam", "scheduled_date", "scheduled_time",
           "address", "room", "location_key", "booked_places", "status"]
ROWS = [
    ("p1", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "Gata 1", "Sal 1", "gata-1|sal-1", "100", "Klar"),
    ("p2", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "Gata 1", "Sal 2", "gata-1|sal-2", "40", "Klar"),
    ("p3", "o2", "1BB002", "Algebra", "Omtenta", "Nej", "2026-02-09", "10:00-13:00", "Gata 5", "Sal 7", "gata-5|sal-7", "60", "Klar"),
    ("p4", "o3", "1CC003", "Fysik", "Ordinarie tenta", "Ja", "", "-", "Gata 1", "Sal 1", "gata-1|sal-1", "0", "Avbokad"),
    ("p5", "o4", "1DD004", "Kemi", "Ordinarie tenta", "Nej", "2026-02-10", "08:00-11:00", "Gata 2", "", "gata-2", "25", "Klar"),
]
ROOMS = [("uu-g1-s1", "gata-1|sal-1", "Gata 1", "Sal 1", "120"), ("uu-g1-s2", "gata-1|sal-2", "Gata 1", "Sal 2", "50")]
EVENTS = [("ev-1", "o1", "2026-02-09", "08:00-12:00", "Klar"), ("ev-2", "o2", "2026-02-09", "10:00-13:00", "Klar"),
          ("ev-3", "o3", "", "-", "Avbokad"), ("ev-4", "o4", "2026-02-10", "08:00-11:00", "Klar")]
DEMANDS = [("ev-1", "a1", "120"), ("ev-2", "a2", "60"), ("ev-3", "a3", "30"), ("ev-4", "a4", "25")]


def write_underlay(folder: Path) -> None:
    pd.DataFrame(ROWS, columns=COLUMNS).to_csv(folder / "bookings.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ROOMS, columns=["room_id", "location_key", "reference_address", "reference_room_name", "capacity_seats"]).to_csv(folder / "room_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"placement_id": ["p1"], "activity_id": ["a1"], "candidate_status": ["single_candidate"]}).to_csv(folder / "candidate_linkage.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"start_date": ["2026-02-01", "2026-03-10"]}).to_csv(folder / "ladok_activities.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(EVENTS, columns=["exam_event_id", "exam_order_id", "scheduled_date", "scheduled_time", "booking_statuses"]).to_csv(folder / "exam_events.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"exam_event_id": event, "activity_id": activity, "course_code": f"C-{event}", "scheduled_date": next(e[2] for e in EVENTS if e[0] == event),
                   "demand_input_status": "ready_provisional_ladok_demand", "observed_cities": "Uppsala", "demand_value": value, "observed_exam_types": "Ordinarie tenta"}
                  for event, activity, value in DEMANDS]).to_csv(folder / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"room_id": "uu-g1-s1"}, {"room_id": "uu-g1-s2"}]).to_csv(folder / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    write_wishes(folder, [
        wish_row("ev-1", "2026-02-09", booked="2026-02-09"), wish_row("ev-2", "2026-02-10", "2026-02-09", booked="2026-02-09"),
        wish_row("ev-3", "2026-02-11", None, None, "ej angivet"), wish_row("ev-4", "2026-02-12", None, None, ".", booked="2026-02-10"),
    ])


class ActualBookingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)
        write_underlay(self.dir)
        self.profile = actual_profile(self.dir, ["ev-1", "ev-2", "ev-3", "ev-4"])
        self.exams = {item["exam_event_id"]: item for item in self.profile["exams"]}

    def test_an_exam_keeps_the_date_time_rooms_and_places_it_was_booked_with(self) -> None:
        first = self.exams["ev-1"]
        self.assertEqual((first["date"], first["start"], first["end"], first["status"]), ("2026-02-09", "08:00", "12:00", "booked"))
        self.assertEqual(sorted((p["label"], p["booked_places"], p["capacity"]) for p in first["places"]), [("Gata 1 – Sal 1", 100, 120), ("Gata 1 – Sal 2", 40, 50)])
        self.assertEqual((first["participants"], first["booked_places"]), (120, 140))  # registered (Ladok) and booked places are two numbers

    def test_an_exam_in_two_rooms_is_one_exam_but_two_rooms(self) -> None:
        self.assertEqual(self.profile["scope"]["booked"], 3)
        self.assertEqual(self.profile["metrics"]["rooms_used"], 3)  # Sal 1, Sal 2 and the room that is not in the register

    def test_a_room_unknown_to_the_model_is_shown_and_counted_but_has_no_capacity(self) -> None:
        place = self.exams["ev-2"]["places"][0]
        self.assertEqual((place["identification"], place["capacity"], place["in_model_register"], place["room_id"]), ("room_named_not_in_register", None, False, None))
        self.assertEqual((self.profile["metrics"]["rooms_in_model_register"], self.profile["metrics"]["rooms_outside_model_register"]), (2, 1))
        self.assertTrue(any("finns inte i optimeringsmodellens lokalregister" in note for note in self.profile["notes"]))

    def test_an_address_without_a_room_is_never_a_room(self) -> None:
        place = self.exams["ev-4"]["places"][0]
        self.assertEqual((place["identification"], place["room_id"], place["capacity"]), ("address_only", None, None))
        self.assertEqual(self.profile["metrics"]["addresses_without_room"], 1)
        self.assertEqual(self.profile["metrics"]["rooms_used"], 3)
        self.assertTrue(any("bara adress" in note for note in self.profile["notes"]))

    def test_a_cancelled_booking_is_reported_as_not_booked_with_a_reason(self) -> None:
        self.assertEqual(self.exams["ev-3"]["status"], "not_booked")
        self.assertEqual([item["exam_event_id"] for item in self.profile["unplaced"]], ["ev-3"])
        self.assertIn("Avbokad", self.profile["unplaced"][0]["reason"])

    def test_the_wish_rank_is_where_the_booked_date_lies_among_the_wished_dates(self) -> None:
        self.assertEqual(self.profile["wish_distribution"], {"first": 1, "reserve_1": 1, "reserve_2": 0, "other": 1, "unknown": 0})
        self.assertEqual(self.exams["ev-4"]["wish"], {"dates": ["2026-02-12", None, None], "status": "reason_only", "reason": ".", "rank": "other"})
        self.assertEqual(self.exams["ev-3"]["wish"]["reason"], "ej angivet")  # the reason is kept as written

    def test_cost_is_not_invented_for_the_actual_booking(self) -> None:
        self.assertEqual((self.profile["cost"]["kind"], self.profile["cost"]["available"]), ("historical", False))
        self.assertIsNone(self.profile["metrics"]["staff_pool"])

    def test_a_scope_of_event_ids_limits_the_exams_and_a_period_selects_by_booked_date(self) -> None:
        self.assertEqual(actual_profile(self.dir, ["ev-1"])["scope"]["exam_count"], 1)
        self.assertEqual(scope_event_ids(self.dir, "Uppsala", "2026-02-10", None), ["ev-4"])
        self.assertEqual(scope_event_ids(self.dir, "Visby", None, None), [])

    def test_a_is_read_twice_without_change_and_does_not_depend_on_the_optimiser(self) -> None:
        self.assertEqual(actual_profile(self.dir, ["ev-1", "ev-2", "ev-3", "ev-4"]), self.profile)
        for module in (profile_actual, sys.modules["tentaoptimering.profile_common"]):
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            imported = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            self.assertFalse([name for name in imported if "optimizer" in name or "strategy" in name or "ortools" in name], f"{module.__name__} must not use the optimiser")

    def test_an_underlay_without_wishes_still_shows_the_booking_and_says_the_wishes_are_unknown(self) -> None:
        (self.dir / "exam_wishes.csv").unlink()
        profile = actual_profile(self.dir, ["ev-1", "ev-2"])
        self.assertEqual(profile["wish_distribution"], {"first": 0, "reserve_1": 0, "reserve_2": 0, "other": 0, "unknown": 2})
        self.assertEqual(profile["exams"][0]["date"], "2026-02-09")
        self.assertEqual(profile["exams"][0]["wish"]["status"], "not_loaded")

    def test_missing_underlay_is_a_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as empty, self.assertRaisesRegex(FileNotFoundError, "inte förberett"):
            actual_profile(Path(empty), ["ev-1"])


if __name__ == "__main__":
    unittest.main()
