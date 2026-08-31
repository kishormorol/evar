from __future__ import annotations

import unittest

from scripts.plan_human_pr_200_power import exact_mcnemar_power, wilson_upper


class HumanPR200PowerTests(unittest.TestCase):
    def test_wilson_upper_accounts_for_small_pilot(self) -> None:
        self.assertGreater(wilson_upper(0, 10), 0.20)
        self.assertGreater(wilson_upper(3, 10), 0.50)

    def test_exact_power_increases_with_sample_size(self) -> None:
        small = exact_mcnemar_power(50, 0.50, 0.15)
        large = exact_mcnemar_power(200, 0.50, 0.15)

        self.assertGreater(large, small)
        self.assertGreaterEqual(small, 0.0)
        self.assertLessEqual(large, 1.0)

    def test_exact_power_rejects_impossible_effect(self) -> None:
        with self.assertRaises(ValueError):
            exact_mcnemar_power(100, 0.10, 0.20)


if __name__ == "__main__":
    unittest.main()
