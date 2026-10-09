from __future__ import annotations

from pathlib import Path
import unittest

from tentaoptimering.parameter_catalog import freeze_parameter_values, load_parameter_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParameterCatalogTests(unittest.TestCase):
    def test_catalog_keeps_supported_and_unsupported_parameters_visible(self) -> None:
        catalog = load_parameter_catalog(REPO_ROOT / "config" / "joint_parameter_catalog.toml")
        definitions = {item.parameter_id: item for item in catalog.parameters}
        self.assertEqual(definitions["rooms.max_rooms_per_exam"].engine_support, "implemented")
        self.assertEqual(definitions["rules.student_conflicts"].engine_support, "contract_only")
        self.assertGreaterEqual(len(definitions), 30)

    def test_frozen_values_preserve_assumptions_and_protect_verified_basis(self) -> None:
        catalog = load_parameter_catalog(REPO_ROOT / "config" / "joint_parameter_catalog.toml")
        values = freeze_parameter_values(
            catalog,
            {"window.earlier_days": 3, "staffing.max_continuous_minutes": 240},
            {
                "window.earlier_days": "Handräknat effektfall.",
                "staffing.max_continuous_minutes": "Experiment med kortare arbetspass.",
            },
        )
        frozen = {item.parameter_id: item for item in values}
        self.assertEqual(frozen["window.earlier_days"].value, 3)
        self.assertEqual(frozen["window.earlier_days"].basis, "assumption")
        self.assertEqual(frozen["staffing.max_continuous_minutes"].basis, "experiment")
        self.assertEqual(frozen["rules.student_conflicts"].engine_support, "contract_only")


if __name__ == "__main__":
    unittest.main()
