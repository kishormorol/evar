from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from evar.verifier.models import EvidenceReceipt, VerificationResult


@dataclass(frozen=True)
class AgentConfig:
    model_name: str
    temperature: float = 0.0
    seed: int | None = None


@dataclass(frozen=True)
class ProtocolBudget:
    review_turns: int = 1
    challenge_turns: int = 1
    revision_turns: int = 1

    @property
    def total_turns(self) -> int:
        return self.review_turns + self.challenge_turns + self.revision_turns


@dataclass(frozen=True)
class Finding:
    id: str
    title: str
    description: str
    severity: str = "medium"
    target_file: str | None = None
    text_evidence: str | None = None
    receipt: EvidenceReceipt | None = None


@dataclass(frozen=True)
class Challenge:
    finding_id: str
    reason: str


@dataclass(frozen=True)
class ProtocolResult:
    protocol_name: str
    findings: list[Finding]
    challenges: list[Challenge]
    actionable_findings: list[Finding]
    verification_results: dict[str, VerificationResult] = field(default_factory=dict)
    budget: ProtocolBudget = field(default_factory=ProtocolBudget)
    config: AgentConfig = field(default_factory=lambda: AgentConfig(model_name="unset"))


class Reviewer(Protocol):
    def propose_findings(self, case: object, config: AgentConfig) -> list[Finding]:
        ...

    def revise_findings(
        self,
        case: object,
        findings: list[Finding],
        challenges: list[Challenge],
        config: AgentConfig,
        *,
        require_text_evidence: bool = False,
        require_receipt: bool = False,
    ) -> list[Finding]:
        ...


class Critic(Protocol):
    def challenge_findings(
        self,
        findings: list[Finding],
        config: AgentConfig,
        *,
        require_evidence: bool = False,
    ) -> list[Challenge]:
        ...


class BaseProtocol:
    name = "Base"

    def __init__(
        self,
        reviewer: Reviewer,
        critic: Critic,
        config: AgentConfig,
        budget: ProtocolBudget,
    ) -> None:
        self.reviewer = reviewer
        self.critic = critic
        self.config = config
        self.budget = budget

    def run(self, case: object) -> ProtocolResult:
        raise NotImplementedError

    def _challenge(self, findings: list[Finding], *, require_evidence: bool) -> list[Challenge]:
        if self.budget.challenge_turns <= 0:
            return []
        return self.critic.challenge_findings(
            findings,
            self.config,
            require_evidence=require_evidence,
        )
