from __future__ import annotations

import unittest
from collections import Counter, defaultdict
from pathlib import Path

from evar.benchmark.loader import load_jsonl_cases
from evar.benchmark.schema import ClaimFamily, GroundTruth


class Manual10FixtureTests(unittest.TestCase):
    def test_manual_10_fixture_is_balanced_and_valid(self) -> None:
        cases = load_jsonl_cases(Path("benchmarks/manual_10/cases.jsonl"))

        self.assertEqual(len(cases), 10)
        self.assertEqual(Counter(case.ground_truth for case in cases)[GroundTruth.SUPPORTED], 5)
        self.assertEqual(Counter(case.ground_truth for case in cases)[GroundTruth.UNSUPPORTED], 5)
        self.assertEqual({case.claim_family for case in cases}, set(ClaimFamily))
        self.assertTrue(all(case.repo_path.exists() for case in cases))

        by_family: dict[ClaimFamily, set[GroundTruth]] = defaultdict(set)
        for case in cases:
            by_family[case.claim_family].add(case.ground_truth)

        for family in ClaimFamily:
            self.assertEqual(by_family[family], {GroundTruth.SUPPORTED, GroundTruth.UNSUPPORTED})
