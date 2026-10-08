from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import pandas as pd

from tentaoptimering.optimizer_config import load_scenario_config
from tentaoptimering.optimizer_model import solve_capacity_scenario
from tentaoptimering.optimizer_validation import validate_solution
from tentaoptimering.paths import REPO_ROOT


def _demands(values: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "demand_id": [f"d{index}" for index in range(len(values))],
            "course_code": [f"C{index}" for index in range(len(values))],
            "scheduled_date": ["2026-01-12"] * len(values),
            "booking_start_time": ["08:00"] * len(values),
            "scheduled_time": ["08:00-09:00"] * len(values),
            "demand_value": values,
            "demand_input_status": ["ready_provisional_ladok_demand"] * len(values),
            "observed_cities": ["Uppsala"] * len(values),
        }
    )


def _rooms(capacities: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "room_id": [f"r{index}" for index in range(len(capacities))],
            "capacity_seats": capacities,
            "reference_city": ["Uppsala"] * len(capacities),
            "eligible_for_exploratory_capacity_poc": [True] * len(capacities),
        }
    )


def _config(room_count: int, **changes: object):
    base = load_scenario_config(REPO_ROOT / "config" / "scenarios" / "reference.toml")
    defaults = {
        "allowed_room_ids": tuple(f"r{index}" for index in range(room_count)),
        "max_rooms_per_exam": room_count,
        "max_time_seconds": 5.0,
    }
    defaults.update(changes)
    return replace(base, **defaults)


class OptimizerTests(unittest.TestCase):
    def test_capacity_is_never_exceeded_and_unplaced_is_visible(self) -> None:
        result = solve_capacity_scenario(
            _demands([40, 40]),
            _rooms([60]),
            pd.DataFrame(columns=["demand_id", "room_id"]),
            _config(1),
        )

        self.assertIn(result.solver_status, {"optimal", "feasible"})
        self.assertEqual(result.metrics["unplaced_exam_count"], 1)
        self.assertLessEqual(result.assignments["allocated_participants"].sum(), 60)
        self.assertEqual(result.metrics["maximum_aggregate_capacity_shortfall"], 20)
        self.assertEqual(
            result.metrics["full_placement_feasibility"],
            "proven_impossible_by_aggregate_capacity_at_fixed_times",
        )

    def test_co_location_can_share_capacity(self) -> None:
        result = solve_capacity_scenario(
            _demands([20, 20]),
            _rooms([60]),
            pd.DataFrame(columns=["demand_id", "room_id"]),
            _config(1),
        )

        self.assertEqual(result.metrics["placed_exam_count"], 2)
        self.assertEqual(result.assignments["allocated_participants"].sum(), 40)

    def test_disabling_co_location_prevents_overlap(self) -> None:
        result = solve_capacity_scenario(
            _demands([20, 20]),
            _rooms([60]),
            pd.DataFrame(columns=["demand_id", "room_id"]),
            _config(1, allow_co_location=False),
        )

        self.assertEqual(result.metrics["unplaced_exam_count"], 1)

    def test_split_demand_uses_multiple_rooms(self) -> None:
        demands = _demands([80])
        rooms = _rooms([50, 40])
        config = _config(2)
        result = solve_capacity_scenario(
            demands,
            rooms,
            pd.DataFrame(columns=["demand_id", "room_id"]),
            config,
        )

        self.assertEqual(result.metrics["unplaced_exam_count"], 0)
        self.assertEqual(len(result.assignments), 2)
        self.assertEqual(result.assignments["allocated_participants"].sum(), 80)
        validation = validate_solution(
            demands, rooms, result.assignments, result.unplaced, config
        )
        self.assertTrue(validation["valid"])

    def test_independent_validator_rejects_capacity_violation(self) -> None:
        demands = _demands([40])
        rooms = _rooms([60])
        config = _config(1)
        result = solve_capacity_scenario(
            demands,
            rooms,
            pd.DataFrame(columns=["demand_id", "room_id"]),
            config,
        )
        tampered = result.assignments.copy()
        tampered.loc[:, "allocated_participants"] = 61

        with self.assertRaisesRegex(ValueError, "Lösningsvalideringen misslyckades"):
            validate_solution(demands, rooms, tampered, result.unplaced, config)

    def test_time_flexibility_changes_feasible_solution_reproducibly(self) -> None:
        config = _config(
            1,
            allow_co_location=False,
            start_time_shift_minutes=60,
            start_time_step_minutes=60,
        )
        inputs = (
            _demands([40, 40]),
            _rooms([60]),
            pd.DataFrame(columns=["demand_id", "room_id"]),
            config,
        )

        first = solve_capacity_scenario(*inputs)
        second = solve_capacity_scenario(*inputs)

        self.assertEqual(first.metrics["unplaced_exam_count"], 0)
        self.assertEqual(first.metrics["full_placement_feasibility"], "demonstrated_feasible")
        self.assertEqual(
            first.assignments.sort_values("demand_id").reset_index(drop=True).to_dict("records"),
            second.assignments.sort_values("demand_id").reset_index(drop=True).to_dict("records"),
        )


if __name__ == "__main__":
    unittest.main()
