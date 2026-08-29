from __future__ import annotations

import unittest
from pathlib import Path

from evar.benchmark.loader import load_jsonl_cases
from evar.benchmark.schema import GroundTruth


class ExternalPR10FixtureTests(unittest.TestCase):
    def test_external_pr_10_fixture_loads_with_balanced_labels(self) -> None:
        cases = load_jsonl_cases(Path("benchmarks/external_pr_10/cases.jsonl"))

        self.assertEqual(len(cases), 10)
        self.assertEqual(sum(case.ground_truth == GroundTruth.SUPPORTED for case in cases), 5)
        self.assertEqual(sum(case.ground_truth == GroundTruth.UNSUPPORTED for case in cases), 5)
        for case in cases:
            self.assertTrue(case.repo_path.exists(), case.case_id)


if __name__ == "__main__":
    unittest.main()
