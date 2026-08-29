from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from evar.agents.model_critic import CriticPromptContext, _critic_user_prompt, parse_critic_decision
from evar.agents.model_reviewer import (
    ModelOutputError,
    _repository_context,
    _review_user_prompt,
    parse_reviewer_receipts,
)
from evar.eval.metrics import compute_fcr_scr
from evar.prompts import load_prompt
from evar.protocols.evar import CriticDecision, TextEvidence
from evar.run_model import main
from evar.verifier.models import EvidenceReceipt, EvidenceRole, EvidenceType, VerificationResult, VerificationStatus


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
                            "evidence_role": "supports_claim",
                            "file": "calculator.py",
                            "line_start": 1,
                            "line_end": 2,
                            "verification_command": "python -m pytest test_supported.py -q",
                            "expected_exit_code": 0,
                            "expected_stdout_contains": "EVAR_WITNESS_PASS",
                            "falsification_condition": "FAIL",
                        }
                    ]
                }
            )
        )

        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].claim_id, "c1")
        self.assertEqual(receipts[0].evidence_type, EvidenceType.BEHAVIORAL)
        self.assertEqual(receipts[0].evidence_role, EvidenceRole.SUPPORTS_CLAIM)

    def test_parse_reviewer_receipts_defaults_legacy_evidence_role_to_supports(self) -> None:
        receipts = parse_reviewer_receipts(
            json.dumps(
                {
                    "receipts": [
                        {
                            "claim_id": "c1",
                            "claim": "claim",
                            "evidence_type": "structural",
                            "file": "sample.py",
                            "line_start": 1,
                            "line_end": 1,
                            "verification_command": None,
                            "expected_exit_code": None,
                            "expected_stdout_contains": "return value",
                            "falsification_condition": "FAIL",
                        }
                    ]
                }
            )
        )

        self.assertEqual(receipts[0].evidence_role, EvidenceRole.SUPPORTS_CLAIM)

    def test_parse_reviewer_receipts_rejects_malformed_output(self) -> None:
        with self.assertRaises(ModelOutputError):
            parse_reviewer_receipts("not json")

    def test_parse_reviewer_receipts_normalizes_empty_optional_strings(self) -> None:
        receipts = parse_reviewer_receipts(
            json.dumps(
                {
                    "receipts": [
                        {
                            "claim_id": "c1",
                            "claim": "claim",
                            "evidence_type": "structural",
                            "file": "sample.py",
                            "line_start": 1,
                            "line_end": 1,
                            "verification_command": "",
                            "expected_exit_code": None,
                            "expected_stdout_contains": "",
                            "falsification_condition": "FAIL",
                        }
                    ]
                }
            )
        )

        self.assertIsNone(receipts[0].verification_command)
        self.assertIsNone(receipts[0].expected_stdout_contains)

    def test_parse_reviewer_receipts_defaults_empty_falsification_condition(self) -> None:
        receipts = parse_reviewer_receipts(
            json.dumps(
                {
                    "receipts": [
                        {
                            "claim_id": "c1",
                            "claim": "claim",
                            "evidence_type": "structural",
                            "file": "sample.py",
                            "line_start": 1,
                            "line_end": 1,
                            "verification_command": None,
                            "expected_exit_code": None,
                            "expected_stdout_contains": "return value",
                            "falsification_condition": "",
                        }
                    ]
                }
            )
        )

        self.assertEqual(
            receipts[0].falsification_condition,
            "The referenced evidence does not support the claim.",
        )

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

    def test_repository_context_includes_relative_paths_and_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "calculator.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")

            context = _repository_context(repo)

        self.assertIn("--- calculator.py ---", context)
        self.assertIn("1: def divide(a, b):", context)
        self.assertIn("2:     return a / b", context)

    def test_repository_context_excludes_jsonl_benchmark_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "cases.jsonl").write_text('{"ground_truth":"SUPPORTED"}\n', encoding="utf-8")

            context = _repository_context(repo)

        self.assertNotIn("ground_truth", context)

    def test_reviewer_prompt_lists_valid_receipt_file_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            package = repo / "zipp"
            package.mkdir()
            (package / "__init__.py").write_text("class Path:\n    pass\n", encoding="utf-8")

            prompt = _review_user_prompt("Review Path behavior.", repo)

        self.assertIn("Valid file paths for EvidenceReceipt.file:", prompt)
        self.assertIn("- zipp/__init__.py", prompt)
        self.assertIn("file must be exactly one path from the valid file path list", prompt)

    def test_reviewer_prompt_prefers_implementation_over_docstring_counterevidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "path.py").write_text(
                "def _ancestry(path):\n"
                "    \"\"\"Example may be confusing.\"\"\"\n"
                "    return path\n",
                encoding="utf-8",
            )

            prompt = _review_user_prompt("Review _ancestry behavior.", repo)

        self.assertIn("Prefer receipts whose evidence_role directly matches executable code semantics", prompt)
        self.assertIn("do not submit docstring-only counterevidence", prompt)

    def test_evar_reviewer_prompt_prefers_structural_evidence_for_call_chains(self) -> None:
        prompt = load_prompt("reviewer_evar_v1.txt").text

        self.assertIn("wrapper/call-chain relationship", prompt)
        self.assertIn("use structural evidence, not behavioral evidence", prompt)

    def test_eval_table_counts_configured_final_actionable_records(self) -> None:
        summary = compute_fcr_scr(
            [
                {
                    "protocol": "ar",
                    "run_status": "ok",
                    "ground_truth": "SUPPORTED",
                    "final_actionable": True,
                },
                {
                    "protocol": "ar",
                    "run_status": "ok",
                    "ground_truth": "UNSUPPORTED",
                    "final_actionable": False,
                },
            ]
        )

        self.assertEqual(summary.supported_actionable, 1)
        self.assertEqual(summary.unsupported_actionable, 0)
        self.assertEqual(summary.scr, 1.0)
        self.assertEqual(summary.fcr, 0.0)

    def test_ar_critic_prompt_does_not_frame_missing_verification_as_failure(self) -> None:
        prompt = _critic_user_prompt(_critic_context(), protocol="ar")

        self.assertIn("External verification: not used by AR.", prompt)
        self.assertNotIn("Verification status: UNVERIFIABLE", prompt)

    def test_ar_text_critic_prompt_includes_textual_evidence(self) -> None:
        prompt = _critic_user_prompt(
            _critic_context(),
            protocol="ar_text",
            text_evidence=TextEvidence(
                claim="claim",
                file="sample.py",
                line_start=1,
                line_end=1,
                explanation="text only",
                quoted_or_paraphrased_support="return bad_value",
                falsification_condition="return good_value",
            ),
        )

        self.assertIn("Textual evidence:", prompt)
        self.assertIn("return bad_value", prompt)
        self.assertNotIn("Verification status: UNVERIFIABLE", prompt)

    def test_evar_critic_prompt_includes_verifier_observations(self) -> None:
        prompt = _critic_user_prompt(_critic_context(), protocol="evar_hard")

        self.assertIn("Verification status: UNVERIFIABLE", prompt)
        self.assertIn("Verification stdout:", prompt)
        self.assertIn("Verifier note:", prompt)


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


def _critic_context() -> CriticPromptContext:
    return CriticPromptContext(
        task="Review this claim.",
        receipt=EvidenceReceipt(
            claim_id="c1",
            claim="claim",
            evidence_type=EvidenceType.STRUCTURAL,
            evidence_role=EvidenceRole.SUPPORTS_CLAIM,
            file="sample.py",
            line_start=1,
            line_end=1,
            verification_command=None,
            expected_exit_code=None,
            expected_stdout_contains="return bad_value",
            falsification_condition="return good_value",
        ),
        verification_result=VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Not used by protocol.",
        ),
    )
