from pathlib import Path
import unittest

from tentaoptimering.integrated_config import load_integrated_term_scenario
from tentaoptimering.term_calendar import generate_calendar_slots


REPO_ROOT = Path(__file__).resolve().parents[1]


class IntegratedConfigTests(unittest.TestCase):
    def test_exploratory_term_scenario_is_traceable_and_generates_calendar(self) -> None:
        scenario = load_integrated_term_scenario(
            REPO_ROOT / "config" / "scenarios" / "integrated_term_exploratory.toml"
        )

        self.assertEqual(scenario.scenario_id, "integrated_term_exploratory_2026")
        self.assertGreaterEqual(len(scenario.assumptions), 6)
        self.assertTrue(all(item.source and item.rationale and item.unit for item in scenario.assumptions))
        self.assertGreater(len(generate_calendar_slots(scenario.calendar)), 0)


if __name__ == "__main__":
    unittest.main()
