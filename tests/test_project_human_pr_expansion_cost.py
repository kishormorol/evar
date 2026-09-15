from __future__ import annotations

import unittest

from scripts.project_human_pr_expansion_cost import build_projection


class HumanPRExpansionCostProjectionTests(unittest.TestCase):
    def test_projection_counts_full_and_additional_stability_attempts(self) -> None:
        projection = build_projection(
            {"model": {"historical_attempts": 20.0, "historical_cost_usd": 2.0, "estimated_cost_per_attempt_usd": 0.1}},
            cases=600,
            protocols=4,
            stability_cases=120,
            additional_stability_repetitions=2,
            contingency=0.25,
        )

        self.assertEqual(projection["full_matrix_attempts_per_model"], 2400)
        self.assertEqual(projection["additional_stability_attempts_per_model"], 960)
        self.assertEqual(projection["total_attempts"], 3360)
        self.assertAlmostEqual(projection["projected_subtotal_usd"], 336.0)
        self.assertAlmostEqual(projection["projected_upper_bound_usd"], 420.0)


if __name__ == "__main__":
    unittest.main()
