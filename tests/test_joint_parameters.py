"""Parameters as the interface edits them: choices, validation, listing order, scenario files and rule-based selection."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_joint_validation_run import CATALOG, _write_pair_dataset  # noqa: E402
from tentaoptimering.joint_inputs import build_real_subset_problem  # noqa: E402
from tentaoptimering.joint_parameters import GROUPS, LAYOUT, describe_parameters, layout  # noqa: E402
from tentaoptimering.joint_selection import (  # noqa: E402
    count_selected, date_window, describe_subset, select_ready_demands, subset_kind,
)
from tentaoptimering.joint_toml import dump_scenario  # noqa: E402
from tentaoptimering.parameter_catalog import load_parameter_catalog  # noqa: E402
from tentaoptimering.parameter_validation import check_value, validate_overrides  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = REPO_ROOT / "config" / "scenarios"
PROCESSED = REPO_ROOT / "data" / "processed"
FULL_TERM = SCENARIOS / "joint_underlay_period.toml"
CATALOG_DATA = load_parameter_catalog(CATALOG)
BY_ID = {item.parameter_id: item for item in CATALOG_DATA.parameters}


def _errors(**overrides: object) -> dict[str, str]:
    """Problems by parameter id; parameter ids with dots are given with `__` for the dot."""
    values = {key.replace("__", "."): value for key, value in overrides.items()}
    return {item["id"]: item["message"] for item in validate_overrides(CATALOG_DATA, values)}


class CatalogChoiceTests(unittest.TestCase):
    def test_every_choice_parameter_lists_its_allowed_values_and_the_default_is_one_of_them(self) -> None:
        choice_parameters = [item for item in CATALOG_DATA.parameters if item.value_type == "choice"]
        self.assertGreaterEqual(len(choice_parameters), 6)
        for item in choice_parameters:
            with self.subTest(parameter=item.parameter_id):
                self.assertTrue(item.choices)
                self.assertIn(item.default, [value for value, _ in item.choices])
                self.assertTrue(all(label for _, label in item.choices))
        self.assertTrue(all(not item.choices for item in CATALOG_DATA.parameters if item.value_type != "choice"))

    def test_the_engine_accepts_every_listed_choice_of_an_implemented_parameter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            scenario = _write_pair_dataset(directory)
            base = scenario.read_text(encoding="utf-8")
            for item in CATALOG_DATA.parameters:
                if item.value_type != "choice" or item.engine_support != "implemented":
                    continue
                for value, _ in item.choices:
                    with self.subTest(parameter=item.parameter_id, value=value):
                        config = directory / "choice.toml"
                        config.write_text(base + f'"{item.parameter_id}" = "{value}"\n', encoding="utf-8")
                        problem = build_real_subset_problem(config, directory, CATALOG)
                        frozen = {entry.parameter_id: entry.value for entry in problem.parameters}
                        self.assertEqual(frozen[item.parameter_id], value)
                        if item.parameter_id == "solver.strategy":
                            self.assertEqual(problem.solver.strategy, value)
            bad = directory / "bad.toml"
            bad.write_text(base + '"demand.rounding" = "sideways"\n', encoding="utf-8")
            with self.assertRaises(ValueError):  # the engine really does refuse values outside the listed choices
                build_real_subset_problem(bad, directory, CATALOG)

    def test_choices_must_be_declared_for_a_choice_parameter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.toml"
            path.write_text('catalog_version = "x"\n[[parameter]]\nid = "a"\ngroup = "g"\nlabel = "l"\nvalue_type = "choice"\n'
                            'default = "u"\ndefault_basis = "assumption"\nhelp_text = "h"\nengine_support = "contract_only"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_parameter_catalog(path)

    def test_the_catalog_version_and_counts_are_the_documented_ones(self) -> None:
        self.assertEqual(CATALOG_DATA.version, "2.5.0")
        self.assertEqual(len(CATALOG_DATA.parameters), 63)
        self.assertEqual(sum(item.engine_support == "implemented" for item in CATALOG_DATA.parameters), 41)


class ValidationTests(unittest.TestCase):
    def test_unknown_and_unsupported_parameters_are_refused(self) -> None:
        errors = _errors(no__such__thing=1, rules__student_conflicts=True, cost__external_room_session_ore=5)
        self.assertEqual(set(errors), {"no.such.thing", "rules.student_conflicts", "cost.external_room_session_ore"})
        self.assertEqual(errors["no.such.thing"], "Okänd parameter.")
        self.assertIn("Stöds inte av motorn än", errors["rules.student_conflicts"])
        self.assertIn("Stöds inte av motorn än", errors["cost.external_room_session_ore"])

    def test_every_error_is_reported_as_id_and_swedish_message(self) -> None:
        result = validate_overrides(CATALOG_DATA, {"window.earlier_days": -1, "x": 1})
        self.assertEqual(sorted(item["id"] for item in result), ["window.earlier_days", "x"])
        self.assertTrue(all(set(item) == {"id", "message"} and item["message"] for item in result))

    def test_each_value_type_rejects_the_wrong_kind_of_value(self) -> None:
        wrong = {
            "window.earlier_days": ["1", 1.5, True, None, -1],        # integer
            "solver.time_limit_seconds": ["a", True, 0, float("nan")],  # number
            "rooms.allow_split": [1, "true", None],                  # boolean
            "demand.rounding": ["sideways", 3, None],                # choice
            "calendar.start_date": [20260112, "2026-13-01", "12/1"],  # date
            "calendar.latest_end_time": ["8:00", "24:00", "12:60", 800],  # time
            "calendar.start_times": ["08:00", [], ["8:00"], ["08:00", "08:00"], [800]],  # time_list
            "calendar.weekdays": [[], [0], [8], ["1"], [1, 1], 3],   # integer_list
            "flex.movable_types": ["ordinarie", [1], [""]],          # string_list
            "calendar.blocked_ranges": [[{"start": "2026-01-02"}], [{"start": "2026-01-05", "end": "2026-01-02"}],
                                        [{"start": "x", "end": "2026-01-02"}], "a"],  # date_range_list
            "staffing.ladder": [[], [{"max_participants": 50}], [{"max_participants": 50, "required_staff": 0}],
                                [{"max_participants": 150, "required_staff": 2}, {"max_participants": 50, "required_staff": 3}],
                                [{"max_participants": 50, "required_staff": 3}, {"max_participants": 150, "required_staff": 2}],
                                [{"max_participants": 50.5, "required_staff": 1}]],  # staffing_ladder
            "rooms.selection": ["uu-r1", [1], [""]],                 # room_id_list
        }
        for parameter_id, values in wrong.items():
            for value in values:
                with self.subTest(parameter=parameter_id, value=value):
                    self.assertIsNotNone(check_value(BY_ID[parameter_id], value))
                    self.assertIn(parameter_id, {item["id"] for item in validate_overrides(CATALOG_DATA, {parameter_id: value})})

    def test_reasonable_values_are_accepted(self) -> None:
        good = {
            "window.earlier_days": 3, "demand.variation_pct": -10, "demand.rounding": "nearest",
            "solver.time_limit_seconds": 30.5, "solver.relative_gap_limit": 0, "rooms.allow_split": False,
            "calendar.start_date": "", "calendar.end_date": "2026-03-31", "calendar.earliest_start_time": "07:30",
            "calendar.start_times": ["08:00", "10:30", "14:00"], "calendar.weekdays": [1, 2, 3, 4, 5],
            "flex.movable_types": [], "rooms.selection": ["uu-r1"],
            "calendar.blocked_ranges": [{"start": "2026-02-01", "end": "2026-02-01"}],
            "staffing.ladder": [{"max_participants": 40, "required_staff": 1}, {"max_participants": 120, "required_staff": 1},
                                {"max_participants": 300, "required_staff": 4}],
            "cost.room_annual_per_seat_ore": 150000, "digital.partial_support_policy": "exclude", "solver.strategy": "monolithic",
            "solver.workers": 4, "solver.seed": 1,
        }
        self.assertEqual(validate_overrides(CATALOG_DATA, good), [])

    def test_number_limits_and_booleans_are_not_integers(self) -> None:
        self.assertIn("rooms.max_rooms_per_exam", _errors(rooms__max_rooms_per_exam=0))
        self.assertIn("solver.workers", _errors(solver__workers=0))
        self.assertIn("solver.relative_gap_limit", _errors(solver__relative_gap_limit=1.5))
        self.assertIn("demand.variation_pct", _errors(demand__variation_pct=-100))
        self.assertIn("cost.staff_annual_ore", _errors(cost__staff_annual_ore=-5))
        self.assertIn("cost.staff_annual_ore", _errors(cost__staff_annual_ore=10 ** 15))
        self.assertIn("window.later_days", _errors(window__later_days=False))

    def test_dates_and_times_must_agree_with_each_other(self) -> None:
        self.assertIn("calendar.start_date", _errors(calendar__start_date="2026-03-02", calendar__end_date="2026-03-01"))
        self.assertIn("calendar.earliest_start_time", _errors(calendar__earliest_start_time="20:00"))
        result = validate_overrides(CATALOG_DATA, {"calendar.end_date": "2026-01-01"}, {"calendar.start_date": "2026-02-01"})
        self.assertEqual([item["id"] for item in result], ["calendar.end_date"])
        self.assertEqual(validate_overrides(CATALOG_DATA, {"calendar.end_date": ""}, {"calendar.start_date": "2026-02-01"}), [])

    def test_every_default_of_an_implemented_parameter_is_acceptable(self) -> None:
        for item in CATALOG_DATA.parameters:
            if item.engine_support == "implemented":
                with self.subTest(parameter=item.parameter_id):
                    self.assertIsNone(check_value(item, item.default))

    def test_the_bundled_scenarios_only_use_acceptable_values(self) -> None:
        for path in SCENARIOS.glob("*.toml"):
            content = tomllib.loads(path.read_text(encoding="utf-8"))
            if content.get("schema_version") == "joint-real-subset-v1":
                with self.subTest(scenario=path.name):
                    errors = validate_overrides(CATALOG_DATA, content["parameters"])
                    # Older files may restate a parameter that the engine does not use yet, at its default.
                    self.assertEqual([item for item in errors if not item["message"].startswith("Stöds inte")], [])
                    if path.name == "joint_underlay_period.toml":
                        self.assertEqual(errors, [])


class ListingTests(unittest.TestCase):
    def test_every_parameter_is_placed_once_in_a_fixed_group_order(self) -> None:
        placed = [parameter_id for ids in LAYOUT.values() for parameter_id in ids]
        self.assertEqual(len(placed), len(set(placed)))
        self.assertEqual(set(placed), set(BY_ID))  # a new catalog parameter must be placed on purpose
        self.assertEqual([group for group, _ in GROUPS], ["tid", "rum", "bemanning", "kostnad", "korning", "ovrigt"])
        rows = layout(CATALOG_DATA)
        self.assertEqual([order for _, _, order in rows], list(range(len(rows))))
        groups = [group for _, group, _ in rows]
        self.assertEqual(groups, sorted(groups, key=[group for group, _ in GROUPS].index))

    def test_the_payload_separates_default_scenario_value_and_effective_value(self) -> None:
        content = tomllib.loads(FULL_TERM.read_text(encoding="utf-8"))
        payload = describe_parameters(CATALOG_DATA, "joint_underlay_period", dict(content["parameters"]))
        self.assertEqual((payload["catalog_version"], payload["scenario_id"]), ("2.5.0", "joint_underlay_period"))
        self.assertEqual(len(payload["parameters"]), 63)
        self.assertEqual(set(payload["group_labels"]), {group for group, _ in GROUPS})
        rows = {row["id"]: row for row in payload["parameters"]}
        window = rows["window.earlier_days"]
        self.assertEqual((window["default"], window["scenario_value"], window["value"], window["differs_from_default"]), (0, 1, 1, True))
        self.assertTrue(window["editable"])
        untouched = rows["rooms.selection"]  # not set by the scenario: the effective value is the default
        self.assertEqual((untouched["scenario_value"], untouched["value"], untouched["differs_from_default"]), (None, [], False))
        self.assertFalse(rows["rules.student_conflicts"]["editable"])
        self.assertEqual(rows["rules.student_conflicts"]["engine_support"], "contract_only")
        self.assertEqual([choice["value"] for choice in rows["demand.rounding"]["choices"]], ["up", "nearest", "down"])
        self.assertIsNone(rows["window.earlier_days"]["choices"])
        self.assertTrue(rows["solver.seed"]["advanced"])
        self.assertFalse(rows["window.earlier_days"]["advanced"])
        self.assertEqual(rows["window.earlier_days"]["basis"], "assumption")
        for row in payload["parameters"]:
            self.assertEqual(row["editable"], row["engine_support"] == "implemented")
            self.assertEqual(set(row), {"id", "label", "group", "value_type", "unit", "help_text", "default", "scenario_value", "value",
                                        "differs_from_default", "basis", "engine_support", "editable", "advanced", "choices", "order"})


class ScenarioFileTests(unittest.TestCase):
    def test_a_scenario_written_back_reads_as_the_same_content(self) -> None:
        for path in SCENARIOS.glob("*.toml"):
            content = tomllib.loads(path.read_text(encoding="utf-8"))
            if content.get("schema_version") == "joint-real-subset-v1":
                with self.subTest(scenario=path.name):
                    self.assertEqual(tomllib.loads(dump_scenario(content)), content)

    def test_odd_values_survive_the_round_trip(self) -> None:
        content = {"schema_version": "x", "t": {"a.b": 'quote " and \\ and åäö', "list": [{"k": 1}, {"k": 2.5}], "flag": True, "d": ""}}
        self.assertEqual(tomllib.loads(dump_scenario(content)), content)
        with self.assertRaises(ValueError):
            dump_scenario({"t": {"x": float("inf")}})


def _rule_frame() -> pd.DataFrame:
    def row(event: str, day: str, city: str = "Uppsala", status: str = "ready_provisional_ladok_demand", activity: str | None = None) -> dict:
        return {"exam_event_id": event, "activity_id": activity or f"act-{event}", "demand_input_status": status, "scheduled_date": day,
                "observed_cities": city}
    return pd.DataFrame([
        row("early", "2026-01-05"), row("a", "2026-01-12"), row("b", "2026-02-02"), row("b", "2026-02-02", activity="b2"),
        row("late", "2026-04-20"), row("visby", "2026-02-03", city="Visby"), row("notready", "2026-02-04", status="missing_configured_demand_value"),
    ])


class RuleSelectionTests(unittest.TestCase):
    def test_the_rule_takes_ready_events_in_the_area_and_dates_not_a_list(self) -> None:
        frame = _rule_frame()
        subset = {"plan_area": "Uppsala", "selection": "all_ready"}
        self.assertEqual(sorted(set(select_ready_demands(frame, subset)["exam_event_id"])), ["a", "b", "early", "late"])
        windowed = {**subset, "date_from": "2026-01-12", "date_to": "2026-03-31"}
        rows = select_ready_demands(frame, windowed)
        self.assertEqual(sorted(set(rows["exam_event_id"])), ["a", "b"])
        self.assertEqual(len(rows), 3)  # the rows of a joint event stay together
        self.assertEqual(sorted(set(select_ready_demands(frame, {**subset, "date_from": "2026-02-02"})["exam_event_id"])), ["b", "late"])
        self.assertEqual(sorted(set(select_ready_demands(frame, {**subset, "date_to": "2026-01-12"})["exam_event_id"])), ["a", "early"])
        self.assertEqual(count_selected(frame, windowed), 2)
        self.assertEqual(sorted(set(select_ready_demands(frame, {"plan_area": "Visby", "selection": "all_ready"})["exam_event_id"])), ["visby"])

    def test_named_events_work_as_before(self) -> None:
        frame = _rule_frame()
        rows = select_ready_demands(frame, {"plan_area": "Uppsala", "exam_event_ids": ["a", "b"]})
        self.assertEqual(sorted(set(rows["exam_event_id"])), ["a", "b"])
        for missing in (["a", "nope"], ["notready"]):
            with self.assertRaises(ValueError) as caught:
                select_ready_demands(frame, {"plan_area": "Uppsala", "exam_event_ids": missing})
            self.assertIn("saknar event", str(caught.exception))

    def test_exactly_one_way_of_choosing_is_allowed_and_bad_rules_are_explained(self) -> None:
        frame = _rule_frame()
        both = {"plan_area": "Uppsala", "exam_event_ids": ["a"], "selection": "all_ready"}
        neither = {"plan_area": "Uppsala"}
        for subset in (both, neither):
            with self.assertRaises(ValueError) as caught:
                select_ready_demands(frame, subset)
            self.assertIn("exam_event_ids", str(caught.exception))
        with self.assertRaises(ValueError):
            subset_kind({"plan_area": "Uppsala", "exam_event_ids": ["a"], "date_from": "2026-01-01"})
        with self.assertRaises(ValueError):
            subset_kind({"plan_area": "Uppsala", "selection": "everything"})
        for bad in ({"date_from": "2026-13-01"}, {"date_to": "x"}, {"date_from": "2026-03-01", "date_to": "2026-02-01"}):
            with self.assertRaises(ValueError):
                select_ready_demands(frame, {"plan_area": "Uppsala", "selection": "all_ready", **bad})
        with self.assertRaises(ValueError):
            select_ready_demands(frame, {"plan_area": "Uppsala", "selection": "all_ready", "date_from": "2027-01-01"})
        self.assertEqual(date_window({"date_from": "2026-01-12"}), ("2026-01-12", None))
        self.assertIn("2 tentor", describe_subset({"plan_area": "Uppsala", "selection": "all_ready"}, 2))

    def test_a_rule_scenario_builds_the_same_problem_as_the_equivalent_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            listed = _write_pair_dataset(directory)
            by_rule = directory / "rule.toml"
            text = listed.read_text(encoding="utf-8")
            by_rule.write_text(text.replace('exam_event_ids = ["X", "Y"]', 'selection = "all_ready"\ndate_from = "2026-01-12"\ndate_to = "2026-01-12"'),
                               encoding="utf-8")
            first = build_real_subset_problem(listed, directory, CATALOG)
            second = build_real_subset_problem(by_rule, directory, CATALOG)
            self.assertEqual(replace(first, problem_id="x"), replace(second, problem_id="x"))
            self.assertEqual([item.exam_demand_id for item in second.demands], ["exam-X", "exam-Y"])
            by_rule.write_text(text.replace('exam_event_ids = ["X", "Y"]', 'selection = "all_ready"\ndate_from = "2026-02-01"'), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_real_subset_problem(by_rule, directory, CATALOG)


@unittest.skipUnless((PROCESSED / "optimization_demands.csv").is_file(), "prepared data is not available")
class FullTermScenarioTests(unittest.TestCase):
    def test_the_full_term_scenario_covers_every_ready_event_of_the_term_in_uppsala(self) -> None:
        demands = pd.read_csv(PROCESSED / "optimization_demands.csv", encoding="utf-8-sig")
        ready = demands[(demands["demand_input_status"] == "ready_provisional_ladok_demand") & (demands["observed_cities"] == "Uppsala")
                        & (demands["scheduled_date"] >= "2026-01-12") & (demands["scheduled_date"] <= "2026-03-31")]
        expected = {f"exam-{event}" for event in ready["exam_event_id"]}
        problem = build_real_subset_problem(FULL_TERM, PROCESSED, CATALOG)
        self.assertEqual({item.exam_demand_id for item in problem.demands}, expected)
        self.assertGreater(len(expected), 100)
        self.assertEqual(problem.problem_id, "joint_underlay_period_2026")
        self.assertEqual((problem.solver.time_limit_seconds, problem.solver.num_workers, problem.solver.strategy), (300.0, 8, "decomposed"))
        self.assertEqual(problem.slots[0].scheduled_date, date(2026, 1, 12))  # the scenario fixes the first day
        values = {item.parameter_id: item.value for item in problem.parameters}
        self.assertEqual((values["window.earlier_days"], values["window.later_days"], values["calendar.start_times"]),
                         (1, 1, ["08:00", "14:00"]))
        self.assertEqual((values["cost.room_annual_per_seat_ore"], values["cost.staff_annual_ore"]), (100000, 5000000))


if __name__ == "__main__":
    unittest.main()
