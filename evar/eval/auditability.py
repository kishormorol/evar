from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable


RECEIPT_FIELDS = {
    "claim_id",
    "claim",
    "evidence_type",
    "evidence_role",
    "file",
    "falsification_condition",
}


def auditability_summary(
    records: Iterable[dict[str, object]],
    *,
    project_root: Path | None = None,
) -> dict[str, object]:
    rows = list(records)
    completed = [row for row in rows if row.get("run_status") == "ok"]
    failed = [row for row in rows if row.get("run_status") != "ok"]
    typed_failures = [
        row
        for row in failed
        if isinstance(row.get("failure"), dict)
        and bool(str(row["failure"].get("type", "")).strip())
        and bool(str(row["failure"].get("reason", "")).strip())
    ]

    transcript_present = 0
    complete_receipts = 0
    verifier_outcomes = 0
    actionable = 0
    hard_protocol_actionable = 0
    actionable_with_machine_checked_receipt = 0
    gate_violations = 0
    failure_types: Counter[str] = Counter()
    for row in failed:
        failure = row.get("failure")
        if isinstance(failure, dict):
            failure_types[str(failure.get("type", "untyped"))] += 1

    for row in completed:
        transcript_path = row.get("transcript_path")
        if isinstance(transcript_path, str):
            path = Path(transcript_path)
            if project_root is not None and not path.is_absolute():
                path = project_root / path
            if project_root is None or path.is_file():
                transcript_present += 1

        findings = row.get("findings")
        if not isinstance(findings, list) or len(findings) != 1 or not isinstance(findings[0], dict):
            continue
        finding = findings[0]
        receipt = finding.get("evidence_receipt")
        verification = finding.get("verification_result")
        if isinstance(receipt, dict) and RECEIPT_FIELDS.issubset(receipt):
            complete_receipts += 1
        if isinstance(verification, dict) and verification.get("status") in {
            "VERIFIED",
            "FAILED",
            "UNVERIFIABLE",
        }:
            verifier_outcomes += 1

        is_actionable = bool(row.get("final_actionable"))
        actionable += int(is_actionable)
        if not is_actionable:
            continue
        protocol = str(row.get("protocol", ""))
        if protocol in {"evar_hard", "evar_blind_gate"}:
            hard_protocol_actionable += 1
            valid = (
                isinstance(verification, dict)
                and verification.get("status") == "VERIFIED"
                and isinstance(receipt, dict)
                and receipt.get("evidence_role") == "supports_claim"
                and finding.get("critic_decision") == "ACCEPT"
            )
            actionable_with_machine_checked_receipt += int(valid)
            gate_violations += int(not valid)

    return {
        "schema_version": 1,
        "attempted": len(rows),
        "completed": len(completed),
        "failed": len(failed),
        "transcript_coverage": _ratio(transcript_present, len(completed)),
        "receipt_schema_coverage": _ratio(complete_receipts, len(completed)),
        "verifier_outcome_coverage": _ratio(verifier_outcomes, len(completed)),
        "typed_failure_coverage": _ratio(len(typed_failures), len(failed)),
        "actionable": actionable,
        "hard_protocol_actionable": hard_protocol_actionable,
        "actionable_with_machine_checked_receipt": actionable_with_machine_checked_receipt,
        "machine_checked_receipt_coverage_for_hard_actionable": _ratio(
            actionable_with_machine_checked_receipt,
            hard_protocol_actionable,
        ),
        "hard_gate_invariant_violations": gate_violations,
        "failure_types": dict(sorted(failure_types.items())),
        "semantic_relevance": (
            "Not inferred mechanically. A blinded human relevance audit is required "
            "for the accepted-receipt sample."
        ),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
