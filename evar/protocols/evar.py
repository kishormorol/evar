from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, Protocol

from evar.benchmark.schema import TaskCase
from evar.protocols.base import (
    BaseProtocol,
    Challenge,
    CriticDecision as LegacyCriticDecision,
    CriticDecisionType,
    Finding,
    ProtocolResult as LegacyProtocolResult,
)
from evar.verifier.models import EvidenceReceipt
from evar.verifier.models import EvidenceRole, VerificationResult, VerificationStatus
from evar.verifier.verify import DeterministicVerifier


class CriticDecision(StrEnum):
    ACCEPT = "ACCEPT"
    CHALLENGE_EVIDENCE = "CHALLENGE_EVIDENCE"
    REQUEST_STRONGER_WITNESS = "REQUEST_STRONGER_WITNESS"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"


@dataclass(frozen=True)
class ReviewFinding:
    claim_id: str
    claim: str
    evidence_receipt: EvidenceReceipt
    verification_result: VerificationResult
    critic_decision: CriticDecision
    actionable: bool
    text_evidence: TextEvidence | None = None


@dataclass(frozen=True)
class TextEvidence:
    claim: str
    file: str
    line_start: int | None
    line_end: int | None
    explanation: str
    quoted_or_paraphrased_support: str
    falsification_condition: str


@dataclass(frozen=True)
class ProtocolResult:
    findings: list[ReviewFinding]
    accepted_findings: list[ReviewFinding]
    rejected_findings: list[ReviewFinding]
    transcript: list[dict[str, object]]
    metadata: dict[str, object] = field(default_factory=dict)


class Reviewer(Protocol):
    def review(self, task: str, repo_path: Path) -> list[EvidenceReceipt]:
        ...


