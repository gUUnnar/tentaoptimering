from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from tentaoptimering.cost_comparison import preliminary_cost_comparison


class CostComparisonTests(unittest.TestCase):
    def test_exposes_internal_rent_only_as_non_comparable_context(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            pd.DataFrame([{"annual_internal_rent_prelim_2026_sek": 100.50}]).to_csv(
                directory / "lease_rows.csv", index=False, encoding="utf-8-sig"
            )
            result = preliminary_cost_comparison(directory, 5_000)

        self.assertEqual(result["status"], "not_comparable")
        self.assertEqual(result["source_baseline_preliminary_internal_rent_ore"], 10_050)
        self.assertNotIn("illustrative_unverified_delta_ore", result)
        self.assertIsNone(result["verified_realizable_saving_ore"])


if __name__ == "__main__":
    unittest.main()
