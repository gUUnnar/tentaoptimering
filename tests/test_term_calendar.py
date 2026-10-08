from __future__ import annotations

from datetime import date
import unittest

from tentaoptimering.term_calendar import CalendarPass, TermCalendar, eligible_slots, generate_calendar_slots


class TermCalendarTests(unittest.TestCase):
    def test_generates_only_configured_weekdays_and_passes(self) -> None:
        calendar = TermCalendar(
            date(2026, 1, 12), date(2026, 1, 18), (1, 3),
            (CalendarPass("morning", "08:00", "12:00"), CalendarPass("afternoon", "13:00", "17:00")), 30,
        )
        slots = generate_calendar_slots(calendar)
        self.assertEqual(len(slots), 4)
        self.assertEqual({slot.scheduled_date.isoweekday() for slot in slots}, {1, 3})

    def test_duration_filters_ineligible_passes(self) -> None:
        calendar = TermCalendar(
            date(2026, 1, 12), date(2026, 1, 12), (1,),
            (CalendarPass("short", "08:00", "09:00"), CalendarPass("long", "13:00", "16:00")), 0,
        )
        self.assertEqual([slot.pass_id for slot in eligible_slots(calendar, 120)], ["long"])


if __name__ == "__main__":
    unittest.main()
