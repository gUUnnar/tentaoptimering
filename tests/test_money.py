"""Kronor everywhere: exact amounts, solver units only inside the solver, and old öre files read as kronor."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tentaoptimering import legacy_money  # noqa: E402
from tentaoptimering.joint_validation import money as validator_money  # noqa: E402
from tentaoptimering.money import check_kr, from_units, has_at_most_two_decimals, kdiff, kmul, ksum, to_units  # noqa: E402
from tentaoptimering.parameter_catalog import ParameterDefinition  # noqa: E402
from tentaoptimering.parameter_validation import check_value  # noqa: E402


class MoneyTests(unittest.TestCase):
    def test_units_round_trip_without_noise(self) -> None:
        for amount in (0, 4.5, 0.07, 1234.56, 600000, 0.01, 99999.99):
            self.assertEqual(from_units(to_units(amount)), amount)
        self.assertEqual(to_units(0.07), 7)  # 0.07 * 100 is 7.000000000000001 in floating point
        self.assertEqual(to_units(4.5), 450)
        self.assertIsInstance(from_units(1000), int)  # a whole number of kronor stays an integer

    def test_sums_differences_and_products_are_exact(self) -> None:
        self.assertEqual(ksum([0.1, 0.2]), 0.3)  # 0.1 + 0.2 is 0.30000000000000004 as floats
        self.assertEqual(kdiff(1234.56, 1000.11), 234.45)
        self.assertEqual(kmul(4.5, 195), 877.5)  # 450 öre per minute for 195 paid minutes
        self.assertEqual(kmul(0.07, 3), 0.21)

    def test_more_than_two_decimals_is_refused(self) -> None:
        self.assertTrue(has_at_most_two_decimals(12.34))
        self.assertFalse(has_at_most_two_decimals(12.345))
        with self.assertRaisesRegex(ValueError, "högst två decimaler"):
            check_kr(12.345, "pris")
        with self.assertRaisesRegex(ValueError, "belopp i kronor"):
            check_kr("12", "pris")
        with self.assertRaises(ValueError):
            check_kr(float("nan"), "pris")

    def test_a_money_parameter_takes_kronor_with_two_decimals(self) -> None:
        definition = ParameterDefinition("cost.staff_paid_minute_kr", "Kostnader", "Kostnad per betald minut", "number", "kr_per_minute", 0,
                                         "assumption", "", "implemented", None)
        self.assertIsNone(check_value(definition, 4.5))
        self.assertIsNotNone(check_value(definition, 4.555))
        self.assertIsNotNone(check_value(definition, -1))


class LegacyTests(unittest.TestCase):
    OLD = {"costs": {"annual_room_cost_ore": 1_000_000, "comparable_total_cost_ore": 1_000_450}, "staffing": {"annual_cost_ore_per_staff": 5_000_000,
           "paid_minute_cost_ore": 450}, "parameters": [{"parameter_id": "cost.staff_annual_ore", "value": 5_000_000, "basis": "assumption"},
                                                         {"parameter_id": "window.later_days", "value": 1, "basis": "assumption"}],
           "solver": {"objective_value_ore": None}, "unit": "ore_per_year"}

    def test_an_old_document_is_read_as_kronor_and_left_unchanged(self) -> None:
        import copy

        snapshot = copy.deepcopy(self.OLD)
        new = legacy_money.upgrade(self.OLD)
        self.assertEqual(self.OLD, snapshot)  # a copy: the stored document is never changed
        self.assertEqual(new["costs"], {"annual_room_cost_kr": 10000, "comparable_total_cost_kr": 10004.5})
        self.assertEqual(new["staffing"], {"annual_cost_kr_per_staff": 50000, "paid_minute_cost_kr": 4.5})
        self.assertEqual(new["parameters"][0], {"parameter_id": "cost.staff_annual_kr", "value": 50000, "basis": "assumption"})
        self.assertEqual(new["parameters"][1]["value"], 1)  # other parameters are not scaled
        self.assertIsNone(new["solver"]["objective_value_kr"])
        self.assertEqual(new["unit"], "kr_per_year")

    def test_upgrading_twice_does_nothing(self) -> None:
        once = legacy_money.upgrade(self.OLD)
        self.assertEqual(legacy_money.upgrade(once), once)
        self.assertFalse(legacy_money.has_legacy_money(once))
        self.assertTrue(legacy_money.has_legacy_money(self.OLD))

    def test_the_validators_own_copy_agrees_with_the_engines(self) -> None:
        mine, theirs = validator_money.upgrade(self.OLD), legacy_money.upgrade(self.OLD)
        mine.pop("unit"), theirs.pop("unit")  # the validator does not read unit labels, only amounts
        self.assertEqual(mine, theirs)

    def test_an_old_scenario_file_is_converted_not_read_a_hundred_times_too_dear(self) -> None:
        content = {"parameters": {"cost.staff_annual_ore": 5_000_000, "cost.staff_paid_minute_ore": 450, "window.later_days": 1},
                   "rationales": {"cost.staff_annual_ore": "Proxy"}}
        new = legacy_money.upgrade_scenario(content)
        self.assertEqual(new["parameters"], {"cost.staff_annual_kr": 50000, "cost.staff_paid_minute_kr": 4.5, "window.later_days": 1})
        self.assertEqual(list(new["rationales"]), ["cost.staff_annual_kr"])


class ValidatorMoneyTests(unittest.TestCase):
    def test_amounts_become_exact_hundredths(self) -> None:
        self.assertEqual(validator_money.units(4.5), 450)
        self.assertEqual(validator_money.units(877.5), 87750)
        self.assertEqual(validator_money.units(0.07), 7)
        with self.assertRaises(ValueError):
            validator_money.units(0.071)
        self.assertIsNone(validator_money.reported_units(None))
        self.assertIsNone(validator_money.reported_units(1.001))  # an inexact reported amount differs from every recomputation
        self.assertEqual(validator_money.text(87750), "877,50 kr")
        self.assertEqual(validator_money.text(60000000), "600000 kr")


if __name__ == "__main__":
    unittest.main()
