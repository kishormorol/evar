from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from evar.agents.model_critic import parse_critic_decision
from evar.agents.model_reviewer import ModelOutputError, parse_reviewer_receipts
from evar.protocols.evar import CriticDecision
from evar.run_model import main
from evar.verifier.models import EvidenceType


class ModelAdapterTests(unittest.TestCase):
    def test_parse_reviewer_receipts_accepts_strict_json(self) -> None:
        receipts = parse_reviewer_receipts(
            json.dumps(
                {
                    "receipts": [
                        {
                            "claim_id": "c1",
                            "claim": "claim",
                            "evidence_type": "behavioral",
                            "file": "calculator.py",
                            "line_start": 1,
                            "line_end": 2,
                            "verification_command": "python -m pytest test_supported.py -q",
                            "expected_exit_code": 0,
                            "expected_stdout_contains": "PASS",
                            "falsification_condition": "FAIL",
                        }
                    ]
                }
            )
        )

        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].claim_id, "c1")
        self.assertEqual(receipts[0].evidence_type, EvidenceType.BEHAVIORAL)

    def test_parse_reviewer_receipts_rejects_malformed_output(self) -> None:
        with self.assertRaises(ModelOutputError):
            parse_reviewer_receipts("not json")

    def test_parse_critic_decision_accepts_allowed_decision(self) -> None:
        decision = parse_critic_decision('{"decision":"REQUEST_STRONGER_WITNESS"}')

        self.assertEqual(decision, CriticDecision.REQUEST_STRONGER_WITNESS)

    def test_parse_critic_decision_rejects_unknown_decision(self) -> None:
        with self.assertRaises(ModelOutputError):
            parse_critic_decision('{"decision":"MAYBE"}')

    def test_run_model_dry_run_validates_cases_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.jsonl"
            cases.write_text(json.dumps(_raw_case(Path(tmp))) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--cases", str(cases), "--dry-run"])

        self.assertEqual(exit_code, 0)
        row = json.loads(stdout.getvalue())
        self.assertTrue(row["dry_run"])
        self.assertEqual(row["case_count"], 1)
        self.assertEqual(row["parsed_receipts"], 0)


def _raw_case(repo: Path) -> dict[str, object]:
    return {
        "case_id": "case-1",
        "repo_path": str(repo),
        "task_description": "Review the guard.",
        "claim": "handler is missing an input guard",
        "ground_truth": "UNSUPPORTED",
        "ground_truth_evidence": "The guard exists in sample.py.",
        "validation_command": ["python", "-m", "unittest"],
        "claim_family": "missing_guard",
    }