class Critic(Protocol):
    def critique(
        self,
        task: str,
        receipt: EvidenceReceipt,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        ...


class FakeReviewer:
    def __init__(self, receipts: list[EvidenceReceipt]) -> None:
        self.receipts = list(receipts)

    def review(self, task: str, repo_path: Path) -> list[EvidenceReceipt]:
        del task, repo_path
        return list(self.receipts)


class FakeCritic:
    def __init__(self, decisions: dict[str, CriticDecision] | CriticDecision) -> None:
        self.decisions = decisions

    def critique(
        self,
        task: str,
        receipt: EvidenceReceipt,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        del task, verification_result
        if isinstance(self.decisions, CriticDecision):
            return self.decisions
        return self.decisions.get(receipt.claim_id, CriticDecision.CHALLENGE_EVIDENCE)

    def critique_text(
        self,
        task: str,
        receipt: EvidenceReceipt,
        text_evidence: TextEvidence,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        del text_evidence
        return self.critique(task, receipt, verification_result)


class EVARHardEvidenceProtocol:
    name = "EVAR-Hard"

    def __init__(
        self,
        reviewer: Reviewer,
        critic: Critic,
        *,
        verifier: DeterministicVerifier | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.reviewer = reviewer
        self.critic = critic
        self.verifier = verifier or DeterministicVerifier()
        self.metadata = dict(metadata or {})

    def run(self, task: str, repo_path: Path) -> ProtocolResult:
        transcript: list[dict[str, object]] = []
        receipts = self.reviewer.review(task, repo_path)

        findings: list[ReviewFinding] = []
        for receipt in receipts:
            transcript.append(
                _event(
                    "REVIEWER_FINDING",
                    receipt.claim_id,
                    receipt=receipt,
                )
            )

            verification_result = self.verifier.verify(receipt, repo_path)
            transcript.append(
                _event(
                    "VERIFICATION_RESULT",
                    receipt.claim_id,
                    verification_result=verification_result,
                )
            )

            critic_decision = self.critic.critique(task, receipt, verification_result)
            transcript.append(
                _event(
                    "CRITIC_DECISION",
                    receipt.claim_id,
                    critic_decision=critic_decision,
                )
            )

            actionable = (
                verification_result.status == VerificationStatus.VERIFIED
                and receipt.evidence_role == EvidenceRole.SUPPORTS_CLAIM
                and critic_decision == CriticDecision.ACCEPT
            )
            finding = ReviewFinding(
                claim_id=receipt.claim_id,
                claim=receipt.claim,
                evidence_receipt=receipt,
                verification_result=verification_result,
                critic_decision=critic_decision,
                actionable=actionable,
            )
            findings.append(finding)
            transcript.append(
                _event(
                    "FINAL_DECISION",
                    receipt.claim_id,
                    actionable=actionable,
                )
            )

        return ProtocolResult(
            findings=findings,
            accepted_findings=[finding for finding in findings if finding.actionable],
            rejected_findings=[finding for finding in findings if not finding.actionable],
            transcript=transcript,
            metadata={
                "protocol": self.name,
                **self.metadata,
            },
        )


class EVARHardProtocol(BaseProtocol):
    name = "EVAR-Hard"

    def __init__(self, *args: object, verifier: DeterministicVerifier | None = None) -> None:
        super().__init__(*args)
        self.verifier = verifier or DeterministicVerifier()

    def run(self, case: TaskCase) -> LegacyProtocolResult:
        interaction_log: list[dict[str, object]] = []
        findings = self.reviewer.propose_findings(case, self.config)
        interaction_log.append(
            _interaction(
                prompt="Reviewer: propose structured EVAR findings.",
                model_response=findings,
                token_usage=None,
            )
        )

        challenges: list[Challenge] = []
        missing_receipt_findings = [finding for finding in findings if finding.receipt is None]
        if missing_receipt_findings and self.budget.revision_turns > 0:
            challenges = [
                Challenge(
                    finding_id=finding.id,
                    reason="EVAR-Hard requires a structured evidence receipt.",
                )
                for finding in missing_receipt_findings
            ]
            interaction_log.append(
                _interaction(
                    prompt="Verifier precheck: request structured evidence receipts.",
                    model_response=challenges,
                    critic_decision=[
                        LegacyCriticDecision(
                            finding_id=challenge.finding_id,
                            decision=CriticDecisionType.CHALLENGE_EVIDENCE,
                            reason=challenge.reason,
                        )
                        for challenge in challenges
                    ],
                    token_usage=None,
                )
            )
            findings = self.reviewer.revise_findings(
                case,
                findings,
                challenges,
                self.config,
                require_text_evidence=False,
                require_receipt=True,
            )
            interaction_log.append(
                _interaction(
                    prompt="Reviewer: provide structured evidence receipts.",
                    model_response=findings,
                    token_usage=None,
                )
            )

        verification_results = {}
        actionable = []
        for finding in findings:
            if finding.receipt is None:
                result = VerificationResult(
                    status=VerificationStatus.UNVERIFIABLE,
                    stdout="",
                    stderr="",
                    exit_code=None,
                    reason="Finding has no structured evidence receipt.",
                )
                verification_results[finding.id] = result
                decision = LegacyCriticDecision(
                    finding_id=finding.id,
                    decision=CriticDecisionType.CHALLENGE_EVIDENCE,
                    reason="Missing structured evidence receipt.",
                )
                interaction_log.append(
                    _interaction(
                        prompt="Verifier: validate structured evidence receipt.",
                        finding=finding,
                        verification_result=result,
                        critic_decision=decision,
                        final_acceptance=False,
                        token_usage=None,
                    )
                )
                continue

            result = self.verifier.verify(finding.receipt, case.repo_root)
            verification_results[finding.id] = result

            if result.status == VerificationStatus.VERIFIED:
                decision = _critic_decision(self.critic, finding, result, self.config)
            else:
                decision = LegacyCriticDecision(
                    finding_id=finding.id,
                    decision=CriticDecisionType.CHALLENGE_EVIDENCE,
                    reason="Evidence did not verify; reviewer should provide stronger evidence.",
                )

            accepted = (
                result.status == VerificationStatus.VERIFIED
                and finding.receipt.evidence_role == EvidenceRole.SUPPORTS_CLAIM
                and _legacy_decision_value(decision) == CriticDecisionType.ACCEPT
            )
            if accepted:
                actionable.append(finding)

            interaction_log.append(
                _interaction(
                    prompt="Verifier and critic: validate evidence, then decide acceptance.",
                    finding=finding,
                    verification_result=result,
                    critic_decision=decision,
                    final_acceptance=accepted,
                    token_usage=None,
                )
            )

        return LegacyProtocolResult(
            protocol_name=self.name,
            findings=findings,
            challenges=challenges,
            actionable_findings=actionable,
            verification_results=verification_results,
            budget=self.budget,
            config=self.config,
            interaction_log=interaction_log,
        )


def _critic_decision(
    critic: object,
    finding: Finding,
    verification_result: VerificationResult,
    config: object,
) -> LegacyCriticDecision:
    decide = getattr(critic, "decide_on_finding", None)
    if decide is not None:
        raw_decision = decide(finding, verification_result, config)
        return _coerce_critic_decision(finding.id, raw_decision)
    return LegacyCriticDecision(
        finding_id=finding.id,
        decision=CriticDecisionType.ACCEPT,
        reason="Verified evidence accepted by default critic policy.",
    )


def _coerce_critic_decision(finding_id: str, raw_decision: object) -> LegacyCriticDecision:
    if isinstance(raw_decision, LegacyCriticDecision):
        return raw_decision
    if isinstance(raw_decision, CriticDecisionType):
        return LegacyCriticDecision(finding_id=finding_id, decision=raw_decision)
    if isinstance(raw_decision, CriticDecision):
        return LegacyCriticDecision(
            finding_id=finding_id,
            decision=CriticDecisionType(raw_decision.value),
        )
    if isinstance(raw_decision, str):
        return LegacyCriticDecision(finding_id=finding_id, decision=CriticDecisionType(raw_decision))
    if isinstance(raw_decision, dict):
        decision = raw_decision.get("decision", CriticDecisionType.ACCEPT)
        if isinstance(decision, CriticDecision):
            decision = CriticDecisionType(decision.value)
        return LegacyCriticDecision(
            finding_id=str(raw_decision.get("finding_id", finding_id)),
            decision=decision if isinstance(decision, CriticDecisionType) else CriticDecisionType(str(decision)),
            reason=str(raw_decision.get("reason", "")),
        )
    raise TypeError(f"Unsupported critic decision: {raw_decision!r}")


def _legacy_decision_value(decision: object) -> CriticDecisionType:
    if isinstance(decision, LegacyCriticDecision):
        return decision.decision
    if isinstance(decision, CriticDecisionType):
        return decision
    if isinstance(decision, CriticDecision):
        return CriticDecisionType(decision.value)
    return CriticDecisionType(str(decision))


def _event(event_type: str, claim_id: str, **payload: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "claim_id": claim_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **{key: _json_safe(value) for key, value in payload.items()},
    }


def no_verification_result(reason: str) -> VerificationResult:
    return VerificationResult(
        status=VerificationStatus.UNVERIFIABLE,
        stdout="",
        stderr="",
        exit_code=None,
        reason=reason,
    )


def _interaction(
    *,
    prompt: str,
    model_response: object | None = None,
    finding: Finding | None = None,
    verification_result: VerificationResult | None = None,
    critic_decision: object | None = None,
    final_acceptance: bool | None = None,
    token_usage: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "model_response": _json_safe(model_response),
        "finding": _json_safe(finding),
        "verification_result": _json_safe(verification_result),
        "critic_decision": _json_safe(critic_decision),
        "final_acceptance": final_acceptance,
        "token_usage": token_usage,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)
