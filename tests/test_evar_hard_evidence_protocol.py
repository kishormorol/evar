from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.protocols.evar import (
    CriticDecision,
    EVARHardEvidenceProtocol,
    FakeCritic,
    FakeReviewer,
)
from evar.verifier.models import EvidenceReceipt, EvidenceRole, EvidenceType, VerificationStatus


class EVARHardEvidenceProtocolTests(unittest.TestCase):
    def test_verified_and_accepted_true_claim_is_actionable(self) -> None:
        result = EVARHardEvidenceProtocol(
            FakeReviewer([SUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual(len(result.accepted_findings), 1)
        self.assertTrue(result.findings[0].actionable)
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.findings[0].critic_decision, CriticDecision.ACCEPT)

    def test_failed_verification_overrides_critic_acceptance(self) -> None:
        result = EVARHardEvidenceProtocol(
            FakeReviewer([UNSUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual(result.accepted_findings, [])
        self.assertEqual(len(result.rejected_findings), 1)
        self.assertFalse(result.findings[0].actionable)
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.FAILED)
        self.assertEqual(result.findings[0].critic_decision, CriticDecision.ACCEPT)

    def test_verified_but_challenged_claim_is_not_actionable(self) -> None:
        result = EVARHardEvidenceProtocol(
            FakeReviewer([SUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.CHALLENGE_EVIDENCE),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual(result.accepted_findings, [])
        self.assertFalse(result.findings[0].actionable)
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.findings[0].critic_decision, CriticDecision.CHALLENGE_EVIDENCE)

    def test_repairs_ast_role_mismatch_before_critic_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "path.py").write_text(
                "import posixpath\n\n"
                "def _ancestry(path):\n"
                "    path = path.rstrip(posixpath.sep)\n"
                "    while path and not path.endswith(posixpath.sep):\n"
                "        yield path\n"
                "        path, tail = posixpath.split(path)\n",
                encoding="utf-8",
            )
            receipt = EvidenceReceipt(
                claim_id="ancestry",
                claim="_ancestry treats multiple separators like a single path separator.",
                evidence_type=EvidenceType.STRUCTURAL,
                evidence_role=EvidenceRole.CONTRADICTS_CLAIM,
                file="path.py",
                line_start=1,
                line_end=7,
                expected_stdout_contains="while path and not path.endswith(posixpath.sep):",
                falsification_condition="Docstring example appears to contradict the claim.",
            )

            result = EVARHardEvidenceProtocol(
                FakeReviewer([receipt]),
                FakeCritic(CriticDecision.ACCEPT),
            ).run("Review _ancestry behavior.", repo)

        self.assertEqual(len(result.accepted_findings), 1)
        self.assertEqual(result.findings[0].evidence_receipt.evidence_role, EvidenceRole.SUPPORTS_CLAIM)
        self.assertEqual(
            result.findings[0].evidence_receipt.falsification_condition,
            "The deterministic AST observation does not support the claim.",
        )
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.VERIFIED)
        self.assertIn("RECEIPT_REPAIR", [event["event_type"] for event in result.transcript])

    def test_repairs_invalid_inline_python_behavioral_witness_to_structural_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "path.py").write_text(
                "class Path:\n"
                "    def iterdir(self):\n"
                "        raise NotADirectoryError(\"Can't listdir a file\")\n",
                encoding="utf-8",
            )
            receipt = EvidenceReceipt(
                claim_id="iterdir",
                claim="Path.iterdir raises NotADirectoryError when called on a file.",
                evidence_type=EvidenceType.BEHAVIORAL,
                evidence_role=EvidenceRole.SUPPORTS_CLAIM,
                file="path.py",
                line_start=1,
                line_end=3,
                verification_command='python -c "try: Path().iterdir(); except NotADirectoryError: print(\'EVAR_WITNESS_PASS\')"',
                expected_exit_code=0,
                expected_stdout_contains="EVAR_WITNESS_PASS",
                falsification_condition="Path.iterdir does not raise NotADirectoryError.",
            )

            result = EVARHardEvidenceProtocol(
                FakeReviewer([receipt]),
                FakeCritic(CriticDecision.ACCEPT),
            ).run("Review Path.iterdir behavior.", repo)

        self.assertEqual(len(result.accepted_findings), 1)
        self.assertEqual(result.findings[0].evidence_receipt.evidence_type, EvidenceType.STRUCTURAL)
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.VERIFIED)
        self.assertIn("RECEIPT_REPAIR", [event["event_type"] for event in result.transcript])

    def test_unverifiable_receipt_is_not_actionable_even_if_critic_accepts(self) -> None:
        missing_file_receipt = replace(SUPPORTED_RECEIPT, claim_id="missing-file", file="missing.py")

        result = EVARHardEvidenceProtocol(
            FakeReviewer([missing_file_receipt]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual(result.accepted_findings, [])
        self.assertFalse(result.findings[0].actionable)
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.UNVERIFIABLE)
        self.assertEqual(result.findings[0].critic_decision, CriticDecision.ACCEPT)

    def test_multiple_findings_only_verified_accept_is_actionable(self) -> None:
        challenged = replace(SUPPORTED_RECEIPT, claim_id="verified_challenged")
        missing_file = replace(SUPPORTED_RECEIPT, claim_id="unverifiable", file="missing.py")
        decisions = {
            SUPPORTED_RECEIPT.claim_id: CriticDecision.ACCEPT,
            UNSUPPORTED_RECEIPT.claim_id: CriticDecision.ACCEPT,
            challenged.claim_id: CriticDecision.COUNTEREXAMPLE,
            missing_file.claim_id: CriticDecision.ACCEPT,
        }

        result = EVARHardEvidenceProtocol(
            FakeReviewer([SUPPORTED_RECEIPT, UNSUPPORTED_RECEIPT, challenged, missing_file]),
            FakeCritic(decisions),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual([finding.claim_id for finding in result.accepted_findings], [SUPPORTED_RECEIPT.claim_id])
        self.assertEqual(len(result.rejected_findings), 3)
        self.assertTrue(all(finding.actionable for finding in result.accepted_findings))
        self.assertTrue(all(not finding.actionable for finding in result.rejected_findings))

    def test_transcript_logs_structured_events_without_ground_truth(self) -> None:
        result = EVARHardEvidenceProtocol(
            FakeReviewer([SUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        event_types = [event["event_type"] for event in result.transcript]
        self.assertEqual(
            event_types,
            ["REVIEWER_FINDING", "VERIFICATION_RESULT", "CRITIC_DECISION", "FINAL_DECISION"],
        )
        self.assertTrue(all(event["claim_id"] == SUPPORTED_RECEIPT.claim_id for event in result.transcript))
        self.assertTrue(all("timestamp" in event for event in result.transcript))
        for event in result.transcript:
            self.assertNotIn("ground_truth", event)
            self.assertNotIn("ground_truth_evidence", event)
