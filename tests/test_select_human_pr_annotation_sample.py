from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.select_human_pr_annotation_sample import select


class HumanPRAnnotationSampleTests(unittest.TestCase):
    def test_selects_balanced_languages_and_caps_repositories(self) -> None:
        rows = []
        for language in ("Go", "Rust"):
            for repo_index in range(3):
                for item_index in range(3):
                    rows.append(
                        {
                            "language": language,
                            "source_repository": f"https://github.com/acme/{language.lower()}{repo_index}",
                            "candidate_id": f"{language}-{repo_index}-{item_index}",
                            "priority_score": item_index,
                        }
                    )
        selected = select(rows, per_language=3, max_per_repo=1)
        self.assertEqual(len(selected), 6)
        self.assertEqual({row["language"] for row in selected}, {"Go", "Rust"})
        self.assertEqual(
            max(sum(row["source_repository"] == repo for row in selected) for repo in {row["source_repository"] for row in selected}),
            1,
        )

    def test_frozen_pilot_is_balanced_and_matches_its_manifest(self) -> None:
        queue_path = Path("benchmarks/human_pr_200/pilot_queue_18.jsonl")
        manifest = json.loads(
            Path("benchmarks/human_pr_200/pilot_queue_18_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        rows = [
            json.loads(line)
            for line in queue_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(rows), 18)
        self.assertEqual(
            Counter(row["language"] for row in rows),
            Counter(manifest["language_counts"]),
        )
        self.assertEqual(len({row["source_repository"] for row in rows}), 18)
        self.assertEqual(
            hashlib.sha256(queue_path.read_bytes()).hexdigest(),
            manifest["output_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
