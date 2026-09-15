from __future__ import annotations

import unittest

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.agents.model_critic import CriticPromptContext, _critic_user_prompt
from evar.prompts import prompt_filename
from evar.protocols.evar import (
    CriticDecision,
    EVARBlindGateEvidenceProtocol,
    FakeReviewer,
)
from evar.verifier.models import VerificationResult, VerificationStatus


class RecordingCritic:
    def __init__(self) -> None:
        self.statuses: list[VerificationStatus] = []

    def critique_text(self, task, receipt, text_evidence, verification_result):
        del task, receipt, text_evidence
        self.statuses.append(verification_result.status)
        return CriticDecision.ACCEPT


class EVARBlindGateEvidenceProtocolTests(unittest.TestCase):
    def test_failed_verification_is_hidden_from_critic_but_hard_gate_still_blocks(self) -> None:
        critic = RecordingCritic()
        result = EVARBlindGateEvidenceProtocol(
            FakeReviewer([UNSUPPORTED_RECEIPT]),
            critic,
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual(critic.statuses, [VerificationStatus.UNVERIFIABLE])
        self.assertEqual(result.findings[0].verification_result.status, VerificationStatus.FAILED)
        self.assertEqual(result.findings[0].critic_decision, CriticDecision.ACCEPT)
        self.assertFalse(result.findings[0].actionable)
        self.assertIsNotNone(result.findings[0].text_evidence)

    def test_verified_receipt_and_blind_critic_acceptance_pass_the_hard_gate(self) -> None:
        critic = RecordingCritic()
        result = EVARBlindGateEvidenceProtocol(
            FakeReviewer([SUPPORTED_RECEIPT]),
            critic,
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        self.assertEqual(len(result.accepted_findings), 1)
        self.assertEqual(critic.statuses, [VerificationStatus.UNVERIFIABLE])

    def test_model_prompt_mapping_reuses_reviewer_but_has_blind_critic(self) -> None:
        self.assertEqual(prompt_filename("reviewer", "evar_blind_gate"), "reviewer_evar_v1.txt")
        self.assertEqual(prompt_filename("critic", "evar_blind_gate"), "critic_evar_blind_v1.txt")

    def test_critic_user_prompt_does_not_expose_verifier_result(self) -> None:
        verified = VerificationResult(
            status=VerificationStatus.VERIFIED,
            stdout="secret verifier output",
            stderr="",
            exit_code=0,
            reason="secret verifier reason",
        )
        prompt = _critic_user_prompt(
            CriticPromptContext("task", SUPPORTED_RECEIPT, verified),
            protocol="evar_blind_gate",
            text_evidence=EVARBlindGateEvidenceProtocol(
                FakeReviewer([]), RecordingCritic()
            )._text_evidence(SUPPORTED_RECEIPT),
        )

        self.assertIn("deliberately withheld", prompt)
        self.assertNotIn("secret verifier output", prompt)
        self.assertNotIn("secret verifier reason", prompt)
        self.assertNotIn("Verification status: VERIFIED", prompt)


if __name__ == "__main__":
    unittest.main()
