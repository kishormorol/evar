from __future__ import annotations

from evar.protocols.base import BaseProtocol, ProtocolResult


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
