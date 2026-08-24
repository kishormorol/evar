from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class EvidenceKind(StrEnum):
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"


@dataclass(frozen=True)
class EvidenceReceipt:
    kind: EvidenceKind
    target: Path
    claim: str
    line_start: int | None = None
    line_end: int | None = None
    must_contain: str | None = None
    command: tuple[str, ...] | None = None
    expected_exit_code: int = 0
    stdout_must_contain: str | None = None
    cwd: Path | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    kind: EvidenceKind
    message: str
    details: dict[str, str] = field(default_factory=dict)
