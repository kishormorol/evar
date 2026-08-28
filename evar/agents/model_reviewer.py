from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from evar.model_backend import ModelBackend, ModelResponse
from evar.prompts import PromptTemplate, load_prompt, prompt_filename
from evar.verifier.models import EvidenceReceipt, EvidenceType


MAX_REPOSITORY_CONTEXT_BYTES = 12000
SKIPPED_DIRS = {"__pycache__", ".git", ".pytest_cache", ".venv"}
CONTEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yaml", ".yml"}


REVIEWER_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["receipts"],
    "properties": {
        "receipts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "claim_id",
                    "claim",
                    "evidence_type",
                    "file",
                    "line_start",
                    "line_end",
                    "verification_command",
                    "expected_exit_code",
                    "expected_stdout_contains",
                    "falsification_condition",
                ],
                "properties": {
                    "claim_id": {"type": "string"},
                    "claim": {"type": "string"},
                    "evidence_type": {"type": "string", "enum": ["behavioral", "structural"]},
                    "file": {"type": "string"},
                    "line_start": {"type": ["integer", "null"]},
                    "line_end": {"type": ["integer", "null"]},
                    "verification_command": {"type": ["string", "null"]},
                    "expected_exit_code": {"type": ["integer", "null"]},
                    "expected_stdout_contains": {
                        "type": ["string", "null"],
                        "description": (
                            "For behavioral evidence, include EVAR_WITNESS_PASS. "
                            "The command should print that marker only when the witness supports the claim."
                        ),
                    },
                    "falsification_condition": {"type": "string"},
                },
            },
        }
    },
}


@dataclass(frozen=True)
class ModelAgentConfig:
    model_name: str
    temperature: float = 0.0
    seed: int | None = 7
    max_output_tokens: int | None = None


class ModelOutputError(ValueError):
    pass


class ModelReviewer:
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
        self.prompt = load_prompt(prompt_filename("reviewer", protocol))
        self.responses: list[ModelResponse] = []

    def review(self, task: str, repo_path: Path) -> list[EvidenceReceipt]:
        response = self.backend.generate(
            self.prompt.text,
            _review_user_prompt(task, repo_path),
            response_schema=REVIEWER_RESPONSE_SCHEMA,
        )
        self.responses.append(response)
        return parse_reviewer_receipts(response.parsed_output if response.parsed_output is not None else response.text)

    @property
    def prompt_template(self) -> PromptTemplate:
        return self.prompt


def parse_reviewer_receipts(raw: str | object) -> list[EvidenceReceipt]:
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelOutputError(f"Reviewer output is not valid JSON: {exc}") from exc
    else:
        payload = raw
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


def _review_user_prompt(task: str, repo_path: Path) -> str:
    return (
        f"Task description and candidate claim:\n{task}\n\n"
        f"Repository path:\n{repo_path}\n\n"
        "Repository context:\n"
        f"{_repository_context(repo_path)}\n\n"
        "Use only repository context allowed by the experiment policy. "
        "Do not include benchmark labels or expected final decisions. "
        "For evidence receipts, file must be a path relative to Repository path."
    )


def _repository_context(repo_path: Path, *, max_bytes: int = MAX_REPOSITORY_CONTEXT_BYTES) -> str:
    if not repo_path.exists() or not repo_path.is_dir():
        return "[repository unavailable]"
    chunks: list[str] = []
    used = 0
    for path in sorted(_iter_context_files(repo_path)):
        relative = path.relative_to(repo_path).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rendered = f"--- {relative} ---\n{_line_numbered(text)}\n"
        encoded_len = len(rendered.encode("utf-8"))
        if used + encoded_len > max_bytes:
            chunks.append("[repository context truncated]")
            break
        chunks.append(rendered)
        used += encoded_len
    return "\n".join(chunks) if chunks else "[no text files available]"


def _iter_context_files(repo_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIPPED_DIRS for part in path.relative_to(repo_path).parts):
            continue
        if path.suffix.lower() not in CONTEXT_SUFFIXES:
            continue
        files.append(path)
    return files


def _line_numbered(text: str) -> str:
    return "\n".join(f"{index}: {line}" for index, line in enumerate(text.splitlines(), start=1))


def _string(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ModelOutputError(f"{key} must be a non-empty string.")
    return value


def _optional_string(item: dict[str, object], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if not isinstance(value, str):
        raise ModelOutputError(f"{key} must be null or a non-empty string.")
    return value


def _optional_int(item: dict[str, object], key: str) -> int | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ModelOutputError(f"{key} must be null or an integer.")
    return value
