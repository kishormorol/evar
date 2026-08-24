from __future__ import annotations

from evar.protocols.base import BaseProtocol, ProtocolResult


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
