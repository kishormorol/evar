from __future__ import annotations

import json
from dataclasses import dataclass

from evar.agents.model_reviewer import ModelAgentConfig, ModelClient, ModelOutputError
from evar.protocols.evar import CriticDecision
from evar.verifier.models import EvidenceReceipt, VerificationResult


@dataclass(frozen=True)
class CriticPromptContext:
    task: str
    receipt: EvidenceReceipt
    verification_result: VerificationResult


class ModelCritic:
    def __init__(self, client: ModelClient, config: ModelAgentConfig) -> None:
        self.client = client
        self.config = config

    def critique(
        self,
        task: str,
        receipt: EvidenceReceipt,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        prompt = _critic_prompt(CriticPromptContext(task, receipt, verification_result))
        raw = self.client.complete(prompt, seed=self.config.seed)
        return parse_critic_decision(raw)


def parse_critic_decision(raw: str) -> CriticDecision:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"Critic output is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or "decision" not in payload:
        raise ModelOutputError("Critic output must be an object with a decision field.")
    try:
        return CriticDecision(str(payload["decision"]))
    except ValueError as exc:
        raise ModelOutputError(f"Unsupported critic decision: {payload['decision']}") from exc


def _critic_prompt(context: CriticPromptContext) -> str:
    return (
        "Return strict JSON with a decision field. "
        "Allowed decisions: ACCEPT, CHALLENGE_EVIDENCE, REQUEST_STRONGER_WITNESS, COUNTEREXAMPLE. "
        "Do not include benchmark ground truth. "
        f"Task: {context.task}\n"
        f"Claim: {context.receipt.claim}\n"
        f"Verification status: {context.verification_result.status.value}\n"
        f"Verification reason: {context.verification_result.reason}"
    )
