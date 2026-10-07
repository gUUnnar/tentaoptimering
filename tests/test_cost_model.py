from __future__ import annotations

import unittest

from tentaoptimering.cost_model import uncalculated_savings


class CostModelTests(unittest.TestCase):
    def test_savings_remain_unavailable_until_cost_links_are_verified(self) -> None:
        result = uncalculated_savings()
        self.assertIsNone(result.potentially_realizable_saving_sek)
        self.assertGreaterEqual(len(result.blocking_reasons), 3)


if __name__ == "__main__":
    unittest.main()
