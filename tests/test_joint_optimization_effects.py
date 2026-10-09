"""Hand-calculated optimisation results: parameters must change what the solver decides.

The adapter tests prove that an input changes. These tests prove that the optimisation result
changes by exactly the amount that can be worked out by hand on a tiny, fully specified case.

Pair case: two exams X and Y, 50 participants, Monday 2026-01-12 08:00-12:00. Two rooms of 60 seats
in different buildings. Room cost 100 öre per seat (6 000 per room), staff pool 1 000, one staff per room
session. Placing both at 08:00 needs two rooms and two staff (2 x 6 000 + 2 x 1 000 = 14 000). Placing Y later
or elsewhere lets one room and one staff serve both (6 000 + 1 000 = 7 000).
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

import pandas as pd

from tentaoptimering.joint_inputs import _digital_requirement, build_real_subset_problem
from tentaoptimering.joint_optimizer import _solver, solve_joint_optimization
from tentaoptimering.parameter_catalog import load_parameter_catalog

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "config" / "joint_parameter_catalog.toml"

BASE = {
    "demand.variation_pct": 0, "demand.rounding": "up",
    "window.earlier_days": 0, "window.later_days": 0,
    "calendar.weekdays": [1, 2, 3, 4, 5], "calendar.start_times": ["08:00", "14:00"],
    "calendar.turnaround_minutes": 30,
    "flex.movable_types": ["ordinarie", "omtenta", "dugga", "hybrid"],
    "rooms.max_rooms_per_exam": 8, "rooms.allow_split_across_buildings": False,
    "staffing.ladder": [{"max_participants": 60, "required_staff": 1}],
    "staffing.preparation_minutes": 0, "staffing.closing_minutes": 0,
    "cost.room_annual_per_seat_ore": 100, "cost.staff_annual_ore": 1000, "cost.staff_session_ore": 0,
    "solver.time_limit_seconds": 10.0, "solver.seed": 3, "solver.workers": 1,
}


def _event(event: str, day: str = "2026-01-12", start: str = "08:00", end: str = "12:00",
           kind: str = "Ordinarie tenta", digital: object = "Nej", count: int = 50) -> dict[str, object]:
    return {
        "exam_event_id": event, "activity_id": f"act-{event}", "demand_input_status": "ready_provisional_ladok_demand",
        "scheduled_date": day, "booking_start_time": start, "scheduled_time": f"{start}-{end}",
        "observed_exam_types": kind, "observed_digital_exam_values": digital, "observed_cities": "Uppsala",
        "demand_value": count, "demand_measure_source_field": "registered_count", "course_code": f"C-{event}",
    }


PAIR = [_event("X"), _event("Y")]
PAIR_OMTENTA = [_event("X", kind="Omtenta"), _event("Y", kind="Omtenta")]
TWO_ROOMS = [("uu-r1", "Adress 1", 60, "all_places_support_e_exam"), ("uu-r2", "Adress 2", 60, "all_places_support_e_exam")]


def _toml(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key} = {_toml(item)}" for key, item in value.items()) + "}"
    raise TypeError(value)


def _solve(directory: Path, events: list[dict[str, object]], rooms: list[tuple], overrides: dict[str, object]):
    pd.DataFrame(events).to_csv(directory / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([
        {"room_id": room, "reference_address": address, "reference_city": "Uppsala", "capacity_seats": cap,
         "digital_capability_status": status, "eligible_for_exploratory_capacity_poc": True,
         "available_from": None, "available_to": None}
        for room, address, cap, status in rooms
    ]).to_csv(directory / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"activity_id": [item["activity_id"] for item in events],
                  "scope_status": ["included"] * len(events)}).to_csv(
        directory / "demand_scope.csv", index=False, encoding="utf-8-sig")
    parameters = {**BASE, **overrides}
    ids = ", ".join(json.dumps(item["exam_event_id"]) for item in {e["exam_event_id"]: e for e in events}.values())
    scenario = directory / "scenario.toml"
    scenario.write_text(
        'schema_version = "joint-real-subset-v1"\n[scenario]\nid = "effect"\ndescription = "d"\n'
        f'[subset]\nplan_area = "Uppsala"\nexam_event_ids = [{ids}]\n[parameters]\n'
        + "\n".join(f"{json.dumps(key)} = {_toml(value)}" for key, value in parameters.items()) + "\n",
        encoding="utf-8",
    )
    problem = build_real_subset_problem(scenario, directory, CATALOG)
    return problem, solve_joint_optimization(problem)


# (case id, parameters it proves, events, rooms, overrides, expected outcome, expected total cost in öre)
CASES = [
    ("base", (), PAIR, TWO_ROOMS, {}, "optimal", 7_000),
    ("start_times_only_08", ("calendar.start_times",), PAIR, TWO_ROOMS, {"calendar.start_times": ["08:00"]}, "optimal", 14_000),
    ("later_day_lets_Y_move", ("window.later_days",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "window.later_days": 1}, "optimal", 7_000),
    ("earlier_day_lets_Y_move", ("window.earlier_days",), [_event("X", "2026-01-13"), _event("Y", "2026-01-13")], TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "window.earlier_days": 1}, "optimal", 7_000),
    ("weekday_policy_blocks_the_move", ("calendar.weekdays",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "window.later_days": 1, "calendar.weekdays": [1]}, "optimal", 14_000),
    ("blocked_range_blocks_the_move", ("calendar.blocked_ranges",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "window.later_days": 1,
      "calendar.blocked_ranges": [{"start": "2026-01-13", "end": "2026-01-13"}]}, "optimal", 14_000),
    ("end_date_blocks_the_move", ("calendar.end_date",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "window.later_days": 1, "calendar.end_date": "2026-01-12"}, "optimal", 14_000),
    ("start_date_removes_monday", ("calendar.start_date",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "window.later_days": 1, "calendar.start_date": "2026-01-13"}, "optimal", 14_000),
    ("earliest_start_removes_08", ("calendar.earliest_start_time",), PAIR, TWO_ROOMS,
     {"calendar.earliest_start_time": "09:00"}, "optimal", 14_000),
    ("latest_end_removes_14", ("calendar.latest_end_time",), PAIR, TWO_ROOMS,
     {"calendar.latest_end_time": "17:00"}, "optimal", 14_000),
    ("fixed_types_cannot_move", ("flex.movable_types",), PAIR_OMTENTA, TWO_ROOMS,
     {"flex.movable_types": ["ordinarie"]}, "optimal", 14_000),
    ("movable_types_can_move", ("flex.movable_types",), PAIR_OMTENTA, TWO_ROOMS, {}, "optimal", 7_000),
    ("turnaround_15_allows_shared_room", ("calendar.turnaround_minutes",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 15}, "optimal", 7_000),
    ("turnaround_30_needs_second_room", ("calendar.turnaround_minutes",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 30}, "optimal", 13_000),
    ("ladder_two_staff_above_25", ("staffing.ladder",), PAIR, TWO_ROOMS,
     {"staffing.ladder": [{"max_participants": 25, "required_staff": 1}, {"max_participants": 60, "required_staff": 2}]},
     "optimal", 8_000),
    ("prep_and_closing_overlap_needs_second_staff", ("staffing.preparation_minutes", "staffing.closing_minutes"), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 15,
      "staffing.preparation_minutes": 30, "staffing.closing_minutes": 30}, "optimal", 8_000),
    # Each of preparation and closing alone must decide the pool. X ends 12:00, Y starts 12:15, same room (turnaround 15).
    # A staff window overlaps when it reaches strictly past the other's start, so 15 minutes touch and 16 overlap.
    ("preparation_15_touches_without_overlap", ("staffing.preparation_minutes",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 15, "staffing.preparation_minutes": 15}, "optimal", 7_000),
    ("preparation_16_overlaps_and_needs_second_staff", ("staffing.preparation_minutes",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 15, "staffing.preparation_minutes": 16}, "optimal", 8_000),
    ("closing_15_touches_without_overlap", ("staffing.closing_minutes",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 15, "staffing.closing_minutes": 15}, "optimal", 7_000),
    ("closing_16_overlaps_and_needs_second_staff", ("staffing.closing_minutes",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00", "12:15"], "calendar.turnaround_minutes": 15, "staffing.closing_minutes": 16}, "optimal", 8_000),
    ("room_cost_doubles", ("cost.room_annual_per_seat_ore",), PAIR, TWO_ROOMS, {"cost.room_annual_per_seat_ore": 200}, "optimal", 13_000),
    ("free_staff_pool", ("cost.staff_annual_ore",), PAIR, TWO_ROOMS, {"cost.staff_annual_ore": 0}, "optimal", 6_000),
    ("staff_session_cost", ("cost.staff_session_ore",), PAIR, TWO_ROOMS, {"cost.staff_session_ore": 500}, "optimal", 8_000),
    ("room_selection_makes_infeasible", ("rooms.selection",), PAIR, TWO_ROOMS,
     {"calendar.start_times": ["08:00"], "rooms.selection": ["uu-r1"]}, "infeasible", None),
    ("variation_makes_exams_too_big_for_one_room", ("demand.variation_pct",), PAIR, TWO_ROOMS,
     {"demand.variation_pct": 30}, "infeasible", None),
    ("variation_with_building_split_costs_two_rooms", ("demand.variation_pct", "rooms.allow_split_across_buildings"), PAIR, TWO_ROOMS,
     {"demand.variation_pct": 30, "rooms.allow_split_across_buildings": True}, "optimal", 14_000),
    ("one_exam_needs_two_buildings_by_default", ("rooms.allow_split_across_buildings",), [_event("Z", count=100)], TWO_ROOMS,
     {}, "infeasible", None),
    ("one_exam_split_across_buildings", ("rooms.allow_split_across_buildings",), [_event("Z", count=100)], TWO_ROOMS,
     {"rooms.allow_split_across_buildings": True}, "optimal", 14_000),
    ("max_rooms_one_blocks_split", ("rooms.max_rooms_per_exam",), [_event("Z", count=100)], TWO_ROOMS,
     {"rooms.allow_split_across_buildings": True, "rooms.max_rooms_per_exam": 1}, "infeasible", None),
    ("allow_split_false_blocks_split", ("rooms.allow_split",), [_event("Z", count=100)], TWO_ROOMS,
     {"rooms.allow_split_across_buildings": True, "rooms.allow_split": False}, "infeasible", None),
    ("partial_digital_room_allowed", ("digital.partial_support_policy",), [_event("E", digital="Ja", count=40)],
     [("paper", "Adress 1", 60, "not_stated"), ("partial", "Adress 2", 60, "supports_e_exam")], {}, "optimal", 7_000),
    ("partial_digital_room_excluded", ("digital.partial_support_policy",), [_event("E", digital="Ja", count=40)],
     [("paper", "Adress 1", 60, "not_stated"), ("partial", "Adress 2", 60, "supports_e_exam")],
     {"digital.partial_support_policy": "exclude"}, "infeasible", None),
    ("unknown_digital_requires_digital_room", ("digital.unknown_demand_policy",), [_event("U", digital=None, count=40)],
     [("paper", "Adress 1", 60, "not_stated")], {}, "infeasible", None),
    ("unknown_digital_assumed_paper", ("digital.unknown_demand_policy",), [_event("U", digital=None, count=40)],
     [("paper", "Adress 1", 60, "not_stated")], {"digital.unknown_demand_policy": "assume_paper"}, "optimal", 7_000),
    ("merged_ja_nej_is_digital_even_when_unknown_is_paper", ("digital.unknown_demand_policy",),
     [_event("M", digital="Ja | Nej", count=40)], [("paper", "Adress 1", 60, "not_stated")],
     {"digital.unknown_demand_policy": "assume_paper"}, "infeasible", None),
]


class OptimizationEffectTests(unittest.TestCase):
    def test_hand_calculated_results(self) -> None:
        for case_id, _params, events, rooms, overrides, outcome, cost in CASES:
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as temp:
                _problem, result = _solve(Path(temp), events, rooms, overrides)
                self.assertEqual(result.solver.outcome, outcome, case_id)
                if cost is not None:
                    self.assertEqual(result.costs.comparable_total_cost_ore, cost, case_id)
                if outcome == "infeasible":
                    self.assertFalse(result.coverage.technical_placement_complete)
                    self.assertEqual(result.assignments, ())

    def test_every_implemented_parameter_is_proven_on_an_optimisation_result(self) -> None:
        implemented = {
            item.parameter_id for item in load_parameter_catalog(CATALOG).parameters if item.engine_support == "implemented"
        }
        covered = {parameter for _id, params, *_rest in CASES for parameter in params}
        covered |= {"demand.rounding", "demand.measure", "solver.time_limit_seconds", "solver.seed", "solver.workers", "solver.deterministic"}
        self.assertEqual(implemented - covered, set(), "implemented parameters without a result-level test")

    def test_rounding_changes_the_placed_participants(self) -> None:
        totals = {}
        for rounding in ("up", "down", "nearest"):
            with tempfile.TemporaryDirectory() as temp:
                _problem, result = _solve(Path(temp), PAIR, TWO_ROOMS, {"demand.variation_pct": 3, "demand.rounding": rounding})
                self.assertTrue(result.coverage.technical_placement_complete)
                totals[rounding] = result.coverage.participants_assigned_to_rooms
        self.assertEqual(totals, {"up": 104, "down": 102, "nearest": 104})  # 50 x 1.03 = 51.5 per exam

    def test_unsupported_demand_measure_never_reaches_the_solver(self) -> None:
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "registered_count"):
            _solve(Path(temp), PAIR, TWO_ROOMS, {"demand.measure": "attendance"})

    def test_solver_parameters_reach_cp_sat(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            problem, _result = _solve(Path(temp), PAIR, TWO_ROOMS, {
                "solver.time_limit_seconds": 7.5, "solver.seed": 99, "solver.workers": 4, "solver.deterministic": True,
            })
        solver = _solver(problem)
        self.assertEqual(solver.parameters.max_time_in_seconds, 7.5)
        self.assertEqual(solver.parameters.random_seed, 99)
        self.assertEqual(solver.parameters.num_search_workers, 4)
        self.assertTrue(solver.parameters.interleave_search)
        with tempfile.TemporaryDirectory() as temp:
            problem, _result = _solve(Path(temp), PAIR, TWO_ROOMS, {"solver.workers": 4, "solver.deterministic": False})
        self.assertFalse(_solver(problem).parameters.interleave_search)

    def test_historical_occasion_outside_settings_counts_as_a_change(self) -> None:
        events = [_event("X", start="09:00", end="13:00"), _event("Y")]
        with tempfile.TemporaryDirectory() as temp:
            problem, result = _solve(Path(temp), events, TWO_ROOMS, {})
        schedule = {row["exam_demand_id"]: row for row in result.schedule}
        self.assertEqual(schedule["exam-X"]["original_start_minute"], 9 * 60)
        self.assertNotEqual(schedule["exam-X"]["slot_id"], "2026-01-12T09:00")
        self.assertGreaterEqual(result.changed_exam_demands, 1)
        self.assertEqual(result.solver.outcome, "optimal")


class DigitalValueParsingTests(unittest.TestCase):
    CASES = [
        (["Ja | Nej"], "e_exam", "observed_mixed"),
        (["Nej | Ja"], "e_exam", "observed_mixed"),
        (["ja, nej"], "e_exam", "observed_mixed"),
        (["Ja", "Nej"], "e_exam", "observed_mixed"),
        (["Ja"], "e_exam", "observed_ja"),
        ([" JA "], "e_exam", "observed_ja"),
        (["Nej"], "paper", "observed_nej"),
        (["Ja | ?"], "e_exam", "observed_mixed"),
    ]

    def test_merged_and_mixed_values_are_never_paper_under_either_policy(self) -> None:
        for raw, requirement, basis in self.CASES:
            for policy in ("require_e_exam", "assume_paper"):
                with self.subTest(raw=raw, policy=policy):
                    self.assertEqual(
                        _digital_requirement(pd.Series(raw, dtype=object), {"digital.unknown_demand_policy": policy}),
                        (requirement, basis),
                    )

    def test_missing_or_unrecognised_values_follow_the_explicit_policy_and_are_flagged(self) -> None:
        for raw in ([None], [""], ["Okänd"], ["Nej | ?"]):
            self.assertEqual(
                _digital_requirement(pd.Series(raw, dtype=object), {"digital.unknown_demand_policy": "require_e_exam"}),
                ("e_exam", "unobserved"),
            )
            self.assertEqual(
                _digital_requirement(pd.Series(raw, dtype=object), {"digital.unknown_demand_policy": "assume_paper"}),
                ("paper", "unobserved"),
            )


if __name__ == "__main__":
    unittest.main()
