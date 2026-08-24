from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from evar.protocols.base import Finding
from evar.verifier.models import EvidenceReceipt


@dataclass(frozen=True)
class GroundTruthFinding:
    id: str
    is_real: bool
    note: str = ""


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    repo_root: Path
    description: str
    seed_findings: list[Finding]
    ground_truth: list[GroundTruthFinding]
    text_evidence_by_finding_id: dict[str, str] = field(default_factory=dict)
    receipts_by_finding_id: dict[str, EvidenceReceipt] = field(default_factory=dict)
