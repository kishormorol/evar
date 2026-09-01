from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.adjudicate_human_pr_annotations import validate_export


class HumanPRAnnotationExportValidationTests(unittest.TestCase):
    def _row(self, candidate_id: str, annotator_id: str) -> dict[str, object]:
        return {
            "candidate_id": candidate_id,
            "queue_id": f"queue-{candidate_id}",
            "review_excerpt": "before",
            "merge_excerpt": "after",
            "annotation": {
                "eligible": True,
                "normalized_claim": "The parser accepts an empty name.",
                "claim_family": "missing_guard",
                "supported_at_review": True,
                "unsupported_at_merge": True,
                "exclusion_reason": None,
                "annotator_id": annotator_id,
            },
        }

    def _write(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_accepts_complete_export_matching_the_queue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = [self._row("one", "")]
            queue[0]["annotation"] = {}
            export = [self._row("one", "reviewer-a")]
            queue_path, export_path = root / "queue.jsonl", root / "export.jsonl"
            self._write(queue_path, queue)
            self._write(export_path, export)
            summary = validate_export(export_path, queue_path)
        self.assertTrue(summary["valid"])
        self.assertEqual(summary["candidate_count"], 1)
        self.assertEqual(summary["annotator_id"], "reviewer-a")

    def test_rejects_missing_candidates_and_changed_source_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = [self._row("one", ""), self._row("two", "")]
            for row in queue:
                row["annotation"] = {}
            queue_path, export_path = root / "queue.jsonl", root / "export.jsonl"
            self._write(queue_path, queue)
            self._write(export_path, [self._row("one", "reviewer-a")])
            with self.assertRaisesRegex(ValueError, "candidate sets differ"):
                validate_export(export_path, queue_path)
            changed = self._row("one", "reviewer-a")
            changed["review_excerpt"] = "changed"
            self._write(queue_path, [queue[0]])
            self._write(export_path, [changed])
            with self.assertRaisesRegex(ValueError, "payload differs"):
                validate_export(export_path, queue_path)

    def test_rejects_unknown_claim_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = self._row("one", "")
            queue["annotation"] = {}
            export = self._row("one", "reviewer-a")
            export["annotation"]["claim_family"] = "invented_family"
            queue_path, export_path = root / "queue.jsonl", root / "export.jsonl"
            self._write(queue_path, [queue])
            self._write(export_path, [export])
            with self.assertRaisesRegex(ValueError, "claim_family must be one of"):
                validate_export(export_path, queue_path)


if __name__ == "__main__":
    unittest.main()
