"""The read-only booking views: one room over a period, one booked exam, search, coverage and what is not known.

Synthetic booking rows give exact expectations (overlap, cancelled rows, address-only bookings, missing capacity). A test
against the locally prepared data compares counts with an independent pandas count and needs no optimisation run.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

import pandas as pd

from tentaoptimering import booking_views as views
from tentaoptimering.app_storage import AppStorage
from tentaoptimering.api import create_app

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
COLUMNS = ["placement_id", "exam_order_id", "course_codes", "course_name", "exam_type", "digital_exam", "scheduled_date", "scheduled_time",
           "address", "room", "location_key", "booked_places", "status"]
S1, S2, ADDR = "a-1|sal-1", "a-1|sal-2", "a-1"
# placement, order, course, name, type, digital, date, time, address, room, location key, places, status
ROWS = [
    ("p1", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "A 1", "Sal 1", S1, "100", "Klar"),
    ("p2", "o2", "1BB002", "Algebra", "Omtenta", "Nej", "2026-02-09", "10:00-14:00", "A 1", "Sal 1", S1, "60", "Klar"),
    ("p3", "o3", "1CC003", "Fysik", "Ordinarie tenta", "Ja", "2026-02-09", "15:00-17:00", "A 1", "Sal 1", S1, "30", "Avbokad"),
    ("p4", "o1", "1AA001", "Analys", "Ordinarie tenta", "Nej", "2026-02-09", "08:00-12:00", "A 1", "Sal 2", S2, "40", "Klar"),
    ("p5", "o4", "1DD004", "Kemi", "Ordinarie tenta", "Nej", "2026-02-10", "08:00-11:00", "A 1", "", ADDR, "25", "Klar"),
    ("p6", "o5", "1EE005", "Biologi", "Ordinarie tenta", "Nej", "2026-03-20", "08:00-11:00", "A 1", "Sal 1", S1, "10", "Klar"),
    ("p7", "o6", "Extern", "Ahmed", "", "", "", "-", "", "", "", "0", "Avbokad"),
]
ROOMS = [("uu-a-1-sal-1", S1, "Sal 1", "120"), ("uu-a-1-sal-2", S2, "Sal 2", ""), ("", ADDR, "", ""), ("uu-a-1-x", ADDR, "X", "41")]
LINKS = [("p1", "a1", "single_candidate"), ("p2", "a2", "ambiguous_candidates"), ("p2", "a3", "ambiguous_candidates"), ("p4", "", "no_candidate")]
LADOK_START_DATES = ["2026-02-01", "2026-03-31"]  # the period the Ladok source covers


def _write(folder: Path, rows: list[tuple] | None = ROWS, rooms: bool = True) -> None:
    if rows is not None:
        pd.DataFrame(rows, columns=COLUMNS).to_csv(folder / "bookings.csv", index=False, encoding="utf-8-sig")
    if rooms:
        pd.DataFrame(ROOMS, columns=["room_id", "location_key", "reference_room_name", "capacity_seats"]).to_csv(folder / "room_inventory.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(LINKS, columns=["placement_id", "activity_id", "candidate_status"]).to_csv(folder / "candidate_linkage.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame({"start_date": LADOK_START_DATES}).to_csv(folder / "ladok_activities.csv", index=False, encoding="utf-8-sig")


class ViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)
        _write(self.dir)

    def test_coverage_counts_what_is_missing_and_says_attendance_is_unknown(self) -> None:
        coverage = views.coverage_payload(self.dir)
        self.assertEqual((coverage["first"], coverage["last"], coverage["rows"], coverage["without_date"], coverage["cancelled"]),
                         ("2026-02-09", "2026-03-20", 7, 1, 2))
        self.assertFalse(coverage["attendance"]["available"])
        self.assertIn("okänd", coverage["attendance"]["note"])

    def test_locations_are_rooms_or_addresses_and_cancelled_rows_do_not_count(self) -> None:
        rows = {item["location_key"]: item for item in views.locations_payload(self.dir)["locations"]}
        self.assertEqual(set(rows), {S1, S2, ADDR})
        self.assertEqual((rows[S1]["bookings"], rows[S1]["capacity"], rows[S1]["room"]), (3, 120, "Sal 1"))  # p3 is cancelled
        self.assertEqual((rows[S2]["capacity"], rows[S2]["bookings"]), (None, 1))  # the register has no capacity for it
        self.assertEqual((rows[ADDR]["room"], rows[ADDR]["capacity"]), (None, None))  # an address is not given a room's capacity
        self.assertIn("sal saknas i uttaget", rows[ADDR]["label"])
        self.assertEqual(rows[ADDR]["identification"], "address_only")

    def test_a_room_over_a_week_counts_overlap_once_and_leaves_out_cancelled_time(self) -> None:
        result = views.location_payload(self.dir, S1, date(2026, 2, 9), date(2026, 2, 15))
        summary = result["summary"]
        self.assertEqual((summary["bookings"], summary["cancelled_bookings"], summary["exam_orders"], summary["days_with_bookings"]), (2, 1, 2, 1))
        self.assertEqual(summary["booked_minutes"], 360)  # 08:00-14:00, the 10:00-12:00 overlap counted once
        self.assertEqual((summary["booked_places"], summary["peak_places"]), (160, 160))
        self.assertEqual((summary["capacity"], summary["peak_share_of_capacity"]), (120, 1.333))  # over capacity is shown, not hidden
        self.assertEqual([item["placement_id"] for item in result["bookings"]], ["p1", "p2", "p3"])  # cancelled is listed, marked
        self.assertTrue(result["bookings"][2]["cancelled"])
        self.assertEqual(result["bookings"][0]["seat_share"], 0.833)
        self.assertFalse(result["attendance"]["available"])
        self.assertEqual(set(result["measures"]), {"booked_time", "booked_places", "seat_share", "attendance"})

    def test_findings_are_counted_without_explaining_them_and_capacity_conflicts_are_flagged(self) -> None:
        room = views.location_payload(self.dir, S1, date(2026, 2, 9), date(2026, 2, 15))
        self.assertEqual(room["data_quality"]["identification"], {"room_matched": 2})
        self.assertTrue(any("Högsta samtidiga bokning överstiger" in note for note in room["notes"]))  # 160 booked at once in a room of 120
        address = views.location_payload(self.dir, ADDR, date(2026, 2, 9), date(2026, 2, 15))
        self.assertEqual(address["data_quality"]["flags"], {"room_missing": 1})
        self.assertEqual(address["bookings"][0]["identification"], "address_only")
        self.assertEqual(address["bookings"][0]["place_label"], "A 1 (sal saknas i uttaget)")
        self.assertNotIn("adressbokning", " ".join(address["notes"]).lower())  # no explanation of why the room is missing is offered
        self.assertEqual(address["bookings"][0]["flags"], ["room_missing"])

    def test_a_place_without_capacity_gives_no_share_and_says_why(self) -> None:
        result = views.location_payload(self.dir, ADDR, date(2026, 2, 9), date(2026, 2, 15))
        self.assertIsNone(result["summary"]["capacity"])
        self.assertIsNone(result["summary"]["peak_share_of_capacity"])
        self.assertIsNone(result["bookings"][0]["seat_share"])
        self.assertTrue(any("ingen sal har antagits" in note for note in result["notes"]))

    def test_periods_outside_or_partly_outside_the_data_are_not_empty_rooms(self) -> None:
        outside = views.location_payload(self.dir, S1, date(2027, 1, 1), date(2027, 1, 7))
        self.assertEqual(outside["bookings"], [])
        self.assertTrue(any("utanför bokningsunderlaget" in note for note in outside["notes"]))
        partly = views.location_payload(self.dir, S1, date(2026, 3, 15), date(2026, 4, 30))
        self.assertTrue(any("okänd, inte tom" in note for note in partly["notes"]))
        self.assertEqual(partly["summary"]["bookings"], 1)

    def test_bad_requests_say_what_is_wrong(self) -> None:
        with self.assertRaisesRegex(ValueError, "senare än slutdatum"):
            views.location_payload(self.dir, S1, date(2026, 2, 9), date(2026, 2, 1))
        with self.assertRaisesRegex(ValueError, "Okänd lokal"):
            views.location_payload(self.dir, "x|y", date(2026, 2, 9), date(2026, 2, 10))
        with self.assertRaisesRegex(ValueError, "Okänd tentamensbokning"):
            views.exam_payload(self.dir, "nope")
        with self.assertRaisesRegex(ValueError, "sökord"):
            views.search_exams(self.dir, "  ")

    def test_an_exam_shows_all_its_rooms_and_flags_unclear_ladok_links(self) -> None:
        exam = views.exam_payload(self.dir, "o1")
        self.assertEqual([(item["room"], item["start"], item["end"], item["booked_places"]) for item in exam["placements"]],
                         [("Sal 1", "08:00", "12:00", 100), ("Sal 2", "08:00", "12:00", 40)])
        self.assertEqual((exam["booked_places"], exam["rooms"]), (140, 2))
        self.assertTrue(exam["link_unclear"])  # p4 has no candidate although Ladok covers the date
        self.assertEqual(exam["link_certainties"], ["none_within_coverage", "unique"])
        self.assertEqual(views.exam_payload(self.dir, "o2")["placements"][0]["link_certainty"], "ambiguous")

    def test_search_finds_by_id_course_and_name_and_by_date(self) -> None:
        self.assertEqual([item["exam_order_id"] for item in views.search_exams(self.dir, "1bb")["exams"]], ["o2"])
        self.assertEqual([item["exam_order_id"] for item in views.search_exams(self.dir, "kemi")["exams"]], ["o4"])
        self.assertEqual([item["exam_order_id"] for item in views.search_exams(self.dir, "o1")["exams"]], ["o1"])
        by_date = views.search_exams(self.dir, "", date(2026, 2, 10), date(2026, 2, 10))
        self.assertEqual([item["exam_order_id"] for item in by_date["exams"]], ["o4"])
        found = views.search_exams(self.dir, "1AA001")["exams"][0]
        self.assertEqual((found["placements"], found["rooms"], found["booked_places"]), (2, 2, 140))
        self.assertTrue(views.search_exams(self.dir, "1CC003")["exams"][0]["all_cancelled"])

    def test_missing_data_is_an_error_not_an_empty_answer(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(views.BookingDataMissing):
                views.locations_payload(Path(empty))

    def test_the_register_may_be_missing_and_the_views_still_work(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            _write(Path(folder), rooms=False)
            result = views.location_payload(Path(folder), S1, date(2026, 2, 9), date(2026, 2, 15))
            self.assertIsNone(result["summary"]["capacity"])
            self.assertEqual(result["bookings"][0]["link_certainty"], "not_assessed")
            self.assertEqual(result["bookings"][0]["identification"], "room_named_not_in_register")  # without a register no room is matched


class RouteTests(unittest.TestCase):
    def test_the_routes_answer_over_http_and_refuse_bad_input_with_a_reason(self) -> None:
        import socket
        import threading
        import time
        import uvicorn
        with tempfile.TemporaryDirectory() as folder:
            storage = AppStorage(Path(folder))
            _write(storage.processed_dir)
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(create_app(Path(folder)), host="127.0.0.1", port=port, log_level="error"))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            self.addCleanup(lambda: (setattr(server, "should_exit", True), thread.join(5)))
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.05)
            base = f"http://127.0.0.1:{port}/api/bookings"

            def get(path: str) -> tuple[int, dict]:
                try:
                    with urlopen(base + path) as response:
                        return response.status, json.load(response)
                except HTTPError as error:
                    with error:
                        return error.code, json.load(error)

            self.assertEqual(get("/locations")[0], 200)
            status, body = get("/location?location=a-1%7Csal-1&date_from=2026-02-09&date_to=2026-02-15")
            self.assertEqual((status, body["summary"]["bookings"]), (200, 2))
            self.assertEqual(get("/location?location=a-1%7Csal-1&date_from=2026-02-15&date_to=2026-02-09")[0], 422)
            self.assertEqual(get("/location?location=a-1%7Csal-1&date_from=bad&date_to=2026-02-09")[0], 422)
            self.assertEqual(get("/exams?q=Kemi")[1]["exams"][0]["exam_order_id"], "o4")
            self.assertEqual(get("/exams/o1")[1]["booked_places"], 140)
            self.assertEqual(get("/exams/nope")[0], 422)
            status, body = get("/overview?date_from=2026-02-09&date_to=2026-02-15")
            self.assertEqual((status, body["totals"]["exam_orders"]), (200, 3))
            status, body = get("/overview?date_from=2026-02-09&date_to=2026-02-15&address=A%201")
            self.assertEqual((status, len(body["bookings"])), (200, 5))
            self.assertEqual(get("/overview?date_from=2026-02-09&date_to=2026-02-15&address=Nowhere")[0], 422)
            self.assertEqual(get("/overview?date_from=2026-02-16&date_to=2026-02-15")[0], 422)
            self.assertEqual(get("/exams/o1/compare?run=20260101T000000Z-none")[0], 404)


@unittest.skipUnless((PROCESSED / "bookings.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class RealDataTests(unittest.TestCase):
    def test_counts_match_an_independent_pandas_count(self) -> None:
        raw = pd.read_csv(PROCESSED / "bookings.csv", encoding="utf-8-sig")
        coverage = views.coverage_payload(PROCESSED)
        self.assertEqual((coverage["rows"], coverage["cancelled"]), (len(raw), int((raw["status"] == "Avbokad").sum())))
        dated = raw[raw["scheduled_date"].notna()]
        self.assertEqual((coverage["first"], coverage["last"]), (dated["scheduled_date"].min(), dated["scheduled_date"].max()))
        key = "bergsbrunnagatan-15|sal-1"
        week = raw[(raw["location_key"] == key) & (raw["scheduled_date"] >= "2026-02-09") & (raw["scheduled_date"] <= "2026-02-15")]
        result = views.location_payload(PROCESSED, key, date(2026, 2, 9), date(2026, 2, 15))
        self.assertEqual(len(result["bookings"]), len(week))
        self.assertEqual(result["summary"]["booked_places"], int(week[week["status"] != "Avbokad"]["booked_places"].sum()))
        self.assertEqual(result["summary"]["capacity"], 206)
        order = result["bookings"][0]["exam_order_id"]
        self.assertEqual(len(views.exam_payload(PROCESSED, order)["placements"]), int((raw["exam_order_id"] == order).sum()))


if __name__ == "__main__":
    unittest.main()
