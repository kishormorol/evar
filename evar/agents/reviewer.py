from __future__ import annotations

from dataclasses import replace

from evar.benchmark.schema import BenchmarkCase
from evar.protocols.base import AgentConfig, Challenge, Finding


class DummyReviewer:
    """Deterministic reviewer used for tests and no-LLM examples."""

    def propose_findings(self, case: BenchmarkCase, config: AgentConfig) -> list[Finding]:
        del config
        return [replace(finding) for finding in case.seed_findings]

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
        del config
        challenged_ids = {challenge.finding_id for challenge in challenges}
        revised: list[Finding] = []
        for finding in findings:
            if finding.id not in challenged_ids:
                revised.append(finding)
                continue

            text_evidence = finding.text_evidence
            receipt = finding.receipt
            if require_text_evidence and text_evidence is None:
                text_evidence = case.text_evidence_by_finding_id.get(finding.id)
            if require_receipt and receipt is None:
                receipt = case.receipts_by_finding_id.get(finding.id)
            revised.append(replace(finding, text_evidence=text_evidence, receipt=receipt))
        return revised
