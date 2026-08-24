from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from evar.verifier.models import EvidenceReceipt, EvidenceType


class ModelClient(Protocol):
    def complete(self, prompt: str, *, seed: int | None = None) -> str:
        ...


@dataclass(frozen=True)
class ModelAgentConfig:
    model_name: str
    temperature: float = 0.0
    seed: int | None = 7
    max_output_tokens: int | None = None


class ModelOutputError(ValueError):
    pass


class ModelReviewer:
    def __init__(self, client: ModelClient, config: ModelAgentConfig) -> None:
        self.client = client
        self.config = config

    def review(self, task: str, repo_path: Path) -> list[EvidenceReceipt]:
        prompt = _review_prompt(task, repo_path)
        raw = self.client.complete(prompt, seed=self.config.seed)
        return parse_reviewer_receipts(raw)


def parse_reviewer_receipts(raw: str) -> list[EvidenceReceipt]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"Reviewer output is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("receipts"), list):
        raise ModelOutputError("Reviewer output must be an object with a receipts list.")
    return [_parse_receipt(item) for item in payload["receipts"]]


def _parse_receipt(item: object) -> EvidenceReceipt:
    if not isinstance(item, dict):
        raise ModelOutputError("Each receipt must be a JSON object.")
    required = {"claim_id", "claim", "evidence_type", "file", "falsification_condition"}
    missing = sorted(required - item.keys())
    if missing:
        raise ModelOutputError(f"Receipt missing required fields: {', '.join(missing)}")
    try:
        evidence_type = EvidenceType(str(item["evidence_type"]))
    except ValueError as exc:
        raise ModelOutputError(f"Unsupported evidence_type: {item['evidence_type']}") from exc

    return EvidenceReceipt(
        claim_id=_string(item, "claim_id"),
        claim=_string(item, "claim"),
        evidence_type=evidence_type,
        file=_string(item, "file"),
        line_start=_optional_int(item, "line_start"),
        line_end=_optional_int(item, "line_end"),
        verification_command=_optional_string(item, "verification_command"),
        expected_exit_code=_optional_int(item, "expected_exit_code"),
        expected_stdout_contains=_optional_string(item, "expected_stdout_contains"),
        falsification_condition=_string(item, "falsification_condition"),
    )


def _review_prompt(task: str, repo_path: Path) -> str:
    return (
        "Return strict JSON with a receipts list of EVAR EvidenceReceipt objects. "
        "Do not include benchmark ground truth. "
        f"Task: {task}\nRepository path: {repo_path}"
    )


def _string(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ModelOutputError(f"{key} must be a non-empty string.")
    return value


def _optional_string(item: dict[str, object], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ModelOutputError(f"{key} must be null or a non-empty string.")
    return value


def _optional_int(item: dict[str, object], key: str) -> int | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ModelOutputError(f"{key} must be null or an integer.")
    return value
