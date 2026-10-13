"""The booking overview (day/period, address, room) and the comparison of a booked exam with a saved run.

Synthetic bookings, register, links and a hand-made run give exact expectations: an exam in two rooms is counted once in the
totals, bookings without a room stay under their address and are never given a room, cancelled bookings are counted apart, and
a comparison says `no_link` / `not_in_run` instead of guessing. A test against the prepared data checks counts independently.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from tentaoptimering import booking_compare as compare
from tentaoptimering import booking_overview as overview
from tentaoptimering.app_storage import AppStorage

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
COLUMNS = ["placement_id", "exam_order_id", "course_codes", "course_name", "exam_type", "digital_exam", "scheduled_date", "scheduled_time",
           "address", "room", "location_key", "booked_places", "status"]
# placement, order, course, name, type, digital, date, time, address, room, key, places, status
ROWS = [
    ("p1", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "Gata 1", "Sal 1", "gata-1|sal-1", "100", "Klar"),
    ("p2", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "Gata 1", "Sal 2", "gata-1|sal-2", "40", "Klar"),
    ("p3", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "Gata 2", "", "gata-2", "5", "Klar"),
    ("p4", "o2", "1BB002", "Algebra", "Omtenta", "Nej", "2026-02-09", "10:00-13:00", "Gata 1", "Sal 1", "gata-1|sal-1", "60", "Klar"),
    ("p5", "o3", "1CC003", "Fysik", "Ordinarie tenta", "Ja", "2026-02-09", "14:00-16:00", "Gata 1", "Sal 1", "gata-1|sal-1", "30", "Avbokad"),
    ("p6", "o4", "1DD004", "Kemi", "Ordinarie tenta", "Nej", "2026-02-10", "08:00-11:00", "Gata 2", "", "gata-2", "25", "Klar"),
    ("p7", "o5", "1EE005", "Biologi", "Ordinarie tenta", "Nej", "2026-02-10", "08:00-11:00", "", "", "", "7", "Klar"),
    ("p8", "o6", "Extern", "Ahmed", "", "", "", "-", "", "", "", "0", "Avbokad"),
    ("p9", "o7", "1FF006", "Geologi", "Ordinarie tenta", "Nej", "2026-03-20", "08:00-11:00", "Gata 1", "Sal 1", "gata-1|sal-1", "10", "Klar"),
    ("p10", "o8", "1GG007", "Zoologi", "Ordinarie tenta", "Nej", "2026-03-25", "08:00-11:00", "Gata 1", "Sal 1", "gata-1|sal-1", "5", "Klar"),
]
ROOMS = [("uu-g1-s1", "gata-1|sal-1", "Gata 1", "Sal 1", "120"), ("uu-g1-s2", "gata-1|sal-2", "Gata 1", "Sal 2", "50"), ("uu-g3-s9", "gata-3|sal-9", "Gata 3", "Sal 9", "80")]
LINKS = [("p1", "act-1", "single_candidate"), ("p2", "act-1", "single_candidate"), ("p3", "act-1", "single_candidate"), ("p4", "", "no_candidate"),
         ("p6", "act-9", "single_candidate"), ("p9", "act-5", "ambiguous_candidates"), ("p9", "act-6", "ambiguous_candidates")]


def _write(folder: Path) -> None:
    pd.DataFrame(ROWS, columns=COLUMNS).to_csv(folder / "bookings.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ROOMS, columns=["room_id", "location_key", "reference_address", "reference_room_name", "capacity_seats"]).to_csv(folder / "room_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LINKS, columns=["placement_id", "activity_id", "candidate_status"]).to_csv(folder / "candidate_linkage.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"start_date": ["2026-02-01", "2026-03-10"]}).to_csv(folder / "ladok_activities.csv", index=False, encoding="utf-8-sig")  # Ladok covers Feb to 10 March


class OverviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)
        _write(self.dir)

    def test_an_exam_in_several_places_is_counted_once_in_the_totals_but_in_each_place(self) -> None:
        result = overview.overview_payload(self.dir, date(2026, 2, 9), date(2026, 2, 9))
        totals = result["totals"]
        self.assertEqual((totals["placements"], totals["cancelled_placements"], totals["exam_orders"], totals["booked_places"]), (4, 1, 2, 205))  # o1 once (3 placements), o2
        self.assertEqual(totals["exam_orders_in_several_places"], 1)
        by_address = {item["address"]: item for item in result["addresses"]}
        self.assertEqual((by_address["Gata 1"]["exam_orders"], by_address["Gata 2"]["exam_orders"]), (2, 1))  # o1 is in both: 2 + 1 > 2 in total
        self.assertTrue(any("kan överstiga totalen" in note for note in result["notes"]))
        self.assertEqual(sum(item["booked_places"] for item in result["addresses"]), totals["booked_places"])  # places are seats and add up

    def test_bookings_without_a_room_stay_under_their_address_and_are_never_given_a_room(self) -> None:
        result = overview.overview_payload(self.dir, date(2026, 2, 9), date(2026, 2, 10))
        by_address = {item["address"]: item for item in result["addresses"]}
        gata2 = by_address["Gata 2"]
        self.assertEqual([(room["room"], room["label"], room["placements"], room["capacity"]) for room in gata2["rooms"]],
                         [(None, "Gata 2 (sal saknas i uttaget)", 2, None)])
        self.assertEqual((gata2["address_only_placements"], gata2["named_rooms"]), (2, 0))
        self.assertEqual(result["totals"]["address_only_placements"], 2)
        self.assertTrue(any("anger bara adress" in note for note in result["notes"]))
        rooms = {room["label"]: room for room in by_address["Gata 1"]["rooms"]}
        self.assertEqual(set(rooms), {"Gata 1 – Sal 1", "Gata 1 – Sal 2"})  # the unnamed Gata 2 rows did not move here

    def test_rows_without_an_address_are_an_entry_of_their_own_not_dropped(self) -> None:
        result = overview.overview_payload(self.dir, date(2026, 2, 10), date(2026, 2, 10))
        self.assertEqual(result["totals"]["no_address_placements"], 1)
        none = next(item for item in result["addresses"] if item["address"] == "")
        self.assertEqual((none["label"], none["placements"], none["booked_places"]), ("Adress saknas", 1, 7))
        self.assertEqual(result["addresses"][-1]["address"], "")  # listed last

    def test_measures_are_separate_and_cancelled_rows_are_outside_the_sums(self) -> None:
        result = overview.overview_payload(self.dir, date(2026, 2, 9), date(2026, 2, 9), "Gata 1")
        sal1 = next(room for room in result["addresses"][0]["rooms"] if room["room"] == "Sal 1")
        self.assertEqual((sal1["placements"], sal1["cancelled_placements"], sal1["booked_places"], sal1["booked_minutes"]), (2, 1, 160, 300))  # 08-13 once
        self.assertEqual((sal1["peak_places"], sal1["peak_share_of_capacity"]), (160, 1.333))
        self.assertFalse(result["attendance"]["available"])
        self.assertEqual(len(result["bookings"]), 4)  # all bookings of the address, the cancelled one listed too
        self.assertIsNone(overview.overview_payload(self.dir, date(2026, 2, 9), date(2026, 2, 9))["bookings"])

    def test_the_exam_list_gives_each_exam_once_with_where_and_how_many_places(self) -> None:
        result = overview.overview_payload(self.dir, date(2026, 2, 9), date(2026, 2, 9))
        self.assertEqual([item["exam_order_id"] for item in result["exams"]], ["o1", "o2"])
        o1 = result["exams"][0]
        self.assertEqual((o1["booked_places"], o1["place_count"]), (145, 3))
        self.assertEqual(sorted(item["label"] for item in o1["places"]), ["Gata 1 – Sal 1", "Gata 1 – Sal 2", "Gata 2 (sal saknas i uttaget)"])

    def test_periods_outside_the_data_and_bad_requests(self) -> None:
        outside = overview.overview_payload(self.dir, date(2027, 1, 1), date(2027, 1, 2))
        self.assertEqual((outside["totals"]["exam_orders"], outside["addresses"]), (0, []))
        self.assertTrue(any("utanför bokningsunderlaget" in note for note in outside["notes"]))
        partly = overview.overview_payload(self.dir, date(2026, 3, 1), date(2026, 4, 30))
        self.assertTrue(any("okända, inte frånvarande" in note for note in partly["notes"]))
        with self.assertRaisesRegex(ValueError, "senare än slutdatum"):
            overview.overview_payload(self.dir, date(2026, 2, 10), date(2026, 2, 9))
        with self.assertRaisesRegex(ValueError, "Okänd adress"):
            overview.overview_payload(self.dir, date(2026, 2, 9), date(2026, 2, 9), "Ingenstans 9")

    def test_the_address_list_includes_every_address_with_its_unnamed_bookings(self) -> None:
        from tentaoptimering.booking_views import locations_payload
        rows = {item["address"]: item for item in locations_payload(self.dir)["addresses"]}
        self.assertEqual((rows["Gata 2"]["bookings"], rows["Gata 2"]["address_only_bookings"], rows["Gata 2"]["named_rooms"]), (2, 2, 0))
        self.assertEqual(rows[""]["label"], "Adress saknas")
        self.assertEqual(rows["Gata 1"]["named_rooms"], 2)


def _run(storage: AppStorage, run_id: str = "20260101T000000Z-t") -> str:
    folder = storage.runs_dir / run_id
    folder.mkdir(parents=True)
    groups = lambda activity, count: [{"group_id": "g", "participant_count": count, "source_activity_ids": [activity], "count_basis": "registered_count"}]
    (folder / "joint_input.json").write_text(json.dumps({"demands": [
        {"exam_demand_id": "exam-1", "participant_groups": groups("act-1", 90), "course_code": "1AA001", "duration_minutes": 240, "original_slot_id": "2026-02-09T08:00", "movable": True},
        {"exam_demand_id": "exam-9", "participant_groups": groups("act-9", 20), "course_code": "1DD004", "duration_minutes": 180, "original_slot_id": "2026-02-10T08:00", "movable": True},
    ]}), encoding="utf-8")
    (folder / "joint_result.json").write_text(json.dumps({
        "problem_id": "t", "solver": {"outcome": "optimal"}, "coverage": {"technical_placement_complete": True},
        "schedule": [{"exam_demand_id": "exam-1", "slot_id": "2026-02-10T08:00"}, {"exam_demand_id": "exam-9", "slot_id": "2026-02-10T08:00"}],
        "assignments": [{"exam_demand_id": "exam-1", "room_id": "uu-g1-s1", "participants": 90}, {"exam_demand_id": "exam-9", "room_id": "uu-g3-s9", "participants": 20}]}), encoding="utf-8")
    return run_id


class CompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.storage = AppStorage(Path(self._temp.name))
        _write(self.storage.processed_dir)
        self.run = _run(self.storage)

    def test_original_booking_is_set_against_the_simulated_slot_and_rooms(self) -> None:
        result = compare.compare_payload(self.storage, "o1", self.run)
        self.assertEqual(result["status"], "compared")
        demand = result["demands"][0]
        self.assertEqual((demand["original"]["date"], demand["simulated"]["date"], demand["moved"], demand["date_shift_days"]), ("2026-02-09", "2026-02-10", True, 1))
        self.assertFalse(demand["start_changed"])
        self.assertEqual([room["label"] for room in demand["simulated_rooms"]], ["Gata 1 – Sal 1"])
        self.assertEqual(demand["participants"], 90)  # registered, apart from the 145 booked places
        self.assertEqual(result["booked_places"], 145)
        self.assertEqual((demand["booked_addresses"], demand["simulated_addresses"], demand["same_addresses"]), (["Gata 1", "Gata 2"], ["Gata 1"], False))
        self.assertIsNone(demand["same_rooms"])  # one booked room has no name: rooms are not compared
        self.assertEqual(demand["booked_rooms_without_name"], 1)
        self.assertEqual(result["run"], {"outcome": "optimal", "technical_placement_complete": True})
        self.assertTrue(any("olika mått" in note for note in result["notes"]))

    def test_an_address_only_booking_is_compared_on_address_not_on_room(self) -> None:
        result = compare.compare_payload(self.storage, "o4", self.run)
        demand = result["demands"][0]
        self.assertEqual((demand["booked_addresses"], demand["simulated_addresses"], demand["same_addresses"]), (["Gata 2"], ["Gata 3"], False))
        self.assertEqual((demand["rooms_compared"], demand["moved"]), (False, False))

    def test_no_link_and_not_in_run_are_stated_not_guessed(self) -> None:
        no_link = compare.compare_payload(self.storage, "o2", self.run)
        self.assertEqual((no_link["status"], no_link["demands"]), ("no_link", []))
        self.assertIn("Ingen koppling har gissats fram", no_link["reason"])
        self.assertEqual(no_link["reason_code"], "no_candidate_within_coverage")  # Ladok covers the date, so the missing link is a finding
        missing = compare.compare_payload(self.storage, "o7", self.run)  # ambiguous link to activities the run does not contain
        self.assertEqual((missing["status"], missing["link"]["unclear"]), ("not_in_run", True))
        self.assertIn("ingår inte i körningen", missing["reason"])

    def test_outside_ladok_coverage_is_told_apart_from_a_missing_link(self) -> None:
        outside = compare.compare_payload(self.storage, "o8", self.run)  # 25 March, after the Ladok period; no linkage rows at all
        self.assertEqual((outside["status"], outside["reason_code"]), ("no_link", "outside_ladok_coverage"))
        self.assertEqual(outside["link"]["certainties"], ["none_outside_coverage"])
        self.assertFalse(outside["link"]["unclear"])  # not applicable is not unclear

    def test_bad_requests(self) -> None:
        with self.assertRaisesRegex(ValueError, "Okänd tentamensbokning"):
            compare.compare_payload(self.storage, "nope", self.run)
        with self.assertRaises(FileNotFoundError):
            compare.compare_payload(self.storage, "o1", "20260101T000001Z-none")


@unittest.skipUnless((PROCESSED / "bookings.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class RealDataTests(unittest.TestCase):
    def test_overview_matches_an_independent_pandas_count(self) -> None:
        raw = pd.read_csv(PROCESSED / "bookings.csv", encoding="utf-8-sig")
        week = raw[(raw["scheduled_date"] >= "2026-02-09") & (raw["scheduled_date"] <= "2026-02-13")]
        live = week[week["status"] != "Avbokad"]
        result = overview.overview_payload(PROCESSED, date(2026, 2, 9), date(2026, 2, 13))
        self.assertEqual(result["totals"]["placements"], len(live))
        self.assertEqual(result["totals"]["exam_orders"], live["exam_order_id"].nunique())
        self.assertEqual(result["totals"]["booked_places"], int(live["booked_places"].sum()))
        self.assertEqual(sum(item["placements"] for item in result["addresses"]), len(live))  # nothing lost, nothing counted twice per address
        self.assertEqual(result["totals"]["address_only_placements"], int((live["room"].isna() & live["address"].notna()).sum()))
        for item in result["addresses"]:
            self.assertEqual(sum(room["placements"] for room in item["rooms"]), item["placements"])


if __name__ == "__main__":
    unittest.main()
