from __future__ import annotations

from evar.protocols.base import BaseProtocol, ProtocolResult
from evar.protocols.evar import (
    Critic,
    CriticDecision,
    ProtocolResult as EvidenceProtocolResult,
    ReviewFinding,
    Reviewer,
    TextEvidence,
    _event,
    no_verification_result,
)


class ARTextProtocol(BaseProtocol):
    name = "AR-Text"

    def run(self, case: object) -> ProtocolResult:
        findings = self.reviewer.propose_findings(case, self.config)
        challenges = self._challenge(findings, require_evidence=True)
        if self.budget.revision_turns > 0:
            findings = self.reviewer.revise_findings(
                case,
                findings,
                challenges,
                self.config,
                require_text_evidence=True,
                require_receipt=False,
            )
        actionable = [finding for finding in findings if finding.text_evidence]
        return ProtocolResult(
            protocol_name=self.name,
            findings=findings,
            challenges=challenges,
            actionable_findings=actionable,
            budget=self.budget,
            config=self.config,
        )


class ARTextEvidenceProtocol:
    name = "AR-Text"

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
            text_evidence = TextEvidence(
                claim=receipt.claim,
                file=receipt.file,
                line_start=receipt.line_start,
                line_end=receipt.line_end,
                explanation="Reviewer supplied textual evidence; AR-Text does not execute it.",
                quoted_or_paraphrased_support=receipt.expected_stdout_contains or receipt.claim,
                falsification_condition=receipt.falsification_condition,
            )
            transcript.append(
                _event("REVIEWER_FINDING", receipt.claim_id, receipt=receipt, text_evidence=text_evidence)
            )
            verification_result = no_verification_result("AR-Text does not execute textual evidence.")
            critique_text = getattr(self.critic, "critique_text", None)
            if critique_text is not None:
                decision = critique_text(task, receipt, text_evidence, verification_result)
            else:
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
                text_evidence=text_evidence,
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
