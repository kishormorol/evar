from __future__ import annotations

from pathlib import Path

from evar.benchmark.schema import BenchmarkCase, GroundTruthFinding
from evar.protocols.base import Finding
from evar.verifier.models import EvidenceKind, EvidenceReceipt


def load_dummy_case(repo_root: Path | None = None) -> BenchmarkCase:
    root = repo_root or Path.cwd()
    target = root / "evar" / "benchmark" / "cases" / "example_bug.py"
    finding = Finding(
        id="F001",
        title="subtract uses the wrong operator",
        description="The helper claims to add two values but subtracts the second operand.",
        severity="high",
        target_file=str(target),
    )
    return BenchmarkCase(
        id="dummy-subtract",
        repo_root=root,
        description="A tiny deterministic benchmark case for smoke tests.",
        seed_findings=[finding],
        ground_truth=[GroundTruthFinding(id="F001", is_real=True, note="The implementation subtracts.")],
        text_evidence_by_finding_id={
            "F001": "example_bug.py returns `a - b` inside a function named add.",
        },
        receipts_by_finding_id={
            "F001": EvidenceReceipt(
                kind=EvidenceKind.STRUCTURAL,
                target=target,
                claim="add subtracts the second operand",
                line_start=2,
                line_end=2,
                must_contain="return a - b",
            ),
        },
    )
