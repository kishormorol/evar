from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.render_human_pr_200 import accepted, render


class HumanPR200RendererTests(unittest.TestCase):
    def _row(self, **annotation: object) -> dict[str, object]:
        row = {
            "candidate_id": "hpr-test",
            "review_excerpt": "review excerpt",
            "merge_excerpt": "merge excerpt",
            "review_commit": "a" * 40,
            "merge_commit": "b" * 40,
            "source_comment_url": "https://github.com/acme/widget/pull/1#discussion_r1",
            "source_repository": "https://github.com/acme/widget",
            "source_pull_request": "https://github.com/acme/widget/pull/1",
            "source_comment_id": 1,
            "source_comment_author": "reviewer",
            "source_comment_body": "Please fix this behavior.",
            "source_comment_path": "src/widget.py",
            "source_comment_line": 2,
            "annotation": annotation,
            "annotation_provenance": {
                "status": "resolved",
                "resolution": "agreement",
                "annotator_ids": ["reviewer-a", "reviewer-b"],
                "adjudicator_id": None,
            },
        }
        candidate_id = annotation.pop("candidate_id", None)
        if candidate_id:
            row["candidate_id"] = candidate_id
        return row

    def test_only_fully_adjudicated_rows_are_accepted(self) -> None:
        base = {
            "eligible": True,
            "normalized_claim": "widget uses the fallback",
            "claim_family": "behavior_inversion",
            "supported_at_review": True,
            "unsupported_at_merge": True,
        }
        self.assertTrue(accepted(self._row(**base)))
        self.assertFalse(accepted(self._row(**{**base, "unsupported_at_merge": False})))
        unprovenanced = self._row(**base)
        unprovenanced.pop("annotation_provenance")
        self.assertFalse(accepted(unprovenanced))

    def test_renderer_creates_temporal_pair_and_rejects_pending_rows(self) -> None:
        rows = [
            self._row(
                eligible=True,
                normalized_claim="widget uses the fallback",
                claim_family="behavior_inversion",
                supported_at_review=True,
                unsupported_at_merge=True,
            ),
            self._row(
                candidate_id="hpr-pending",
                eligible=None,
                normalized_claim=None,
                claim_family=None,
                supported_at_review=None,
                unsupported_at_merge=None,
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "human_pr_200"
            audit = render(rows, output)
            self.assertEqual(audit["accepted_source_comments"], 1)
            self.assertEqual(audit["case_count"], 2)
            cases = [json.loads(line) for line in (output / "cases.jsonl").read_text().splitlines()]
            self.assertEqual([case["ground_truth"] for case in cases], ["SUPPORTED", "UNSUPPORTED"])
            self.assertEqual(cases[0]["paired_case_id"], cases[1]["case_id"])
            self.assertEqual(cases[1]["paired_case_id"], cases[0]["case_id"])
            self.assertEqual(
                (output / "repos/case_001/context/target.txt").read_text(), "review excerpt"
            )


if __name__ == "__main__":
    unittest.main()
