from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from evar.protocols.base import Finding
from evar.verifier.models import EvidenceReceipt


class GroundTruth(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class ClaimFamily(StrEnum):
    BEHAVIOR_INVERSION = "behavior_inversion"
    MISSING_GUARD = "missing_guard"
    INCORRECT_CALL_RELATIONSHIP = "incorrect_call_relationship"
    CAUSAL_MISLOCALIZATION = "causal_mislocalization"
    STALE_EVIDENCE = "stale_evidence"


@dataclass(frozen=True)
class GroundTruthFinding:
    id: str
    is_real: bool
    note: str = ""


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    repo_path: Path
    task_description: str
    claim: str
    ground_truth: GroundTruth
    ground_truth_evidence: str
    validation_command: tuple[str, ...]
    claim_family: ClaimFamily
    seed_findings: list[Finding]
    text_evidence_by_finding_id: dict[str, str] = field(default_factory=dict)
    receipts_by_finding_id: dict[str, EvidenceReceipt] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.case_id

    @property
    def repo_root(self) -> Path:
        return self.repo_path

    @property
    def description(self) -> str:
        return self.task_description

    @property
    def ground_truth_findings(self) -> list[GroundTruthFinding]:
        return [
            GroundTruthFinding(
                id=finding.id,
                is_real=self.ground_truth == GroundTruth.SUPPORTED,
                note=self.ground_truth_evidence,
            )
            for finding in self.seed_findings
        ]

    def to_task_case(self) -> TaskCase:
        return TaskCase(
            case_id=self.case_id,
            repo_path=self.repo_path,
            task_description=self.task_description,
            claim=self.claim,
            validation_command=self.validation_command,
            claim_family=self.claim_family,
            seed_findings=self.seed_findings,
            text_evidence_by_finding_id=self.text_evidence_by_finding_id,
            receipts_by_finding_id=self.receipts_by_finding_id,
        )


@dataclass(frozen=True)
class TaskCase:
    """Protocol-visible benchmark view with ground truth stripped out."""

    case_id: str
    repo_path: Path
    task_description: str
    claim: str
    validation_command: tuple[str, ...]
    claim_family: ClaimFamily
    seed_findings: list[Finding]
    text_evidence_by_finding_id: dict[str, str] = field(default_factory=dict)
    receipts_by_finding_id: dict[str, EvidenceReceipt] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.case_id

    @property
    def repo_root(self) -> Path:
        return self.repo_path

    @property
    def description(self) -> str:
        return self.task_description
