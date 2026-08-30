from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evar.model_backend import ModelResponse
from scripts.llm_annotate_human_pr import ANNOTATION_SCHEMA, annotate, user_prompt


class FakeBackend:
    model_name = "fake-annotator"

    def generate(self, system_prompt: str, user_prompt: str, *, response_schema: object | None = None) -> ModelResponse:
        assert "advisory benchmark annotator" in system_prompt
        assert "Reviewed snapshot" in user_prompt
        assert response_schema == ANNOTATION_SCHEMA
        text = json.dumps(
            {
                "eligible": True,
                "normalized_claim": "the fallback is missing",
                "claim_family": "missing_guard",
                "supported_at_review": True,
                "unsupported_at_merge": True,
                "rationale": "The excerpts show the guard being added.",
                "confidence": 0.9,
            }
        )
        return ModelResponse(text, json.loads(text), self.model_name, 10, 20, 0.01)


class LLMAnnotationTests(unittest.TestCase):
    def _row(self) -> dict[str, object]:
        return {
            "candidate_id": "hpr-test",
            "language": "Python",
            "source_repository": "https://github.com/acme/widget",
            "source_pull_request": "https://github.com/acme/widget/pull/1",
            "source_comment_body": "Please add the missing guard.",
            "source_comment_path": "widget.py",
            "source_comment_line": 2,
            "review_commit": "a" * 40,
            "merge_commit": "b" * 40,
            "review_excerpt": "review",
            "merge_excerpt": "merge",
        }

    def test_prompt_contains_temporal_context(self) -> None:
        prompt = user_prompt(self._row())
        self.assertIn("Reviewed snapshot", prompt)
        self.assertIn("Merged snapshot", prompt)
        self.assertIn("Please add the missing guard", prompt)

    def test_annotation_is_separate_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "annotations.jsonl"
            annotate([self._row()], backend=FakeBackend(), output=output)  # type: ignore[arg-type]
            annotate([self._row()], backend=FakeBackend(), output=output)  # type: ignore[arg-type]
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "ok")
            self.assertEqual(rows[0]["annotation"]["claim_family"], "missing_guard")
            self.assertNotIn("ground_truth", rows[0])


if __name__ == "__main__":
    unittest.main()
