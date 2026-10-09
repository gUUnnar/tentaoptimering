"""Every parameter marked `implemented` must visibly change the model, and none may disappear."""

from __future__ import annotations

from datetime import date
import importlib
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

import pandas as pd

from tentaoptimering.joint_contract import _jsonable
from tentaoptimering.joint_inputs import build_real_subset_problem
from tentaoptimering.joint_optimizer import solve_joint_optimization
from tentaoptimering.parameter_catalog import load_parameter_catalog

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "config" / "joint_parameter_catalog.toml"

# Identifiers of the pre-contract registry (config/parameters.toml and the term-engine bindings).
LEGACY_REGISTRY_IDS = {
    "date_shift_earlier_days", "date_shift_later_days", "start_time_shift_minutes", "allowed_weekdays",
    "earliest_start_time", "latest_end_time", "turnaround_minutes", "demand_measure", "capacity_safety_margin",
    "allowed_room_inventory", "poc_room_availability_mode", "digital_compatibility", "co_location_rules",
    "allow_split", "max_rooms_per_exam", "optimization_objective_weights", "support_place_rules",
    "travel_time_minutes", "minimum_invigilator_staffing", "avoidable_cost_definition",
    "term_start_date", "term_end_date", "calendar_passes", "calendar_periods", "staff_shifts",
    "minimum_break_minutes", "maximum_continuous_minutes", "maximum_daily_minutes",
    "minimum_daily_rest_minutes", "annual_staff_cost", "annual_room_cost", "course_program_conflicts",
}

_BASE_PARAMETERS = """
"demand.variation_pct" = 10
"demand.rounding" = "up"
"window.earlier_days" = 1
"window.later_days" = 1
"calendar.weekdays" = [1, 2, 3, 4, 5]
"calendar.start_times" = ["08:00", "14:00"]
"calendar.turnaround_minutes" = 30
"flex.movable_types" = ["ordinarie", "omtenta", "dugga", "hybrid"]
"rooms.max_rooms_per_exam" = 8
"rooms.allow_split_across_buildings" = false
"staffing.ladder" = [{max_participants = 50, required_staff = 1}, {max_participants = 150, required_staff = 2}]
"staffing.preparation_minutes" = 30
"staffing.closing_minutes" = 30
"cost.room_annual_per_seat_ore" = 100000
"cost.staff_annual_ore" = 5000000
"cost.staff_session_ore" = 1000
"solver.time_limit_seconds" = 5.0
"solver.seed" = 7
"solver.workers" = 1
"""


def _write_dataset(path: Path, extra: list[dict[str, object]] | None = None) -> None:
    def row(event: str, activity: str, day: str, start: str, end: str, kind: str, digital: object,
            course: str, count: int) -> dict[str, object]:
        return {
            "exam_event_id": event, "activity_id": activity, "demand_input_status": "ready_provisional_ladok_demand",
            "scheduled_date": day, "booking_start_time": start, "scheduled_time": f"{start}-{end}",
            "observed_exam_types": kind, "observed_digital_exam_values": digital, "observed_cities": "Uppsala",
            "demand_value": count, "demand_measure_source_field": "registered_count", "course_code": course,
        }

    rows = [
        row("ev1", "a1", "2026-01-12", "08:00", "12:00", "Ordinarie tenta", "Ja", "AAA", 15),
        row("ev2", "a2", "2026-01-12", "14:00", "18:00", "Omtenta", "Nej", "BBB", 40),
        row("ev3", "a3", "2026-01-13", "09:00", "13:00", "Dugga", None, "CCC", 25),
        row("ev4", "a4", "2026-01-13", "08:00", "11:00", "Hemtenta", "Nej", "DDD", 10),
        row("ev6", "a6", "2026-01-14", "08:00", "12:00", "Ordinarie tenta", "Ja", "EEE", 20),
        row("ev6", "a7", "2026-01-14", "08:00", "12:00", "Ordinarie tenta", "Ja", "FFF", 30),
        *(extra or []),
    ]
    pd.DataFrame(rows).to_csv(path / "optimization_demands.csv", index=False, encoding="utf-8-sig")
    rooms = [
        ("uu-r1", "Adress 1", "Uppsala", 100, "all_places_support_e_exam"),
        ("uu-r2", "Adress 2", "Uppsala", 60, "supports_e_exam"),
        ("uu-r3", "Adress 3", "Uppsala", 40, "not_stated"),
        ("uu-visby", "Visby 1", "Visby", 30, "all_places_support_e_exam"),
    ]
    pd.DataFrame([
        {"room_id": room, "reference_address": address, "reference_city": city, "capacity_seats": cap,
         "digital_capability_status": status, "eligible_for_exploratory_capacity_poc": True,
         "available_from": "2027-01-01" if city == "Visby" else None, "available_to": None}
        for room, address, city, cap, status in rooms
    ]).to_csv(path / "optimization_rooms.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"activity_id": ["a1", "a2", "a3", "a4", "a6", "a7", "x"],
                  "scope_status": ["included"] * 6 + ["unresolved"]}).to_csv(
        path / "demand_scope.csv", index=False, encoding="utf-8-sig")


