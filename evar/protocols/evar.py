from __future__ import annotations

from evar.protocols.base import BaseProtocol, ProtocolResult
from evar.verifier.verify import DeterministicVerifier


class EVARHardProtocol(BaseProtocol):
    name = "EVAR-Hard"

    def __init__(self, *args: object, verifier: DeterministicVerifier | None = None) -> None:
        super().__init__(*args)
        self.verifier = verifier or DeterministicVerifier()

    def run(self, case: object) -> ProtocolResult:
        findings = self.reviewer.propose_findings(case, self.config)
        challenges = self._challenge(findings, require_evidence=True)
        if self.budget.revision_turns > 0:
            findings = self.reviewer.revise_findings(
                case,
                findings,
                challenges,
                self.config,
                require_text_evidence=False,
                require_receipt=True,
            )

        verification_results = {}
        actionable = []
        for finding in findings:
            if finding.receipt is None:
                continue
            result = self.verifier.verify(finding.receipt)
            verification_results[finding.id] = result
            if result.ok:
                actionable.append(finding)

        return ProtocolResult(
            protocol_name=self.name,
            findings=findings,
            challenges=challenges,
            actionable_findings=actionable,
            verification_results=verification_results,
            budget=self.budget,
            config=self.config,
        )
