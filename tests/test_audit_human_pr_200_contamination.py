from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_human_pr_200_contamination import build_audit


class HumanPR200ContaminationAuditTests(unittest.TestCase):
    def _write(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def _row(self, number: int, repository: str = "https://github.com/new/repo") -> dict[str, object]:
        return {
            "candidate_id": f"candidate-{number}",
            "source_comment_url": f"https://github.com/new/repo/pull/{number}#discussion_r{number}",
            "source_pull_request": f"https://github.com/new/repo/pull/{number}",
            "source_repository": repository,
            "review_commit": f"review-{number}",
            "merge_commit": f"merge-{number}",
        }

    def test_passes_for_disjoint_valid_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected, protected = root / "selected.jsonl", root / "protected.jsonl"
            self._write(selected, [self._row(1), self._row(2)])
            self._write(protected, [self._row(9, "https://github.com/old/repo")])
            audit = build_audit(selected, [protected], expected_selected=2)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["protected_overlap"], {})

    def test_fails_on_protected_repository_and_duplicate_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected, protected = root / "selected.jsonl", root / "protected.jsonl"
            rows = [self._row(1), self._row(2)]
            rows[1]["source_pull_request"] = rows[0]["source_pull_request"]
            self._write(selected, rows)
            self._write(protected, [self._row(9)])
            audit = build_audit(selected, [protected], expected_selected=2)
        self.assertFalse(audit["passed"])
        self.assertIn("source_pull_request", audit["duplicate_identifiers"])
        self.assertIn("source_repository", audit["protected_overlap"])


if __name__ == "__main__":
    unittest.main()

