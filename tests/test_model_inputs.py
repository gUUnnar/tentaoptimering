from __future__ import annotations

import unittest

import pandas as pd

from tentaoptimering.model_inputs import (
    build_optimization_inputs,
    load_demand_measure,
    load_poc_policy,
    load_room_register,
)
from tentaoptimering.paths import REPO_ROOT


class OptimizationInputTests(unittest.TestCase):
    def test_demand_measure_is_read_from_parameter_registry(self) -> None:
        self.assertEqual(
            load_demand_measure(REPO_ROOT / "config" / "parameters.toml"), "registered_count"
        )

    def test_official_room_capacity_keeps_temporal_uncertainty(self) -> None:
        rooms = load_room_register(REPO_ROOT / "config" / "room_register.toml")
        bergsbrunnagatan = rooms.loc[
            rooms["reference_room_id"].eq("uu-bergsbrunnagatan-15-sal-1")
        ].iloc[0]
        self.assertEqual(bergsbrunnagatan["capacity_seats"], 206)
        self.assertEqual(int(rooms["capacity_seats"].sum()), 1220)
        self.assertEqual(
            int((rooms["capacity_seats"].notna() & rooms["capacity_scope"].eq("room")).sum()),
            8,
        )
        self.assertEqual(
            bergsbrunnagatan["capacity_temporal_status"],
            "current_published_not_verified_for_booking_period_2025_2026",
        )

    def test_explicit_poc_policy_selects_only_room_scoped_capacities(self) -> None:
        parameter_path = REPO_ROOT / "config" / "parameters.toml"
        policy = load_poc_policy(parameter_path)
        official_rooms = load_room_register(REPO_ROOT / "config" / "room_register.toml")
        bookings = pd.DataFrame(
            {
                "placement_id": ["p1"],
                "exam_order_id": ["order-a"],
                "course_codes": ["ABC123"],
                "scheduled_date": ["2026-01-12"],
                "scheduled_time": ["08:00-12:00"],
                "status": ["Klar"],
                "booked_places": [100],
                "address": ["Bergsbrunnagatan 15"],
                "room": ["Sal 1"],
                "city": ["Uppsala"],
                "location_key": ["bergsbrunnagatan-15|sal-1"],
                "room_key": ["sal-1"],
            }
        )
        ladok = pd.DataFrame(
            {
                "activity_id": ["a1"],
                "course_code": ["ABC123"],
                "start_date": ["2026-01-12"],
                "start_time": ["08:00"],
                "registered_count": [100],
            }
        )

        result = build_optimization_inputs(
            bookings,
            ladok,
            pd.DataFrame({"room_key": []}),
            "registered_count",
            official_rooms,
            policy,
        )

        self.assertTrue(policy.allow_current_published_room_capacity)
        self.assertEqual(len(result.optimization_rooms), 8)
        self.assertEqual(int(result.optimization_rooms["capacity_seats"].sum()), 1179)
        self.assertTrue(result.optimization_rooms["eligible_for_exploratory_capacity_poc"].all())
        self.assertFalse(result.optimization_rooms["eligible_for_operational_scheduling"].any())
        self.assertEqual(
            result.metrics["capacity_optimization_readiness"],
            "ready_for_exploratory_capacity_poc_with_explicit_uncertainty",
        )

    def test_keeps_multi_room_placement_and_excludes_ambiguous_candidates(self) -> None:
        bookings = pd.DataFrame(
            {
                "placement_id": ["p1", "p2", "p3", "p4"],
                "exam_order_id": ["order-a", "order-a", "order-b", "order-c"],
                "course_codes": ["ABC123", "ABC123", "DEF456", "DEF456"],
                "scheduled_date": ["2026-01-12"] * 4,
                "scheduled_time": ["08:00-12:00", "08:00-12:00", "14:00-16:00", "14:00-16:00"],
                "status": ["Klar"] * 4,
                "booked_places": [10, 20, 15, 15],
                "address": ["Adress 1", "Adress 1", "Adress 2", "Adress 3"],
                "room": ["Sal 1", "Sal 2", "Sal 3", "Sal 4"],
                "city": ["Uppsala"] * 4,
                "location_key": ["adress-1|sal-1", "adress-1|sal-2", "adress-2|sal-3", "adress-3|sal-4"],
                "room_key": ["sal-1", "sal-2", "sal-3", "sal-4"],
            }
        )
        ladok = pd.DataFrame(
            {
                "activity_id": ["a1", "a2"],
                "course_code": ["ABC123", "DEF456"],
                "start_date": ["2026-01-12", "2026-01-12"],
                "start_time": ["08:00", "14:00"],
                "registered_count": [25, 30],
            }
        )
        leases = pd.DataFrame({"room_key": ["sal-1", "sal-3"]})

        result = build_optimization_inputs(bookings, ladok, leases, "registered_count")

        self.assertEqual(result.metrics["ladok_activities_unambiguous_candidate"], 1)
        self.assertEqual(result.metrics["ladok_activities_ambiguous_candidates"], 1)
        self.assertEqual(result.metrics["optimization_demands_ready_provisional"], 1)
        self.assertEqual(result.optimization_demands.iloc[0]["activity_id"], "a1")
        self.assertEqual(len(result.optimization_placements), 2)
        self.assertTrue(result.room_inventory["capacity_seats"].isna().all())
        self.assertTrue(
            result.room_inventory["capacity_status"].eq(
                "missing_no_published_room_capacity"
            ).all()
        )

    def test_missing_registered_count_is_not_ready_for_optimization(self) -> None:
        bookings = pd.DataFrame(
            {
                "placement_id": ["p1"],
                "exam_order_id": ["order-a"],
                "course_codes": ["ABC123"],
                "scheduled_date": ["2026-01-12"],
                "scheduled_time": ["08:00-12:00"],
                "status": ["Klar"],
                "booked_places": [10],
                "address": ["Adress 1"],
                "room": ["Sal 1"],
                "city": ["Uppsala"],
                "location_key": ["adress-1|sal-1"],
                "room_key": ["sal-1"],
            }
        )
        ladok = pd.DataFrame(
            {
                "activity_id": ["a1"],
                "course_code": ["ABC123"],
                "start_date": ["2026-01-12"],
                "start_time": ["08:00"],
                "registered_count": [pd.NA],
            }
        )

        result = build_optimization_inputs(bookings, ladok, pd.DataFrame({"room_key": []}), "registered_count")

        self.assertEqual(result.metrics["optimization_demands_ready_provisional"], 0)
        self.assertEqual(
            result.optimization_demands.iloc[0]["demand_input_status"],
            "missing_configured_demand_value",
        )


if __name__ == "__main__":
    unittest.main()
