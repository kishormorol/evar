from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    backend: str
    model: str
    temperature: float | None
    max_output_tokens: int | None
    reasoning_effort: str | None = None
    request_timeout_seconds: float | None = None
    max_attempts: int | None = None
    max_total_seconds: float | None = None


@dataclass(frozen=True)
class ProtocolConfig:
    critic_rounds: int
    verifier_timeout_seconds: float
    verifier_execution_backend: str = "local"
    verifier_container_image: str = "python:3.12.5-slim-bookworm"
    reviewer_prompt: str | None = None
    reviewer_parse_retries: int = 0


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    repetitions: int


@dataclass(frozen=True)
class PilotConfig:
    model: ModelConfig
    protocol: ProtocolConfig
    experiment: ExperimentConfig


def load_config(path: Path) -> PilotConfig:
    data = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    return PilotConfig(
        model=ModelConfig(
            backend=str(data["model"]["backend"]),
            model=str(data["model"]["model"]),
            temperature=_optional_float(data["model"].get("temperature")),
            max_output_tokens=_optional_int(data["model"].get("max_output_tokens")),
            reasoning_effort=_optional_string(data["model"].get("reasoning_effort")),
            request_timeout_seconds=_optional_float(data["model"].get("request_timeout_seconds")),
            max_attempts=_optional_int(data["model"].get("max_attempts")),
            max_total_seconds=_optional_float(data["model"].get("max_total_seconds")),
        ),
        protocol=ProtocolConfig(
            critic_rounds=int(data["protocol"]["critic_rounds"]),
            verifier_timeout_seconds=float(data["protocol"]["verifier_timeout_seconds"]),
            verifier_execution_backend=str(data["protocol"].get("verifier_execution_backend", "local")),
            verifier_container_image=str(
                data["protocol"].get("verifier_container_image", "python:3.12.5-slim-bookworm")
            ),
            reviewer_prompt=_optional_string(data["protocol"].get("reviewer_prompt")),
            reviewer_parse_retries=int(data["protocol"].get("reviewer_parse_retries", 0)),
        ),
        experiment=ExperimentConfig(
            seed=int(data["experiment"]["seed"]),
            repetitions=int(data["experiment"]["repetitions"]),
        ),
    )


def _parse_simple_yaml(text: str) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            result[current] = {}
            continue
        if current is None or ":" not in line:
            raise ValueError(f"Unsupported config line: {raw_line}")
        key, value = line.strip().split(":", 1)
        result[current][key.strip()] = _parse_scalar(value.strip())
    return result


def _parse_scalar(value: str) -> object:
    if value in ("null", "None", ""):
        return None
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip('"').strip("'")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
