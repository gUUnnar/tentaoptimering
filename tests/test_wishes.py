"""The business's wishes (requested date, two reserve dates, reason) are carried from the booking export, kept apart from the booking and never interpreted."""

from __future__ import annotations

from pathlib import Path
import unittest

import pandas as pd

from tentaoptimering.wishes import build_exam_wishes, date_rank, reason_has_letters, summarize_wishes

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"


def _bookings(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["exam_order_id", "scheduled_date", "scheduled_time", "requested_date", "reserve_date_1", "reserve_date_2", "no_reserve_date_reason"])


def _events(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["exam_event_id", "exam_order_id", "scheduled_date", "scheduled_time"])


class WishRowTests(unittest.TestCase):
    def setUp(self) -> None:
        bookings = _bookings([
            ("o1", "2026-02-09", "08:00-12:00", "2026-02-09", "2026-02-10", "2026-02-11", None),  # booked on the first choice
            ("o1", "2026-02-09", "08:00-12:00", "2026-02-09", "2026-02-10", "2026-02-11", None),  # second room of the same exam
            ("o2", "2026-02-10", "08:00-12:00", "2026-02-09", "2026-02-10", None, None),  # booked on reserve 1
            ("o3", "2026-02-13", "08:00-12:00", "2026-02-09", None, None, "Alla kurser tentar i augusti"),  # booked on a date nobody wished
            ("o4", "2026-02-09", "08:00-12:00", "2026-02-09", None, None, None),  # no reserve and no reason
            ("o5", "2026-02-09", "08:00-12:00", "2026-02-09", None, None, " ."),  # a reason that has no letters
            ("o6", None, None, "2026-02-09", None, None, None),  # cancelled: no booked date
        ])
        events = _events([("e1", "o1", "2026-02-09", "08:00-12:00"), ("e2", "o2", "2026-02-10", "08:00-12:00"), ("e3", "o3", "2026-02-13", "08:00-12:00"),
                          ("e4", "o4", "2026-02-09", "08:00-12:00"), ("e5", "o5", "2026-02-09", "08:00-12:00"), ("e6", "o6", None, None)])
        self.wishes = build_exam_wishes(bookings, events).set_index("exam_event_id")

    def test_one_row_per_exam_event_even_when_the_exam_has_several_booking_rows(self) -> None:
        self.assertEqual(len(self.wishes), 6)
        self.assertTrue(self.wishes.index.is_unique)

    def test_the_rank_of_the_booked_date_among_the_wishes(self) -> None:
        self.assertEqual(self.wishes["booked_date_rank"].to_dict(), {"e1": "first", "e2": "reserve_1", "e3": "other", "e4": "first", "e5": "first", "e6": "not_booked"})

    def test_status_tells_reserves_reason_or_neither_without_interpreting_the_reason(self) -> None:
        self.assertEqual(self.wishes["wish_status"].to_dict(), {"e1": "reserves_given", "e2": "reserves_given", "e3": "reason_only", "e4": "neither", "e5": "reason_only", "e6": "neither"})
        self.assertEqual(self.wishes.loc["e3", "no_reserve_date_reason"], "Alla kurser tentar i augusti")  # kept as written

    def test_a_reason_without_letters_is_a_fact_about_the_text_not_a_reading_of_it(self) -> None:
        self.assertFalse(reason_has_letters("."))
        self.assertFalse(reason_has_letters(None))
        self.assertTrue(reason_has_letters("Hemtenta"))
        self.assertFalse(bool(self.wishes.loc["e5", "reason_has_letters"]))

    def test_summary_counts_each_order_once(self) -> None:
        summary = summarize_wishes(self.wishes.reset_index())
        self.assertEqual((summary["events"], summary["orders"]), (6, 6))
        self.assertEqual(summary["status"], {"reserves_given": 2, "reason_only": 2, "neither": 2, "no_request": 0})
        self.assertEqual(summary["reason_without_letters"], 1)
        self.assertEqual(summary["booked_date_rank"], {"first": 3, "reserve_1": 1, "reserve_2": 0, "other": 1})
        self.assertEqual(summary["not_booked_events"], 1)

    def test_conflicting_wishes_inside_one_order_are_flagged_not_averaged(self) -> None:
        bookings = _bookings([("o1", "2026-02-09", "08:00-12:00", "2026-02-09", None, None, None), ("o1", "2026-02-09", "08:00-12:00", "2026-02-12", None, None, None)])
        wishes = build_exam_wishes(bookings, _events([("e1", "o1", "2026-02-09", "08:00-12:00")]))
        self.assertTrue(bool(wishes.loc[0, "wish_conflict"]))

    def test_date_rank_prefers_the_earlier_wish_when_a_date_is_wished_twice(self) -> None:
        self.assertEqual(date_rank("2026-02-09", ("2026-02-09", "2026-02-09", None)), "first")
        self.assertEqual(date_rank("2026-02-12", ("2026-02-09", None, None)), "other")


@unittest.skipUnless((PROCESSED / "exam_wishes.csv").is_file() and (PROCESSED / "bookings.csv").is_file(), "kräver lokalt genererat underlag (data/processed)")
class RealDataTests(unittest.TestCase):
    def test_the_prepared_wishes_match_an_independent_count_over_the_prepared_bookings(self) -> None:
        bookings = pd.read_csv(PROCESSED / "bookings.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
        wishes = pd.read_csv(PROCESSED / "exam_wishes.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
        orders = bookings.groupby("exam_order_id").agg(r1=("reserve_date_1", lambda s: any(v.strip() for v in s)), r2=("reserve_date_2", lambda s: any(v.strip() for v in s)),
                                                       reason=("no_reserve_date_reason", lambda s: any(v.strip() for v in s)))
        with_reserve = int((orders["r1"] | orders["r2"]).sum())
        neither = int((~(orders["r1"] | orders["r2"]) & ~orders["reason"]).sum())
        summary = summarize_wishes(wishes.assign(reason_has_letters=wishes["reason_has_letters"] == "True", wish_conflict=wishes["wish_conflict"] == "True",
                                                 order_event_count=pd.to_numeric(wishes["order_event_count"])))
        self.assertEqual(summary["status"]["reserves_given"], with_reserve)
        self.assertEqual(summary["status"]["neither"], neither)
        self.assertEqual(summary["orders"], bookings["exam_order_id"].nunique())
        self.assertEqual(summary["orders_with_conflicting_wishes"], 0)
        # Every wish row belongs to an exam event of the prepared underlay.
        events = pd.read_csv(PROCESSED / "exam_events.csv", encoding="utf-8-sig", dtype=str)
        self.assertEqual(set(wishes["exam_event_id"]), set(events["exam_event_id"]))


if __name__ == "__main__":
    unittest.main()