def _scenario(path: Path, parameters: str, events: str = '"ev1", "ev2", "ev3", "ev4", "ev6"') -> Path:
    scenario = path / "scenario.toml"
    scenario.write_text(
        'schema_version = "joint-real-subset-v1"\n[scenario]\nid = "effect"\ndescription = "d"\n'
        f'[subset]\nplan_area = "Uppsala"\nexam_event_ids = [{events}]\n[parameters]\n{parameters}\n',
        encoding="utf-8",
    )
    return scenario


def _build(directory: Path, overrides: dict[str, object] | None = None, **kwargs: object):
    parameters = tomllib.loads("[p]\n" + _BASE_PARAMETERS)["p"]
    parameters.update(overrides or {})
    lines = "\n".join(f"{json.dumps(key)} = {_toml(value)}" for key, value in parameters.items())
    scenario = _scenario(directory, lines, **kwargs)
    return build_real_subset_problem(scenario, directory, CATALOG)


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


def _fingerprint(problem) -> str:
    """Everything the optimizer sees, excluding the parameter log itself."""
    payload = _jsonable(problem)
    payload.pop("parameters")
    return json.dumps(payload, sort_keys=True)


# parameter id -> alternative value. Each must change what the optimizer receives.
EFFECT_CASES: dict[str, object] = {
    "demand.variation_pct": 50,
    "demand.rounding": "down",
    "window.earlier_days": 0,
    "window.later_days": 0,
    "calendar.weekdays": [1],
    "calendar.blocked_ranges": [{"start": "2026-01-13", "end": "2026-01-13"}],
    "calendar.start_times": ["08:00"],
    "calendar.earliest_start_time": "09:00",
    "calendar.latest_end_time": "13:00",
    "calendar.start_date": "2026-01-13",
    "calendar.end_date": "2026-01-13",
    "calendar.turnaround_minutes": 60,
    "flex.movable_types": ["omtenta"],
    "rooms.selection": ["uu-r1"],
    "rooms.max_rooms_per_exam": 1,
    "rooms.allow_split": False,
    "rooms.allow_split_across_buildings": True,
    "digital.partial_support_policy": "exclude",
    "digital.unknown_demand_policy": "assume_paper",
    "staffing.ladder": [{"max_participants": 60, "required_staff": 1}, {"max_participants": 150, "required_staff": 3}],
    "staffing.preparation_minutes": 0,
    "staffing.closing_minutes": 0,
    "cost.room_annual_per_seat_ore": 0,
    "cost.staff_annual_ore": 0,
    "cost.staff_session_ore": 5000,
    "solver.time_limit_seconds": 9.0,
    "solver.seed": 8,
    "solver.workers": 2,
    "solver.deterministic": True,
}


class ParameterEffectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        _write_dataset(self.dir)

    def test_every_implemented_parameter_has_an_effect_case_and_changes_the_model(self) -> None:
        catalog = load_parameter_catalog(CATALOG)
        implemented = {item.parameter_id for item in catalog.parameters if item.engine_support == "implemented"}
        implemented.discard("demand.measure")  # rejects other values; covered separately
        self.assertEqual(set(EFFECT_CASES), implemented, "implemented parameters and effect cases must match")
        base = _fingerprint(_build(self.dir))
        for parameter_id, value in EFFECT_CASES.items():
            with self.subTest(parameter=parameter_id):
                altered = _fingerprint(_build(self.dir, {parameter_id: value}))
                self.assertNotEqual(base, altered, f"{parameter_id} is marked implemented but is ignored")

    def test_unsupported_demand_measure_is_rejected_not_ignored(self) -> None:
        with self.assertRaisesRegex(ValueError, "registered_count"):
            _build(self.dir, {"demand.measure": "attendance"})

    def test_honored_by_points_at_real_code(self) -> None:
        for item in load_parameter_catalog(CATALOG).parameters:
            if item.engine_support != "implemented":
                continue
            module_name, _, attribute = str(item.honored_by).partition(".")
            module = importlib.import_module(f"tentaoptimering.{module_name}")
            self.assertTrue(hasattr(module, attribute), f"{item.parameter_id}: {item.honored_by}")

    def test_contract_only_parameters_never_change_the_model_but_are_reported_when_edited(self) -> None:
        catalog = load_parameter_catalog(CATALOG)
        contract_only = [item for item in catalog.parameters if item.engine_support == "contract_only"]
        self.assertIn("cost.external_room_session_ore", {item.parameter_id for item in contract_only})
        base = _build(self.dir)
        altered = _build(self.dir, {"cost.external_room_session_ore": 5_000_000})
        self.assertEqual(_fingerprint(base), _fingerprint(altered))
        self.assertTrue(all(room.external_session_cost_ore == 0 for room in altered.rooms))
        result = solve_joint_optimization(altered)
        self.assertTrue(any("ignoreras" in text and "cost.external_room_session_ore" in text for text in result.limitations))

    def test_catalog_keeps_every_legacy_parameter_or_a_declared_counterpart(self) -> None:
        covered = {legacy for item in load_parameter_catalog(CATALOG).parameters for legacy in item.legacy_ids}
        self.assertEqual(LEGACY_REGISTRY_IDS - covered, set(), "legacy parameters without counterpart")

    def test_frozen_values_not_raw_scenario_keys_drive_candidate_generation(self) -> None:
        source = (REPO_ROOT / "src" / "tentaoptimering" / "joint_inputs.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('config["parameters"]'), 1)
        # Omitting every optional key must fall back to catalog defaults, not crash.
        scenario = _scenario(self.dir, '"window.earlier_days" = 1\n"window.later_days" = 1')
        problem = build_real_subset_problem(scenario, self.dir, CATALOG)
        defaults = {item.parameter_id: item.value for item in problem.parameters}
        self.assertEqual(defaults["calendar.weekdays"], [1, 2, 3, 4, 5, 6, 7])
        self.assertTrue(any(slot.start_minute == 14 * 60 for slot in problem.slots))


class StartTimeAndReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        _write_dataset(self.dir)

    def test_slots_follow_start_times_not_a_hidden_pass_table(self) -> None:
        problem = _build(self.dir, {"calendar.start_times": ["10:00"]})
        regular = {slot.start_minute for slot in problem.slots if not slot.reference_only}
        self.assertEqual(regular, {10 * 60})

    def test_original_occasion_outside_user_settings_is_a_reference_not_a_candidate(self) -> None:
        # ev3 starts 09:00 (not an allowed start). It is movable, so 09:00 must not become a candidate.
        problem = _build(self.dir)
        ev3 = next(item for item in problem.demands if item.exam_demand_id == "exam-ev3")
        slots = {slot.slot_id: slot for slot in problem.slots}
        self.assertEqual(ev3.original_date, date(2026, 1, 13))
        self.assertEqual(ev3.original_start_minute, 9 * 60)
        self.assertNotIn((date(2026, 1, 13), 9 * 60), {(s.scheduled_date, s.start_minute) for s in slots.values()})
        self.assertTrue(all(slots[item].start_minute in (8 * 60, 14 * 60) for item in ev3.candidate_slot_ids))
        self.assertIsNone(ev3.original_slot_id)
        result = solve_joint_optimization(problem)
        schedule = {row["exam_demand_id"]: row for row in result.schedule}
        self.assertEqual(schedule["exam-ev3"]["original_start_minute"], 9 * 60)
        self.assertGreaterEqual(result.changed_exam_demands, 1)  # ev3 cannot stay at 09:00

    def test_fixed_exam_keeps_history_even_when_it_violates_the_calendar(self) -> None:
        # Hemtenta is not movable, starts 08:00 on Tue; forbid Tuesday for everyone else.
        problem = _build(self.dir, {"calendar.weekdays": [1, 3, 4, 5]})
        ev4 = next(item for item in problem.demands if item.exam_demand_id == "exam-ev4")
        slot = {item.slot_id: item for item in problem.slots}[ev4.candidate_slot_ids[0]]
        self.assertEqual((slot.scheduled_date, slot.start_minute), (date(2026, 1, 13), 8 * 60))
        self.assertTrue(slot.reference_only)
        regular_dates = {item.scheduled_date for item in problem.slots if not item.reference_only}
        self.assertNotIn(date(2026, 1, 13), regular_dates)

    def test_movable_exam_without_any_allowed_occasion_blocks_instead_of_crashing(self) -> None:
        problem = _build(self.dir, {"window.earlier_days": 0, "window.later_days": 0, "calendar.weekdays": [1]})
        result = solve_joint_optimization(problem)
        self.assertEqual(result.solver.outcome, "infeasible")
        self.assertFalse(result.coverage.technical_placement_complete)
        self.assertTrue(any(text.startswith("Blockerande krav") for text in result.limitations))
        self.assertEqual(result.verification["independent_validation"], "not_performed")


class DigitalAndGroupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        _write_dataset(self.dir)

    def test_supports_e_exam_is_digital_capable_but_flagged_unverified(self) -> None:
        problem = _build(self.dir)
        rooms = {room.room_id: room for room in problem.rooms}
        self.assertEqual(rooms["uu-r1"].digital_support_basis, "all_places")
        self.assertIn("e_exam", rooms["uu-r2"].digital_capabilities)
        self.assertEqual(rooms["uu-r2"].digital_support_basis, "some_places_unquantified")
        self.assertEqual(rooms["uu-r3"].digital_capabilities, ("paper",))
        self.assertEqual(rooms["uu-r3"].digital_support_basis, "unknown")
        self.assertNotIn("uu-visby", rooms)  # other planning area

    def test_exclude_policy_removes_partial_rooms_from_digital_exams(self) -> None:
        problem = _build(self.dir, {"digital.partial_support_policy": "exclude"})
        rooms = {room.room_id: room for room in problem.rooms}
        self.assertEqual(rooms["uu-r2"].digital_capabilities, ("paper",))

    def test_missing_or_mixed_digital_flag_is_never_silently_paper(self) -> None:
        problem = _build(self.dir)
        demands = {item.exam_demand_id: item for item in problem.demands}
        self.assertEqual((demands["exam-ev3"].digital_requirement, demands["exam-ev3"].digital_requirement_basis),
                         ("e_exam", "unobserved"))
        self.assertEqual(demands["exam-ev2"].digital_requirement, "paper")
        problem = _build(self.dir, {"digital.unknown_demand_policy": "assume_paper"})
        ev3 = next(item for item in problem.demands if item.exam_demand_id == "exam-ev3")
        self.assertEqual((ev3.digital_requirement, ev3.digital_requirement_basis), ("paper", "unobserved"))

    def test_mixed_digital_values_in_one_event_require_digital_and_are_flagged(self) -> None:
        extra = [
            {"exam_event_id": "ev9", "activity_id": "a9", "demand_input_status": "ready_provisional_ladok_demand",
             "scheduled_date": "2026-01-14", "booking_start_time": "14:00", "scheduled_time": "14:00-17:00",
             "observed_exam_types": "Ordinarie tenta", "observed_digital_exam_values": "Ja", "observed_cities": "Uppsala",
             "demand_value": 5, "demand_measure_source_field": "registered_count", "course_code": "GGG"},
            {"exam_event_id": "ev9", "activity_id": "a10", "demand_input_status": "ready_provisional_ladok_demand",
             "scheduled_date": "2026-01-14", "booking_start_time": "14:00", "scheduled_time": "14:00-17:00",
             "observed_exam_types": "Ordinarie tenta", "observed_digital_exam_values": "Nej", "observed_cities": "Uppsala",
             "demand_value": 5, "demand_measure_source_field": "registered_count", "course_code": "HHH"},
        ]
        _write_dataset(self.dir, extra)
        problem = _build(self.dir, events='"ev9"')
        demand = problem.demands[0]
        self.assertEqual((demand.digital_requirement, demand.digital_requirement_basis), ("e_exam", "observed_mixed"))

    def test_result_does_not_claim_verified_digital_compatibility(self) -> None:
        result = solve_joint_optimization(_build(self.dir))
        self.assertIn("digital_compatibility", result.verification)
        self.assertNotIn("verified_by", result.verification["digital_compatibility"])
        self.assertTrue(result.verification["digital_compatibility"].startswith(("assumed_not_verified", "consistent_with_published")))
        self.assertEqual(result.verification["independent_validation"], "not_performed")
        self.assertEqual(result.verification["student_overlap"], "not_evaluated")

    def test_shared_exam_sums_groups_but_records_unverified_disjointness(self) -> None:
        problem = _build(self.dir)
        ev6 = next(item for item in problem.demands if item.exam_demand_id == "exam-ev6")
        self.assertEqual(len(ev6.participant_groups), 2)
        self.assertEqual(ev6.participant_count, 22 + 33)  # 20 and 30 scaled +10 %, rounded up
        self.assertEqual(ev6.participant_group_basis, "assumed_disjoint_groups_sum")
        result = solve_joint_optimization(problem)
        self.assertIn("assumed_not_verified", result.verification["group_disjointness"])

    def test_integer_rounding_has_no_float_noise(self) -> None:
        from tentaoptimering.joint_inputs import _scaled_count
        self.assertEqual(_scaled_count(15, 10, "up"), 17)       # 16.5 -> 17
        self.assertEqual(_scaled_count(15, 10, "down"), 16)
        self.assertEqual(_scaled_count(15, 10, "nearest"), 17)  # half up
        self.assertEqual(_scaled_count(7, -90, "down"), 1)      # never below one participant
        self.assertEqual(_scaled_count(7, 0, "up"), 7)


if __name__ == "__main__":
    unittest.main()
