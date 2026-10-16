"""B, the base optimisation, is defined by documented values: apart from them it uses the catalog defaults."""

from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from tentaoptimering.parameter_catalog import load_parameter_catalog

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "config" / "scenarios" / "joint_base.toml"
CATALOG = ROOT / "config" / "joint_parameter_catalog.toml"
ASSUMPTIONS = {"wish.candidate_policy", "wish.tiebreak", "rooms.include_observed_unregistered", "cost.room_annual_per_seat_ore", "resources.pack"}


class BaseScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.content = tomllib.loads(REFERENCE.read_text(encoding="utf-8"))

    def test_it_sets_only_the_documented_assumptions(self) -> None:
        self.assertEqual(set(self.content["parameters"]), ASSUMPTIONS)

    def test_every_value_it_sets_differs_from_the_default_and_has_a_reason(self) -> None:
        defaults = {item.parameter_id: item.default for item in load_parameter_catalog(CATALOG).parameters}
        for key, value in self.content["parameters"].items():
            with self.subTest(parameter=key):
                self.assertNotEqual(value, defaults[key], "a value equal to the default is not an assumption")
                self.assertTrue(self.content["rationales"].get(key), "every assumption needs a rationale")

    def test_it_takes_every_ready_exam_without_a_date_limit(self) -> None:
        subset = self.content["subset"]
        self.assertEqual(subset["selection"], "all_ready")
        self.assertNotIn("date_from", subset)
        self.assertNotIn("date_to", subset)


if __name__ == "__main__":
    unittest.main()
