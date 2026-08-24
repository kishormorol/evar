from __future__ import annotations

import unittest
from dataclasses import replace

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
from evar.verifier.models import VerificationStatus


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
