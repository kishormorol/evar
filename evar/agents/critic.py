from __future__ import annotations

from evar.protocols.base import AgentConfig, Challenge, Finding


class DummyCritic:
    """Deterministic critic that challenges every proposed finding once."""

    def challenge_findings(
        self,
        findings: list[Finding],
        config: AgentConfig,
        *,
        require_evidence: bool = False,
    ) -> list[Challenge]:
        del config
        reason = "Provide evidence." if require_evidence else "Why is this actionable?"
        return [Challenge(finding_id=finding.id, reason=reason) for finding in findings]
