from __future__ import annotations

import json
import io
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
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
                            "expected_stdout_contains": "EVAR_WITNESS_PASS",
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
        temperature: float | None = 0.0,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or _load_env_api_key(Path(".env"))
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI backend.")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: object | None = None,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            payload["max_output_tokens"] = self.max_output_tokens
        if self.reasoning_effort is not None:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        if response_schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "evar_model_response",
                    "schema": response_schema,
                    "strict": True,
                }
            }

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


class OpenRouterChatBackend:
    """OpenAI-compatible chat backend for reproducible cross-provider runs."""

    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    request_timeout_seconds = 20
    max_attempts = 2
    max_total_seconds = 50

    def __init__(
        self,
        *,
        model_name: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.api_key = (
            api_key
            or os.environ.get("OPENROUTER_API_KEY")
            or _load_env_value(Path(".env"), "OPENROUTER_API_KEY")
        )
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for the OpenRouter backend.")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: object | None = None,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            payload["max_tokens"] = self.max_output_tokens
        if self.reasoning_effort is not None:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        if response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "evar_model_response",
                    "schema": response_schema,
                    "strict": True,
                },
            }
            payload["provider"] = {"require_parameters": True}

        request_body = json.dumps(payload).encode("utf-8")
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kishormorol/evar",
            "X-OpenRouter-Title": "EVAR Research Evaluation",
        }
        started = time.perf_counter()
        raw: dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            if time.perf_counter() - started >= self.max_total_seconds:
                break
            try:
                decoded = _curl_json_post(
                    self.endpoint,
                    request_body,
                    request_headers,
                    timeout=self.request_timeout_seconds,
                )
                if not isinstance(decoded, dict):
                    raise ValueError("OpenRouter returned a non-object JSON response")
                raw = decoded
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 402 or exc.code < 500 and exc.code != 429:
                    raise
                if exc.code != 429 and not 500 <= exc.code < 600:
                    raise
                retry_after = _retry_after_seconds(exc)
                exc.close()
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                retry_after = None
            if attempt + 1 >= self.max_attempts:
                break
            delay = retry_after if retry_after is not None else min(30.0, 2.0 ** attempt)
            remaining = self.max_total_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                break
            time.sleep(min(delay, remaining))
        if raw is None:
            if last_error is not None:
                raise last_error
            raise TimeoutError("OpenRouter request exceeded its total deadline")
        latency = time.perf_counter() - started
        text = _extract_chat_output_text(raw)
        usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
        return ModelResponse(
            text=text,
            parsed_output=_try_parse_json(text),
            model_name=self.model_name,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_seconds=latency,
            raw_metadata=raw if isinstance(raw, dict) else {"raw": raw},
        )


def _curl_json_post(
    endpoint: str,
    body: bytes,
    headers: dict[str, str],
    *,
    timeout: float,
) -> dict[str, Any]:
    """POST JSON through curl so a stalled chunked response cannot hang a run."""
    marker = b"\n__EVAR_STATUS:"
    command = [
        "curl", "--silent", "--show-error", "--max-time", str(int(timeout)),
        "--connect-timeout", "10", "--request", "POST", endpoint,
        "--write-out", "\n__EVAR_STATUS:%{http_code}",
    ]
    for name, value in headers.items():
        command.extend(["--header", f"{name}: {value}"])
    command.extend(["--data-binary", "@-"])
    try:
        completed = subprocess.run(
            command, input=body, capture_output=True, timeout=timeout + 5, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"request exceeded {timeout:g}s deadline") from exc
    if completed.returncode != 0:
        raise urllib.error.URLError(completed.stderr.decode("utf-8", errors="replace"))
    if marker not in completed.stdout:
        raise ValueError("curl response did not include an HTTP status")
    response_body, status_bytes = completed.stdout.rsplit(marker, 1)
    status = int(status_bytes.strip())
    if status >= 400:
        raise urllib.error.HTTPError(
            endpoint, status, "OpenRouter HTTP error", {}, io.BytesIO(response_body)
        )
    decoded = json.loads(response_body.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("OpenRouter returned a non-object JSON response")
    return decoded


def _retry_after_seconds(error: urllib.error.HTTPError) -> float | None:
    value = error.headers.get("Retry-After") if error.headers else None
    if value is None:
        return None
    try:
        return max(0.0, min(30.0, float(value)))
    except ValueError:
        return None


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


def _extract_chat_output_text(raw: dict[str, Any]) -> str:
    choices = raw.get("choices", [])
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message", {})
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return ""


def _try_parse_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _load_env_api_key(path: Path) -> str | None:
    return _load_env_value(path, "OPENAI_API_KEY")


def _load_env_value(path: Path, variable: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == variable:
            stripped = value.strip().strip('"').strip("'")
            return stripped or None
    return None


def _extract_candidate_claim(user_prompt: str) -> str:
    marker = "Candidate claim:\n"
    if marker not in user_prompt:
        return "dry-run candidate claim"
    after = user_prompt.split(marker, 1)[1]
    return after.split("\n\n", 1)[0].strip() or "dry-run candidate claim"
