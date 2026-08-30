from __future__ import annotations

import json
import unittest
from pathlib import Path

from evar.benchmark.human_pr_candidates import (
    RepositorySpec,
    acquire_candidates,
    anchor_changed,
    build_candidate,
    is_candidate_comment,
    load_repository_specs,
    map_line,
    priority_score,
)


def _comment(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": 123,
        "body": "This condition should use the fallback when the value is absent.",
        "path": "src/example.py",
        "original_line": 2,
        "pull_request_url": "https://api.github.com/repos/acme/widget/pulls/7",
        "html_url": "https://github.com/acme/widget/pull/7#discussion_r123",
        "original_commit_id": "a" * 40,
        "author_association": "MEMBER",
        "created_at": "2026-01-02T03:04:05Z",
        "diff_hunk": "@@ -1,2 +1,2 @@",
        "user": {"login": "reviewer", "type": "User"},
    }
    value.update(overrides)
    return value


class HumanPRCandidateTests(unittest.TestCase):
    def test_repository_registry_is_multilingual_and_unique(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repositories.json"
            path.write_text(
                json.dumps(
                    {
                        "repositories": [
                            {"repository": "acme/python", "language": "Python"},
                            {"repository": "acme/rust", "language": "Rust"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                load_repository_specs(path),
                [RepositorySpec("acme/python", "Python"), RepositorySpec("acme/rust", "Rust")],
            )

    def test_repository_registry_rejects_duplicates(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repositories.json"
            path.write_text(
                json.dumps(
                    {
                        "repositories": [
                            {"repository": "acme/widget", "language": "Python"},
                            {"repository": "acme/widget", "language": "Python"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate repository"):
                load_repository_specs(path)

    def test_comment_filter_rejects_bots_low_information_and_existing_ids(self) -> None:
        self.assertTrue(is_candidate_comment(_comment(), excluded_ids=set()))
        self.assertFalse(is_candidate_comment(_comment(id=123), excluded_ids={123}))
        self.assertFalse(
            is_candidate_comment(
                _comment(user={"login": "dependabot[bot]", "type": "Bot"}), excluded_ids=set()
            )
        )
        self.assertFalse(is_candidate_comment(_comment(body="nit"), excluded_ids=set()))
        self.assertFalse(is_candidate_comment(_comment(path="image.png"), excluded_ids=set()))

    def test_map_line_and_anchor_change_follow_an_inserted_fix(self) -> None:
        before = ["header", "if value:", "    return value", "tail"]
        after = ["header", "if value is not None:", "    return value", "tail"]
        mapped = map_line(before, after, 2)
        self.assertEqual(mapped, 2)
        self.assertTrue(anchor_changed(before, after, 2, mapped))

    def test_priority_prefers_changed_substantive_suggestions(self) -> None:
        plain = _comment(body="Please reconsider this implementation because it is difficult to follow.")
        suggestion = _comment(
            body="This should preserve the fallback.\n```suggestion\nreturn value or fallback\n```"
        )
        self.assertGreater(
            priority_score(suggestion, changed_anchor=True),
            priority_score(plain, changed_anchor=True),
        )

    def test_build_candidate_preserves_provenance_without_assigning_label(self) -> None:
        comment = _comment()
        pull = {
            "number": 7,
            "html_url": "https://github.com/acme/widget/pull/7",
            "title": "Fix fallback",
            "merged_at": "2026-01-03T03:04:05Z",
            "merge_commit_sha": "b" * 40,
        }
        row = build_candidate(
            RepositorySpec("acme/widget", "Python"),
            comment,
            pull,
            b"header\nif value:\n    return value\n",
            b"header\nif value is not None:\n    return value\n",
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["review_commit"], "a" * 40)
        self.assertEqual(row["merge_commit"], "b" * 40)
        self.assertEqual(row["selection_status"], "pending_annotation")
        self.assertEqual(
            row["annotation"],
            {
                "eligible": None,
                "normalized_claim": None,
                "claim_family": None,
                "exclusion_reason": None,
                "annotator_1": None,
                "annotator_2": None,
                "adjudicator": None,
            },
        )
        self.assertNotIn("ground_truth", row)

    def test_acquisition_skips_inaccessible_pull_requests(self) -> None:
        class MissingPullClient:
            def get_json(self, url: str) -> object:
                del url
                return [_comment()]

            def get_pull(self, url: str) -> dict[str, object]:
                raise RuntimeError(f"Pull is inaccessible: {url}")

        from datetime import datetime, timezone

        rows, audit = acquire_candidates(
            [RepositorySpec("acme/widget", "Python")],
            client=MissingPullClient(),  # type: ignore[arg-type]
            excluded_ids=set(),
            cutoff=datetime(2026, 8, 30, tzinfo=timezone.utc),
            pages=1,
            per_repo=1,
        )
        self.assertEqual(rows, [])
        self.assertEqual(audit["acme/widget"]["comments_seen"], 1)


if __name__ == "__main__":
    unittest.main()
