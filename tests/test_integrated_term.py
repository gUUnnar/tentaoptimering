from __future__ import annotations

from datetime import date
import unittest

from tentaoptimering.integrated_term import AggregateStaffing, IntegratedDemand, IntegratedRoom, solve_integrated_term
from tentaoptimering.term_calendar import CalendarPass, TermCalendar


class IntegratedTermTests(unittest.TestCase):
    def test_calendar_candidate_limit_is_explicit_and_reproducible(self) -> None:
        result = solve_integrated_term(
            demands=(IntegratedDemand("e1", 20, 60, "Uppsala"),),
            rooms=(IntegratedRoom("r1", 20, "Uppsala", 1),),
            calendar=TermCalendar(date(2026, 1, 12), date(2026, 1, 16), (1, 2, 3, 4, 5), (CalendarPass("day", "08:00", "12:00"),), 0),
            staffing=AggregateStaffing(1, 1),
            max_calendar_slots_per_demand=2,
        )
        self.assertIn(result.assignments[0]["slot_id"], {"2026-01-12-day", "2026-01-16-day"})

    def test_places_every_participant_and_optimizes_rooms_with_staff_pool(self) -> None:
        result = solve_integrated_term(
            demands=(IntegratedDemand("e1", 20, 120, "Uppsala"), IntegratedDemand("e2", 20, 90, "Uppsala")),
            rooms=(IntegratedRoom("large", 40, "Uppsala", 350000), IntegratedRoom("small-a", 20, "Uppsala", 40000), IntegratedRoom("small-b", 20, "Uppsala", 40000)),
            calendar=TermCalendar(date(2026, 1, 12), date(2026, 1, 12), (1,), (CalendarPass("morning", "08:00", "12:00"),), 30),
            staffing=AggregateStaffing(1, 120000),
        )
        self.assertIn(result.status, {"optimal", "feasible"})
        self.assertEqual(sum(item["participants"] for item in result.assignments), 40)
        self.assertEqual(result.annual_room_cost_ore, 80000)
        self.assertEqual(result.staff_pool_size, 2)
        self.assertEqual(result.objective_ore, 320000)

    def test_enforces_explicit_course_conflicts_and_room_rules(self) -> None:
        calendar = TermCalendar(
            date(2026, 1, 12), date(2026, 1, 12), (1,),
            (CalendarPass("am", "08:00", "10:00"), CalendarPass("pm", "10:00", "12:00")), 0,
        )
        result = solve_integrated_term(
            demands=(
                IntegratedDemand("first", 10, 60, "Uppsala", course_code="COURSE", digital_requirement="e_exam"),
                IntegratedDemand("second", 10, 60, "Uppsala", course_code="COURSE", digital_requirement="e_exam"),
            ),
            rooms=(
                IntegratedRoom("offline", 10, "Uppsala", 1, digital_capabilities=frozenset({"paper"})),
                IntegratedRoom("online", 10, "Uppsala", 1, digital_capabilities=frozenset({"e_exam"}), available_slot_ids=frozenset({"2026-01-12-am", "2026-01-12-pm"})),
            ),
            calendar=calendar, staffing=AggregateStaffing(1, 1),
        )

        self.assertIn(result.status, {"optimal", "feasible"})
        self.assertEqual({item["room_id"] for item in result.assignments}, {"online"})
        self.assertEqual(len({item["slot_id"] for item in result.assignments}), 2)


if __name__ == "__main__":
    unittest.main()
