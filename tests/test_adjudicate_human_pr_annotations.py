from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.adjudicate_human_pr_annotations import adjudicate
from scripts.render_human_pr_200 import accepted


class HumanPRAdjudicationTests(unittest.TestCase):
    def _row(self, candidate_id: str, annotator: str, claim: str = "guard rejects empty input") -> dict[str, object]:
        return {
            "candidate_id": candidate_id,
            "review_excerpt": "before",
            "merge_excerpt": "after",
            "annotation": {
                "eligible": True,
                "normalized_claim": claim,
                "claim_family": "missing_guard",
                "supported_at_review": True,
                "unsupported_at_merge": True,
                "exclusion_reason": None,
                "annotator_id": annotator,
            },
        }

    def _write(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def _run(
        self,
        root: Path,
        a_rows: list[dict[str, object]],
        b_rows: list[dict[str, object]],
        adjudications: list[dict[str, object]] | None = None,
    ) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
        a_path, b_path = root / "a.jsonl", root / "b.jsonl"
        self._write(a_path, a_rows)
        self._write(b_path, b_rows)
        adjudications_path = None
        if adjudications is not None:
            adjudications_path = root / "adjudications.jsonl"
            self._write(adjudications_path, adjudications)
        resolved, disagreements, audit = root / "resolved.jsonl", root / "disagreements.jsonl", root / "audit.json"
        summary = adjudicate(a_path, b_path, resolved, disagreements, audit, adjudications_path)
        resolved_rows = [json.loads(line) for line in resolved.read_text().splitlines()]
        disagreement_rows = [json.loads(line) for line in disagreements.read_text().splitlines()]
        return summary, resolved_rows, disagreement_rows

    def test_exact_agreement_is_resolved_with_dual_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary, resolved, disagreements = self._run(
                Path(directory), [self._row("one", "a")], [self._row("one", "b")]
            )
        self.assertEqual(summary["exact_agreements"], 1)
        self.assertEqual(disagreements, [])
        self.assertTrue(accepted(resolved[0]))
        self.assertEqual(resolved[0]["annotation_provenance"]["resolution"], "agreement")

    def test_disagreement_is_queued_and_can_be_adjudicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = self._row("one", "a", "first claim")
            b = self._row("one", "b", "second claim")
            summary, resolved, disagreements = self._run(root, [a], [b])
            self.assertEqual(summary["unresolved"], 1)
            self.assertEqual(resolved, [])
            self.assertEqual(len(disagreements[0]["independent_annotations"]), 2)
            self.assertTrue(
                all("annotator_id" not in item for item in disagreements[0]["independent_annotations"])
            )
            decision = self._row("one", "judge", "adjudicated claim")
            summary, resolved, _ = self._run(root, [a], [b], [decision])
        self.assertEqual(summary["adjudicated"], 1)
        self.assertTrue(accepted(resolved[0]))
        self.assertEqual(resolved[0]["annotation_provenance"]["adjudicator_id"], "judge")

    def test_rejects_same_reviewer_and_mismatched_candidate_sets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "distinct"):
                self._run(root, [self._row("one", "same")], [self._row("one", "same")])
            with self.assertRaisesRegex(ValueError, "candidate sets differ"):
                self._run(root, [self._row("one", "a")], [self._row("two", "b")])


if __name__ == "__main__":
    unittest.main()
