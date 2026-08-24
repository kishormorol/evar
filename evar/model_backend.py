from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelResponse:
    text: str
    parsed_output: object | None
    model_name: str
    input_tokens: int | None
    output_tokens: int | None
    latency_seconds: float
    raw_metadata: dict[str, object] = field(default_factory=dict)


class ModelBackend(Protocol):
    model_name: str

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: object | None = None,
    ) -> ModelResponse:
        ...


@dataclass(frozen=True)
class BackendCall:
    system_prompt: str
    user_prompt: str
    response_schema: object | None


class DryRunBackend:
    def __init__(self, model_name: str = "dry-run-model") -> None:
        self.model_name = model_name
        self.calls: list[BackendCall] = []

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: object | None = None,
    ) -> ModelResponse:
        self.calls.append(BackendCall(system_prompt, user_prompt, response_schema))
        if "receipts" in system_prompt.lower():
            claim = _extract_candidate_claim(user_prompt)
            text = json.dumps(
                {
                    "receipts": [
                        {
                            "claim_id": "dry_run_claim",
                            "claim": claim,
                            "evidence_type": "behavioral",
                            "file": "README.md",
                            "line_start": None,
                            "line_end": None,
                            "verification_command": "python -m unittest discover",
                            "expected_exit_code": 0,
                            "expected_stdout_contains": "OK",
                            "falsification_condition": "FAILED",
                        }
                    ]
                }
            )
        else:
            text = '{"decision":"CHALLENGE_EVIDENCE"}'
        return ModelResponse(
            text=text,
            parsed_output=json.loads(text),
            model_name=self.model_name,
            input_tokens=None,
            output_tokens=None,
            latency_seconds=0.0,
            raw_metadata={"dry_run": True},
        )


class OpenAIResponsesBackend:
    def __init__(
        self,
        *,
        model_name: str,
        temperature: float = 0.0,
        max_output_tokens: int | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI backend.")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: object | None = None,
    ) -> ModelResponse:
        del response_schema
        payload: dict[str, Any] = {
            "model": self.model_name,
            "temperature": self.temperature,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.max_output_tokens is not None:
            payload["max_output_tokens"] = self.max_output_tokens

        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.loads(response.read().decode("utf-8"))
        latency = time.perf_counter() - started
        text = _extract_output_text(raw)
        usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
        parsed = _try_parse_json(text)
        return ModelResponse(
            text=text,
            parsed_output=parsed,
            model_name=self.model_name,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            latency_seconds=latency,
            raw_metadata=raw if isinstance(raw, dict) else {"raw": raw},
        )


def _extract_output_text(raw: dict[str, Any]) -> str:
    if isinstance(raw.get("output_text"), str):
        return raw["output_text"]
    chunks: list[str] = []
    for item in raw.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "".join(chunks)


def _try_parse_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_candidate_claim(user_prompt: str) -> str:
    marker = "Candidate claim:\n"
    if marker not in user_prompt:
        return "dry-run candidate claim"
    after = user_prompt.split(marker, 1)[1]
    return after.split("\n\n", 1)[0].strip() or "dry-run candidate claim"
