from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.benchmark.schema import GroundTruth
from evar.eval.metrics import false_consensus_rate, supported_claim_retention
from evar.protocols.evar import CriticDecision, FakeCritic, FakeReviewer
from evar.protocols.registry import PROTOCOL_REGISTRY, create_protocol
from evar.results import BenchmarkResultRecord, result_record_from_protocol_result
from evar.verifier.models import EvidenceReceipt, VerificationResult
from evar.verifier.verify import DeterministicVerifier


class CrossProtocolEvidenceTests(unittest.TestCase):
    def test_false_claim_critic_accepts_ar_and_ar_text_but_evar_rejects(self) -> None:
        results = _run_all(UNSUPPORTED_RECEIPT, CriticDecision.ACCEPT)

        self.assertTrue(results["ar"].accepted_findings)
        self.assertTrue(results["ar_text"].accepted_findings)
        self.assertFalse(results["evar_hard"].accepted_findings)

    def test_supported_claim_accepts_all_protocols_when_critic_accepts(self) -> None:
        results = _run_all(SUPPORTED_RECEIPT, CriticDecision.ACCEPT)

        self.assertTrue(results["ar"].accepted_findings)
        self.assertTrue(results["ar_text"].accepted_findings)
        self.assertTrue(results["evar_hard"].accepted_findings)

    def test_registry_exposes_all_treatments(self) -> None:
        self.assertEqual(set(PROTOCOL_REGISTRY), {"ar", "ar_text", "evar_hard"})

    def test_result_record_schema_and_metrics(self) -> None:
        ar_result = create_protocol(
            "ar",
            FakeReviewer([UNSUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)
        evar_result = create_protocol(
            "evar_hard",
            FakeReviewer([UNSUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)
        supported_result = create_protocol(
            "evar_hard",
            FakeReviewer([SUPPORTED_RECEIPT]),
            FakeCritic(CriticDecision.ACCEPT),
        ).run("Review calculator behavior.", TOY_REPO_PATH)

        records = [
            result_record_from_protocol_result(
                case_id="u-ar",
                ground_truth=GroundTruth.UNSUPPORTED,
                result=ar_result,
                transcript_path="transcripts/u-ar.json",
                duration=0.1,
            ),
            result_record_from_protocol_result(
                case_id="u-evar",
                ground_truth=GroundTruth.UNSUPPORTED,
                result=evar_result,
                transcript_path="transcripts/u-evar.json",
                duration=0.1,
            ),
            result_record_from_protocol_result(
                case_id="s-evar",
                ground_truth=GroundTruth.SUPPORTED,
                result=supported_result,
                transcript_path="transcripts/s-evar.json",
                duration=0.1,
            ),
        ]

        self.assertEqual(records[0].protocol, "AR")
        self.assertTrue(records[0].final_actionable)
        self.assertEqual(false_consensus_rate(records), 0.5)
        self.assertEqual(supported_claim_retention(records), 1.0)

    def test_methodological_safeguards_no_ground_truth_passed_to_agents_or_verifier(self) -> None:
        task = "Review calculator behavior."
        reviewer = SpyReviewer([SUPPORTED_RECEIPT])
        critic = SpyCritic(CriticDecision.ACCEPT)
        verifier = SpyVerifier()

        for name in ["ar", "ar_text", "evar_hard"]:
            protocol = create_protocol(name, reviewer, critic, verifier=verifier)
            protocol.run(task, TOY_REPO_PATH)

        self.assertEqual(reviewer.tasks_seen, [task, task, task])
        self.assertTrue(all("SUPPORTED" not in seen and "UNSUPPORTED" not in seen for seen in reviewer.tasks_seen))
        self.assertTrue(all("SUPPORTED" not in seen and "UNSUPPORTED" not in seen for seen in critic.tasks_seen))
        self.assertTrue(all("SUPPORTED" not in seen and "UNSUPPORTED" not in seen for seen in verifier.repo_paths_seen))
        self.assertEqual(critic.text_evidence_seen, 1)

    def test_all_protocols_receive_same_task_and_same_claim_in_paired_test(self) -> None:
        task = "Review calculator behavior."
        reviewer = SpyReviewer([UNSUPPORTED_RECEIPT])
        critic = SpyCritic(CriticDecision.ACCEPT)

        results = {}
        for name in ["ar", "ar_text", "evar_hard"]:
            results[name] = create_protocol(name, reviewer, critic).run(task, TOY_REPO_PATH)

        self.assertEqual(reviewer.tasks_seen, [task, task, task])
        claims = {name: result.findings[0].claim for name, result in results.items()}
        self.assertEqual(set(claims.values()), {UNSUPPORTED_RECEIPT.claim})


class SpyReviewer(FakeReviewer):
    def __init__(self, receipts: list[EvidenceReceipt]) -> None:
        super().__init__(receipts)
        self.tasks_seen: list[str] = []

    def review(self, task: str, repo_path: Path) -> list[EvidenceReceipt]:
        self.tasks_seen.append(task)
        return super().review(task, repo_path)


class SpyCritic(FakeCritic):
    def __init__(self, decision: CriticDecision) -> None:
        super().__init__(decision)
        self.tasks_seen: list[str] = []
        self.text_evidence_seen = 0

    def critique(
        self,
        task: str,
        receipt: EvidenceReceipt,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        self.tasks_seen.append(task)
        return super().critique(task, receipt, verification_result)

    def critique_text(self, task, receipt, text_evidence, verification_result) -> CriticDecision:
        self.text_evidence_seen += 1
        self.tasks_seen.append(task)
        return CriticDecision.ACCEPT


class SpyVerifier(DeterministicVerifier):
    def __init__(self) -> None:
        super().__init__()
        self.repo_paths_seen: list[str] = []

    def verify(self, receipt: EvidenceReceipt, repo_path: Path) -> VerificationResult:
        self.repo_paths_seen.append(str(repo_path))
        return super().verify(receipt, repo_path)


def _run_all(receipt: EvidenceReceipt, decision: CriticDecision):
    return {
        name: create_protocol(name, FakeReviewer([replace(receipt)]), FakeCritic(decision)).run(
            "Review calculator behavior.",
            TOY_REPO_PATH,
        )
        for name in ["ar", "ar_text", "evar_hard"]
    }
