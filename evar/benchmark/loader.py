from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evar.benchmark.schema import BenchmarkCase, ClaimFamily, GroundTruth
from evar.protocols.base import Finding
from evar.verifier.models import EvidenceReceipt, EvidenceType


REQUIRED_FIELDS = {
    "case_id",
    "repo_path",
    "task_description",
    "claim",
    "ground_truth",
    "ground_truth_evidence",
    "validation_command",
    "claim_family",
}


class BenchmarkValidationError(ValueError):
    pass


def load_dummy_case(repo_root: Path | None = None) -> BenchmarkCase:
    root = repo_root or Path.cwd()
    target = Path("evar") / "benchmark" / "cases" / "example_bug.py"
    finding = Finding(
        id="F001",
        title="subtract uses the wrong operator",
        description="The helper claims to add two values but subtracts the second operand.",
        severity="high",
        target_file=str(target),
    )
    return BenchmarkCase(
        case_id="dummy-subtract",
        repo_path=root,
        task_description="A tiny deterministic benchmark case for smoke tests.",
        claim="add subtracts the second operand",
        ground_truth=GroundTruth.SUPPORTED,
        ground_truth_evidence="The implementation subtracts.",
        validation_command=("python", "-m", "unittest", "discover", "-s", "tests"),
        claim_family=ClaimFamily.BEHAVIOR_INVERSION,
        seed_findings=[finding],
        text_evidence_by_finding_id={
            "F001": "example_bug.py returns `a - b` inside a function named add.",
        },
        receipts_by_finding_id={
            "F001": EvidenceReceipt(
                claim_id="F001",
                claim="add subtracts the second operand",
                evidence_type=EvidenceType.STRUCTURAL,
                file=str(target),
                line_start=2,
                line_end=2,
                expected_stdout_contains="return a - b",
                falsification_condition="return a + b",
            ),
        },
    )


def load_jsonl_cases(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise BenchmarkValidationError(f"Line {line_number}: invalid JSON: {exc}") from exc
            cases.append(validate_case(raw, source=path, line_number=line_number))
    return cases


def validate_case(raw: object, *, source: Path | None = None, line_number: int | None = None) -> BenchmarkCase:
    context = _context(source, line_number)
    if not isinstance(raw, dict):
        raise BenchmarkValidationError(f"{context}case must be a JSON object.")

    missing = sorted(REQUIRED_FIELDS - raw.keys())
    if missing:
        raise BenchmarkValidationError(f"{context}missing required fields: {', '.join(missing)}")

    case_id = _required_str(raw, "case_id", context)
    repo_path = Path(_required_str(raw, "repo_path", context))
    task_description = _required_str(raw, "task_description", context)
    claim = _required_str(raw, "claim", context)
    ground_truth_evidence = _required_str(raw, "ground_truth_evidence", context)

    try:
        ground_truth = GroundTruth(_required_str(raw, "ground_truth", context))
    except ValueError as exc:
        raise BenchmarkValidationError(f"{context}ground_truth must be SUPPORTED or UNSUPPORTED.") from exc

    try:
        claim_family = ClaimFamily(_required_str(raw, "claim_family", context))
    except ValueError as exc:
        allowed = ", ".join(family.value for family in ClaimFamily)
        raise BenchmarkValidationError(f"{context}claim_family must be one of: {allowed}.") from exc

    validation_command = _validation_command(raw["validation_command"], context)
    seed_finding = Finding(
        id=case_id,
        title=claim,
        description=claim,
        target_file=None,
    )
    return BenchmarkCase(
        case_id=case_id,
        repo_path=repo_path,
        task_description=task_description,
        claim=claim,
        ground_truth=ground_truth,
        ground_truth_evidence=ground_truth_evidence,
        validation_command=validation_command,
        claim_family=claim_family,
        seed_findings=[seed_finding],
    )


def _required_str(raw: dict[str, Any], field: str, context: str) -> str:
    value = raw[field]
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkValidationError(f"{context}{field} must be a non-empty string.")
    return value


def _validation_command(value: object, context: str) -> tuple[str, ...]:
    if isinstance(value, str):
        if not value.strip():
            raise BenchmarkValidationError(f"{context}validation_command must be non-empty.")
        return (value,)
    if isinstance(value, list) and value and all(isinstance(part, str) and part for part in value):
        return tuple(value)
    raise BenchmarkValidationError(
        f"{context}validation_command must be a non-empty string or non-empty list of strings."
    )


def _context(source: Path | None, line_number: int | None) -> str:
    if source is None:
        return ""
    if line_number is None:
        return f"{source}: "
    return f"{source}:{line_number}: "
