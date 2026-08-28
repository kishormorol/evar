from __future__ import annotations

import json
from dataclasses import dataclass

from evar.agents.model_reviewer import ModelAgentConfig, ModelOutputError
from evar.model_backend import ModelBackend, ModelResponse
from evar.prompts import PromptTemplate, load_prompt, prompt_filename
from evar.protocols.evar import CriticDecision
from evar.protocols.evar import TextEvidence
from evar.verifier.models import EvidenceReceipt, VerificationResult


CRITIC_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decision"],
    "properties": {
        "decision": {
            "type": "string",
            "enum": [
                "ACCEPT",
                "CHALLENGE_EVIDENCE",
                "REQUEST_STRONGER_WITNESS",
                "COUNTEREXAMPLE",
            ],
        }
    },
}


@dataclass(frozen=True)
class CriticPromptContext:
    task: str
    receipt: EvidenceReceipt
    verification_result: VerificationResult


class ModelCritic:
    def __init__(
        self,
        backend: ModelBackend,
        config: ModelAgentConfig,
        *,
        protocol: str = "evar_hard",
    ) -> None:
        self.backend = backend
        self.config = config
        self.protocol = protocol
        self.prompt = load_prompt(prompt_filename("critic", protocol))
        self.responses: list[ModelResponse] = []

    def critique(
        self,
        task: str,
        receipt: EvidenceReceipt,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        response = self.backend.generate(
            self.prompt.text,
            _critic_user_prompt(CriticPromptContext(task, receipt, verification_result)),
            response_schema=CRITIC_RESPONSE_SCHEMA,
        )
        self.responses.append(response)
        return parse_critic_decision(response.parsed_output if response.parsed_output is not None else response.text)

    def critique_text(
        self,
        task: str,
        receipt: EvidenceReceipt,
        text_evidence: TextEvidence,
        verification_result: VerificationResult,
    ) -> CriticDecision:
        del text_evidence
        return self.critique(task, receipt, verification_result)

    @property
    def prompt_template(self) -> PromptTemplate:
        return self.prompt


def parse_critic_decision(raw: str | object) -> CriticDecision:
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelOutputError(f"Critic output is not valid JSON: {exc}") from exc
    else:
        payload = raw
    if not isinstance(payload, dict) or "decision" not in payload:
        raise ModelOutputError("Critic output must be an object with a decision field.")
    try:
        return CriticDecision(str(payload["decision"]))
    except ValueError as exc:
        raise ModelOutputError(f"Unsupported critic decision: {payload['decision']}") from exc


def _critic_user_prompt(context: CriticPromptContext) -> str:
    return (
        f"Task: {context.task}\n"
        f"Claim: {context.receipt.claim}\n"
        f"Evidence receipt: {context.receipt}\n"
        f"Verification status: {context.verification_result.status.value}\n"
        f"Verification reason: {context.verification_result.reason}"
    )
