from __future__ import annotations

import unittest
from pathlib import Path

from evar.benchmark.loader import load_jsonl_cases
from evar.benchmark.schema import GroundTruth


class ExternalPR20FixtureTests(unittest.TestCase):
    def test_external_pr_20_fixture_loads_with_balanced_labels(self) -> None:
        cases = load_jsonl_cases(Path("benchmarks/external_pr_20/cases.jsonl"))

        self.assertEqual(len(cases), 20)
        self.assertEqual(sum(case.ground_truth == GroundTruth.SUPPORTED for case in cases), 10)
        self.assertEqual(sum(case.ground_truth == GroundTruth.UNSUPPORTED for case in cases), 10)
        for case in cases:
            self.assertTrue(case.repo_path.exists(), case.case_id)


if __name__ == "__main__":
    unittest.main()
