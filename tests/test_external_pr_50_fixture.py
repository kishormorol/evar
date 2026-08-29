from __future__ import annotations

import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path

from evar.benchmark.loader import load_jsonl_cases
from evar.benchmark.schema import GroundTruth


class ExternalPR50FixtureTests(unittest.TestCase):
    def test_fixture_is_balanced_and_commit_grounded(self) -> None:
        path = Path("benchmarks/external_pr_50/cases.jsonl")
        raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        cases = load_jsonl_cases(path)

        self.assertEqual(len(cases), 50)
        self.assertEqual(Counter(case.ground_truth for case in cases), {
            GroundTruth.SUPPORTED: 25,
            GroundTruth.UNSUPPORTED: 25,
        })
        self.assertEqual(set(Counter(case.claim_family for case in cases).values()), {10})
        self.assertEqual(set(Counter(row["source_repository"] for row in raw).values()), {10})
        self.assertTrue(all(len(row["source_commit"]) == 40 for row in raw))

        grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        for row in raw:
            grouped[(row["source_repository"], row["claim_family"])].append(row)
            repo = Path(row["repo_path"])
            self.assertEqual([item.name for item in repo.iterdir()], ["upstream.patch"])
            self.assertLess((repo / "upstream.patch").stat().st_size, 30_000)
        self.assertEqual(len(grouped), 25)
        for pair in grouped.values():
            self.assertEqual({row["ground_truth"] for row in pair}, {"SUPPORTED", "UNSUPPORTED"})
            self.assertEqual(len({row["source_commit"] for row in pair}), 1)


if __name__ == "__main__":
    unittest.main()
