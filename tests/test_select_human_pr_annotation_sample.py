from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
