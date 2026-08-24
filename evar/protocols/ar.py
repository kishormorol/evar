from __future__ import annotations

from evar.protocols.base import BaseProtocol, ProtocolResult
from evar.protocols.evar import (
    Critic,
    CriticDecision,
    ProtocolResult as EvidenceProtocolResult,
    ReviewFinding,
    Reviewer,
    _event,
    no_verification_result,
)


class ARProtocol(BaseProtocol):
    name = "AR"

    def run(self, case: object) -> ProtocolResult:
        findings = self.reviewer.propose_findings(case, self.config)
        challenges = self._challenge(findings, require_evidence=False)
        if self.budget.revision_turns > 0:
            findings = self.reviewer.revise_findings(
                case,
                findings,
                challenges,
                self.config,
                require_text_evidence=False,
                require_receipt=False,
            )
        return ProtocolResult(
            protocol_name=self.name,
            findings=findings,
            challenges=challenges,
            actionable_findings=findings,
            budget=self.budget,
            config=self.config,
        )


class AREvidenceProtocol:
    name = "AR"

    def __init__(
        self,
        reviewer: Reviewer,
        critic: Critic,
        *,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.reviewer = reviewer
        self.critic = critic
        self.metadata = dict(metadata or {})

    def run(self, task: str, repo_path) -> EvidenceProtocolResult:
        transcript: list[dict[str, object]] = []
        receipts = self.reviewer.review(task, repo_path)
        findings: list[ReviewFinding] = []

        for receipt in receipts:
            transcript.append(_event("REVIEWER_FINDING", receipt.claim_id, receipt=receipt))
            verification_result = no_verification_result("AR does not use external verification.")
            decision = self.critic.critique(task, receipt, verification_result)
            transcript.append(_event("CRITIC_DECISION", receipt.claim_id, critic_decision=decision))

            actionable = decision == CriticDecision.ACCEPT
            finding = ReviewFinding(
                claim_id=receipt.claim_id,
                claim=receipt.claim,
                evidence_receipt=receipt,
                verification_result=verification_result,
                critic_decision=decision,
                actionable=actionable,
            )
            findings.append(finding)
            transcript.append(_event("FINAL_DECISION", receipt.claim_id, actionable=actionable))

        return EvidenceProtocolResult(
            findings=findings,
            accepted_findings=[finding for finding in findings if finding.actionable],
            rejected_findings=[finding for finding in findings if not finding.actionable],
            transcript=transcript,
            metadata={"protocol": self.name, **self.metadata},
        )
