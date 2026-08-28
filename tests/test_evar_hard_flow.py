from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evar.benchmark.schema import BenchmarkCase, ClaimFamily, GroundTruth
from evar.protocols.base import (
    AgentConfig,
    Challenge,
    CriticDecision,
    CriticDecisionType,
    Finding,
    ProtocolBudget,
)
from evar.protocols.evar import EVARHardProtocol
from evar.verifier.models import EvidenceReceipt, EvidenceRole, EvidenceType, VerificationResult, VerificationStatus


class FakeReviewer:
    def __init__(self, findings: list[Finding]) -> None:
        self.findings = findings

    def propose_findings(self, case: BenchmarkCase, config: AgentConfig) -> list[Finding]:
        del case, config
        return self.findings

    def revise_findings(
        self,
        case: BenchmarkCase,
        findings: list[Finding],
        challenges: list[Challenge],
        config: AgentConfig,
        *,
        require_text_evidence: bool = False,
        require_receipt: bool = False,
    ) -> list[Finding]:
        del case, challenges, config, require_text_evidence, require_receipt
        return findings


class FakeCritic:
    def __init__(self, decision: CriticDecisionType) -> None:
        self.decision = decision
        self.calls: list[tuple[Finding, VerificationResult]] = []

    def challenge_findings(
        self,
        findings: list[Finding],
        config: AgentConfig,
        *,
        require_evidence: bool = False,
    ) -> list[Challenge]:
        del config, require_evidence
        return [Challenge(finding_id=finding.id, reason="challenge") for finding in findings]

    def decide_on_finding(
        self,
        finding: Finding,
        verification_result: VerificationResult,
        config: AgentConfig,
    ) -> CriticDecision:
        del config
        self.calls.append((finding, verification_result))
        return CriticDecision(
            finding_id=finding.id,
            decision=self.decision,
            reason=f"fake critic: {self.decision.value}",
        )


