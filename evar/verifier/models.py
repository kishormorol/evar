from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceType(StrEnum):
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"


EvidenceKind = EvidenceType


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(frozen=True)
class EvidenceReceipt:
    claim_id: str
    claim: str
    evidence_type: EvidenceType
    file: str
    line_start: int | None = None
    line_end: int | None = None
    verification_command: str | None = None
    expected_exit_code: int | None = None
    expected_stdout_contains: str | None = None
    falsification_condition: str = ""


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    stdout: str
    stderr: str
    exit_code: int | None
    reason: str

    @property
    def ok(self) -> bool:
        return self.status == VerificationStatus.VERIFIED
