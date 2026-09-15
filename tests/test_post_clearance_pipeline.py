from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.adjudicate_human_pr_annotations import adjudicate, validate_export
from scripts.audit_human_pr_200_contamination import build_audit
from scripts.freeze_human_pr_200_model_inputs import validate_cases
from scripts.render_human_pr_200 import render
from scripts.select_human_pr_200 import select


class PostClearancePipelineTests(unittest.TestCase):
    def _source(self, number: int) -> dict[str, object]:
        repository = number % 50
        return {
            "candidate_id": f"candidate-{number:03d}",
            "language": ["Go", "Java", "JavaScript", "Python", "Rust", "TypeScript"][number % 6],
            "review_excerpt": f"before {number}",
            "merge_excerpt": f"after {number}",
            "review_commit": f"review-{number:03d}",
            "merge_commit": f"merge-{number:03d}",
            "source_comment_url": f"https://github.com/new/repo-{repository}/pull/{number}#discussion_r{number}",
            "source_repository": f"https://github.com/new/repo-{repository}",
            "source_pull_request": f"https://github.com/new/repo-{repository}/pull/{number}",
            "source_comment_id": number,
            "source_comment_author": f"author-{number}",
            "source_comment_body": "Please reject empty input.",
            "source_comment_path": "src/parser.py",
            "source_comment_line": 2,
        }

    def _annotation(self, reviewer: str, family: str = "missing_guard") -> dict[str, object]:
        return {
            "eligible": True,
            "normalized_claim": "The parser accepts empty input.",
            "claim_family": family,
            "supported_at_review": True,
            "unsupported_at_merge": True,
            "exclusion_reason": None,
            "annotator_id": reviewer,
        }

    def _write(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_synthetic_320_candidate_flow_produces_300_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue_rows, a_rows, b_rows = [], [], []
            for number in range(320):
                source = self._source(number)
                queue_rows.append({**source, "annotation": {}})
                a_rows.append({**source, "annotation": self._annotation("expert-a")})
                family = "stale_evidence" if number % 20 == 0 else "missing_guard"
                b_rows.append({**source, "annotation": self._annotation("expert-b", family)})

            queue = root / "queue.jsonl"
            annotator_a, annotator_b = root / "a.jsonl", root / "b.jsonl"
            self._write(queue, queue_rows)
            self._write(annotator_a, a_rows)
            self._write(annotator_b, b_rows)
            self.assertTrue(validate_export(annotator_a, queue)["valid"])
            self.assertTrue(validate_export(annotator_b, queue)["valid"])

            resolved = root / "resolved.jsonl"
            disagreements = root / "disagreements.jsonl"
            audit = root / "adjudication-audit.json"
            first = adjudicate(annotator_a, annotator_b, resolved, disagreements, audit)
            self.assertEqual(first["disagreements"], 16)

            disagreement_rows = [json.loads(line) for line in disagreements.read_text().splitlines()]
            adjudication_rows = [
                {**row, "annotation": self._annotation("adjudicator")}
                for row in disagreement_rows
            ]
            adjudications = root / "adjudications.jsonl"
            self._write(adjudications, adjudication_rows)
            self.assertTrue(validate_export(adjudications, disagreements)["valid"])
            final = adjudicate(
                annotator_a,
                annotator_b,
                resolved,
                disagreements,
                audit,
                adjudications,
            )
            self.assertEqual(final["unresolved"], 0)
            self.assertEqual(final["resolved_candidates"], 320)

            resolved_rows = [json.loads(line) for line in resolved.read_text().splitlines()]
            selected_rows = select(resolved_rows, target=300, min_repositories=40, max_per_repo=6)
            selected = root / "final_300.jsonl"
            self._write(selected, selected_rows)
            frozen = root / "frozen"
            render_summary = render(selected_rows, frozen)
            self.assertEqual(render_summary["case_count"], 600)

            protected = root / "protected.jsonl"
            self._write(
                protected,
                [
                    {
                        **self._source(999),
                        "source_repository": "https://github.com/old/protected",
                    }
                ],
            )
            contamination = build_audit(selected, [protected])
            self.assertTrue(contamination["passed"])
            frozen_rows = [json.loads(line) for line in (frozen / "cases.jsonl").read_text().splitlines()]
            case_summary = validate_cases(frozen_rows)
            self.assertEqual(case_summary["source_comment_count"], 300)


if __name__ == "__main__":
    unittest.main()