class EVARHardFlowTests(unittest.TestCase):
    def test_verified_and_accepted_finding_is_actionable_and_logged_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _write_repo(Path(tmp), "def add(a, b):\n    return a - b\n")
            finding = _finding(_receipt(expected_stdout_contains="return a - b"))
            critic = FakeCritic(CriticDecisionType.ACCEPT)

            result = EVARHardProtocol(
                FakeReviewer([finding]),
                critic,
                AgentConfig(model_name="fake"),
                ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1),
            ).run(_case(repo, [finding]).to_task_case())

        self.assertEqual([finding.id for finding in result.actionable_findings], ["F001"])
        self.assertEqual(result.verification_results["F001"].status, VerificationStatus.VERIFIED)
        self.assertEqual(len(critic.calls), 1)
        self.assertTrue(result.interaction_log[-1]["final_acceptance"])
        self.assertEqual(result.interaction_log[-1]["critic_decision"]["decision"], "ACCEPT")
        self.assertEqual(
            set(result.interaction_log[-1]),
            {
                "timestamp",
                "prompt",
                "model_response",
                "finding",
                "verification_result",
                "critic_decision",
                "final_acceptance",
                "token_usage",
            },
        )
        json.dumps(result.interaction_log)

    def test_verified_finding_with_counterexample_is_not_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _write_repo(Path(tmp), "def add(a, b):\n    return a - b\n")
            finding = _finding(_receipt(expected_stdout_contains="return a - b"))
            critic = FakeCritic(CriticDecisionType.COUNTEREXAMPLE)

            result = EVARHardProtocol(
                FakeReviewer([finding]),
                critic,
                AgentConfig(model_name="fake"),
                ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1),
            ).run(_case(repo, [finding]).to_task_case())

        self.assertEqual(result.actionable_findings, [])
        self.assertEqual(result.verification_results["F001"].status, VerificationStatus.VERIFIED)
        self.assertEqual(result.interaction_log[-1]["critic_decision"]["decision"], "COUNTEREXAMPLE")
        self.assertFalse(result.interaction_log[-1]["final_acceptance"])

    def test_verified_counterevidence_is_not_actionable_even_if_critic_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _write_repo(Path(tmp), "def add(a, b):\n    return a - b\n")
            finding = _finding(
                _receipt(
                    expected_stdout_contains="return a - b",
                    evidence_role=EvidenceRole.CONTRADICTS_CLAIM,
                )
            )
            critic = FakeCritic(CriticDecisionType.ACCEPT)

            result = EVARHardProtocol(
                FakeReviewer([finding]),
                critic,
                AgentConfig(model_name="fake"),
                ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1),
            ).run(_case(repo, [finding]).to_task_case())

        self.assertEqual(result.verification_results["F001"].status, VerificationStatus.VERIFIED)
        self.assertEqual(result.actionable_findings, [])
        self.assertFalse(result.interaction_log[-1]["final_acceptance"])

    def test_failed_verification_is_not_actionable_and_does_not_reach_acceptance_critic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _write_repo(Path(tmp), "def add(a, b):\n    return a + b\n")
            finding = _finding(_receipt(expected_stdout_contains="return a - b"))
            critic = FakeCritic(CriticDecisionType.ACCEPT)

            result = EVARHardProtocol(
                FakeReviewer([finding]),
                critic,
                AgentConfig(model_name="fake"),
                ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1),
            ).run(_case(repo, [finding]).to_task_case())

        self.assertEqual(result.actionable_findings, [])
        self.assertEqual(result.verification_results["F001"].status, VerificationStatus.FAILED)
        self.assertEqual(critic.calls, [])
        self.assertEqual(result.interaction_log[-1]["critic_decision"]["decision"], "CHALLENGE_EVIDENCE")
        self.assertFalse(result.interaction_log[-1]["final_acceptance"])

    def test_unverifiable_finding_without_receipt_is_not_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _write_repo(Path(tmp), "def add(a, b):\n    return a - b\n")
            finding = _finding(receipt=None)
            critic = FakeCritic(CriticDecisionType.ACCEPT)

            result = EVARHardProtocol(
                FakeReviewer([finding]),
                critic,
                AgentConfig(model_name="fake"),
                ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=0),
            ).run(_case(repo, [finding]).to_task_case())

        self.assertEqual(result.actionable_findings, [])
        self.assertEqual(result.verification_results["F001"].status, VerificationStatus.UNVERIFIABLE)
        self.assertEqual(critic.calls, [])
        self.assertEqual(result.interaction_log[-1]["critic_decision"]["decision"], "CHALLENGE_EVIDENCE")
        self.assertFalse(result.interaction_log[-1]["final_acceptance"])


def _write_repo(repo: Path, contents: str) -> Path:
    (repo / "sample.py").write_text(contents, encoding="utf-8")
    return repo


def _receipt(
    expected_stdout_contains: str,
    *,
    evidence_role: EvidenceRole = EvidenceRole.SUPPORTS_CLAIM,
) -> EvidenceReceipt:
    return EvidenceReceipt(
        claim_id="F001",
        claim="add uses the wrong operator",
        evidence_type=EvidenceType.STRUCTURAL,
        evidence_role=evidence_role,
        file="sample.py",
        line_start=2,
        line_end=2,
        expected_stdout_contains=expected_stdout_contains,
        falsification_condition="return a + b",
    )


def _finding(receipt: EvidenceReceipt | None) -> Finding:
    return Finding(
        id="F001",
        title="wrong operator",
        description="add subtracts instead of adding",
        receipt=receipt,
    )


def _case(repo: Path, findings: list[Finding]) -> BenchmarkCase:
    return BenchmarkCase(
        case_id="fake",
        repo_path=repo,
        task_description="fake benchmark case",
        claim="add uses the wrong operator",
        ground_truth=GroundTruth.SUPPORTED,
        ground_truth_evidence="line 2 subtracts",
        validation_command=("python", "-m", "unittest"),
        claim_family=ClaimFamily.BEHAVIOR_INVERSION,
        seed_findings=findings,
    )
