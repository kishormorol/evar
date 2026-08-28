from __future__ import annotations

import shlex
import subprocess
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path

from evar.verifier.models import (
    EvidenceReceipt,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
)


DEFAULT_TIMEOUT_SECONDS = 5.0
BEHAVIORAL_SUPPORT_MARKER = "EVAR_WITNESS_PASS"


@dataclass(frozen=True)
class CommandExecution:
    command: str
    argv: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool = False


def verify_evidence(
    receipt: EvidenceReceipt,
    repo_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> VerificationResult:
    """Verify a reviewer evidence receipt without using an LLM."""
    repo_result = _check_repo_path(repo_path)
    if repo_result is not None:
        return repo_result

    repo_root = repo_path.resolve()
    target = _resolve_receipt_file(repo_root, receipt.file)

    file_result = _check_file(receipt, target)
    if file_result is not None:
        return file_result

    line_result = _check_line_range(receipt, target)
    if line_result is not None:
        return line_result

    if receipt.evidence_type == EvidenceType.STRUCTURAL:
        return _verify_structural(receipt, target)
    if receipt.evidence_type == EvidenceType.BEHAVIORAL:
        return _verify_behavioral(receipt, repo_root, timeout_seconds)

    return VerificationResult(
        status=VerificationStatus.UNVERIFIABLE,
        stdout="",
        stderr="",
        exit_code=None,
        reason=f"Unsupported evidence type: {receipt.evidence_type}",
    )


def execute_command(
    command: str,
    repo_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> CommandExecution:
    """Central command execution point; intentionally uses shell=False."""
    argv = _parse_command(command)
    popen_args: str | list[str] = command if os.name == "nt" else argv
    try:
        completed = subprocess.run(
            popen_args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandExecution(
            command=command,
            argv=tuple(argv),
            stdout=_to_text(exc.stdout),
            stderr=_to_text(exc.stderr),
            exit_code=None,
            timed_out=True,
        )

    return CommandExecution(
        command=command,
        argv=tuple(argv),
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
    )


def _parse_command(command: str) -> list[str]:
    if not command or not command.strip():
        raise ValueError("verification_command must be a non-empty string.")
    return shlex.split(command, posix=os.name != "nt")


def _check_repo_path(repo_path: Path) -> VerificationResult | None:
    if not repo_path.exists():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Repository path does not exist: {repo_path}",
        )
    if not repo_path.is_dir():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Repository path is not a directory: {repo_path}",
        )
    return None


def _resolve_receipt_file(repo_root: Path, file_path: str) -> Path:
    path = Path(file_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _check_file(receipt: EvidenceReceipt, target: Path) -> VerificationResult | None:
    if not receipt.file or not str(receipt.file).strip():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Evidence receipt requires a referenced file.",
        )
    if not target.exists():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Referenced file does not exist: {receipt.file}",
        )
    if not target.is_file():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Referenced path is not a file: {receipt.file}",
        )
    return None


def _check_line_range(receipt: EvidenceReceipt, target: Path) -> VerificationResult | None:
    if receipt.line_start is None and receipt.line_end is None:
        return None
    if receipt.line_start is None or receipt.line_end is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Evidence line range must include both line_start and line_end.",
        )
    if receipt.line_start < 1 or receipt.line_end < receipt.line_start:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Evidence receipt has an invalid line range.",
        )

    line_count = len(target.read_text(encoding="utf-8").splitlines())
    if receipt.line_end > line_count:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Requested lines do not exist in referenced file.",
        )
    return None


def _verify_structural(receipt: EvidenceReceipt, target: Path) -> VerificationResult:
    if receipt.line_start is None or receipt.line_end is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Structural evidence requires line_start and line_end.",
        )

    lines = target.read_text(encoding="utf-8").splitlines()
    excerpt = "\n".join(lines[receipt.line_start - 1 : receipt.line_end])
    normalized_excerpt = _normalize_structural_text(excerpt)
    if (
        receipt.falsification_condition
        and _normalize_structural_text(receipt.falsification_condition) in normalized_excerpt
    ):
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=excerpt,
            stderr="",
            exit_code=0,
            reason="Falsification condition was observed in referenced lines.",
        )
    if (
        receipt.expected_stdout_contains
        and _normalize_structural_text(receipt.expected_stdout_contains) not in normalized_excerpt
    ):
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=excerpt,
            stderr="",
            exit_code=0,
            reason="Expected structural observation was not present in referenced lines.",
        )
    if not receipt.expected_stdout_contains:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout=excerpt,
            stderr="",
            exit_code=0,
            reason="Structural evidence requires expected_stdout_contains.",
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        stdout=excerpt,
        stderr="",
        exit_code=0,
        reason="Structural evidence verified.",
    )


def _normalize_structural_text(text: str) -> str:
    return "\n".join(line.strip() for line in textwrap.dedent(text).strip().splitlines())


def _verify_behavioral(
    receipt: EvidenceReceipt,
    repo_root: Path,
    timeout_seconds: float,
) -> VerificationResult:
    if receipt.verification_command is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Behavioral evidence requires verification_command.",
        )
    if receipt.expected_exit_code is None and receipt.expected_stdout_contains is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Behavioral evidence requires expected_exit_code or expected_stdout_contains.",
        )
    if (
        receipt.expected_stdout_contains is None
        or BEHAVIORAL_SUPPORT_MARKER not in receipt.expected_stdout_contains
    ):
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=(
                "Behavioral evidence requires expected_stdout_contains to include "
                f"{BEHAVIORAL_SUPPORT_MARKER!r}, printed only when the witness supports the claim."
            ),
        )

    try:
        execution = execute_command(
            receipt.verification_command,
            repo_root,
            timeout_seconds=timeout_seconds,
        )
    except ValueError as exc:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=str(exc),
        )
    except OSError as exc:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr=str(exc),
            exit_code=None,
            reason=f"Verification command could not be executed: {receipt.verification_command}",
        )

    command_note = f"command={execution.command!r}; argv={list(execution.argv)!r}"
    if execution.timed_out:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=None,
            reason=f"Verification command timed out after {timeout_seconds} seconds; {command_note}",
        )

    if receipt.expected_exit_code is not None and execution.exit_code != receipt.expected_exit_code:
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            reason=f"Expected exit code {receipt.expected_exit_code}, observed {execution.exit_code}; {command_note}",
        )
    if receipt.falsification_condition and receipt.falsification_condition in execution.stdout + execution.stderr:
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            reason=f"Falsification condition was observed in command output; {command_note}",
        )
    if (
        receipt.expected_stdout_contains is not None
        and receipt.expected_stdout_contains not in execution.stdout
    ):
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            reason=f"Expected stdout text was not observed; {command_note}",
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        stdout=execution.stdout,
        stderr=execution.stderr,
        exit_code=execution.exit_code,
        reason=f"Behavioral evidence verified; {command_note}",
    )


def _to_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


class DeterministicVerifier:
    """Dispatches structured receipts to deterministic non-LLM verifiers."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.timeout_seconds = timeout_seconds

    def verify(self, receipt: EvidenceReceipt, repo_path: Path) -> VerificationResult:
        return verify_evidence(receipt, repo_path, timeout_seconds=self.timeout_seconds)
