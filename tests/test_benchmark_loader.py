from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evar.benchmark.loader import BenchmarkValidationError, load_jsonl_cases, validate_case
from evar.benchmark.schema import ClaimFamily, GroundTruth


class BenchmarkLoaderTests(unittest.TestCase):
    def test_load_jsonl_cases_validates_and_normalizes_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            cases_path = Path(tmp) / "cases.jsonl"
            cases_path.write_text(json.dumps(_raw_case(repo)) + "\n", encoding="utf-8")

            cases = load_jsonl_cases(cases_path)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].case_id, "case-1")
        self.assertEqual(cases[0].repo_path, repo)
        self.assertEqual(cases[0].ground_truth, GroundTruth.SUPPORTED)
        self.assertEqual(cases[0].claim_family, ClaimFamily.BEHAVIOR_INVERSION)
        self.assertEqual(cases[0].validation_command, ("python", "-m", "unittest"))
        self.assertEqual(cases[0].seed_findings[0].id, "case-1")
        self.assertEqual(cases[0].seed_findings[0].description, "add subtracts instead of adding")
        self.assertEqual(cases[0].text_evidence_by_finding_id, {})

    def test_task_case_does_not_expose_ground_truth_or_expected_answers(self) -> None:
        case = validate_case(_raw_case(Path("repo")))
        task_case = case.to_task_case()

        self.assertFalse(hasattr(task_case, "ground_truth"))
        self.assertFalse(hasattr(task_case, "ground_truth_evidence"))
        self.assertEqual(task_case.text_evidence_by_finding_id, {})
        self.assertEqual(task_case.claim, case.claim)

    def test_validate_case_rejects_missing_required_fields(self) -> None:
        raw = _raw_case(Path("repo"))
        del raw["claim"]

        with self.assertRaisesRegex(BenchmarkValidationError, "missing required fields: claim"):
            validate_case(raw)

    def test_validate_case_rejects_unknown_claim_family(self) -> None:
        raw = _raw_case(Path("repo"))
        raw["claim_family"] = "unknown"

        with self.assertRaisesRegex(BenchmarkValidationError, "claim_family must be one of"):
            validate_case(raw)

    def test_validate_case_rejects_unknown_ground_truth(self) -> None:
        raw = _raw_case(Path("repo"))
        raw["ground_truth"] = "MAYBE"

        with self.assertRaisesRegex(BenchmarkValidationError, "ground_truth must be"):
            validate_case(raw)

    def test_validate_case_rejects_empty_validation_command(self) -> None:
        raw = _raw_case(Path("repo"))
        raw["validation_command"] = []

        with self.assertRaisesRegex(BenchmarkValidationError, "validation_command"):
            validate_case(raw)


def _raw_case(repo: Path) -> dict[str, object]:
    return {
        "case_id": "case-1",
        "repo_path": str(repo),
        "task_description": "Review the add helper.",
        "claim": "add subtracts instead of adding",
        "ground_truth": "SUPPORTED",
        "ground_truth_evidence": "sample.py line 2 returns a - b",
        "validation_command": ["python", "-m", "unittest"],
        "claim_family": "behavior_inversion",
    }
