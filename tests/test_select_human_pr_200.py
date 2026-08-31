from __future__ import annotations

import unittest

from scripts.select_human_pr_200 import select


def row(number: int, repository: int, language: str, family: str) -> dict[str, object]:
    return {
        "candidate_id": f"candidate-{number}",
        "source_repository": f"https://github.com/acme/repo-{repository}",
        "language": language,
        "annotation": {
            "eligible": True,
            "normalized_claim": f"claim {number}",
            "claim_family": family,
            "supported_at_review": True,
            "unsupported_at_merge": True,
        },
        "annotation_provenance": {
            "status": "resolved",
            "resolution": "agreement",
            "annotator_ids": ["a", "b"],
            "adjudicator_id": None,
        },
    }


class HumanPRSelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_balanced_and_repo_capped(self) -> None:
        rows = [
            row(i, i % 20, ["Python", "Java", "TypeScript"][i % 3], ["missing_guard", "stale_evidence"][i % 2])
            for i in range(140)
        ]
        first = select(rows, target=100, max_per_repo=6, min_repositories=20, seed=53)
        second = select(list(reversed(rows)), target=100, max_per_repo=6, min_repositories=20, seed=53)
        self.assertEqual([item["candidate_id"] for item in first], [item["candidate_id"] for item in second])
        counts: dict[str, int] = {}
        for item in first:
            repo = str(item["source_repository"])
            counts[repo] = counts.get(repo, 0) + 1
        self.assertEqual(len(counts), 20)
        self.assertLessEqual(max(counts.values()), 6)

    def test_selection_fails_closed_when_labels_are_insufficient(self) -> None:
        with self.assertRaisesRegex(ValueError, "resolved eligible"):
            select([row(1, 1, "Python", "missing_guard")], target=2, min_repositories=1)


if __name__ == "__main__":
    unittest.main()
