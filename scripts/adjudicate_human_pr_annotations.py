from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


DECISION_FIELDS = (
    "eligible",
    "normalized_claim",
    "claim_family",
    "supported_at_review",
    "unsupported_at_merge",
    "exclusion_reason",
)
CLAIM_FAMILIES = {
    "behavior_inversion",
    "missing_guard",
    "incorrect_call_relationship",
    "causal_mislocalization",
    "stale_evidence",
}


def load_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _annotation(row: dict[str, object]) -> dict[str, object]:
    annotation = row.get("annotation")
    if not isinstance(annotation, dict):
        raise ValueError(f"{row.get('candidate_id', '<unknown>')}: annotation must be an object")
    return annotation


def _validate_export(rows: list[dict[str, object]], label: str) -> tuple[dict[str, dict[str, object]], str]:
    if not rows:
        raise ValueError(f"{label}: annotation export is empty")
    by_id: dict[str, dict[str, object]] = {}
    annotator_ids: set[str] = set()
    for row in rows:
        candidate_id = row.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError(f"{label}: candidate_id must be a non-empty string")
        if candidate_id in by_id:
            raise ValueError(f"{label}: duplicate candidate_id {candidate_id}")
        annotation = _annotation(row)
        annotator_id = annotation.get("annotator_id")
        if not isinstance(annotator_id, str) or not annotator_id.strip():
            raise ValueError(f"{label}/{candidate_id}: annotator_id is required")
        annotator_ids.add(annotator_id.strip())
        eligible = annotation.get("eligible")
        if not isinstance(eligible, bool):
            raise ValueError(f"{label}/{candidate_id}: eligible must be true or false")
        if eligible:
            if not isinstance(annotation.get("normalized_claim"), str) or not str(
                annotation["normalized_claim"]
            ).strip():
                raise ValueError(f"{label}/{candidate_id}: normalized_claim is required")
            if not isinstance(annotation.get("claim_family"), str) or not str(
                annotation["claim_family"]
            ).strip():
                raise ValueError(f"{label}/{candidate_id}: claim_family is required")
            if annotation["claim_family"] not in CLAIM_FAMILIES:
                raise ValueError(
                    f"{label}/{candidate_id}: claim_family must be one of {sorted(CLAIM_FAMILIES)}"
                )
            if not isinstance(annotation.get("supported_at_review"), bool):
                raise ValueError(f"{label}/{candidate_id}: supported_at_review must be boolean")
            if not isinstance(annotation.get("unsupported_at_merge"), bool):
                raise ValueError(f"{label}/{candidate_id}: unsupported_at_merge must be boolean")
        elif not isinstance(annotation.get("exclusion_reason"), str) or not str(
            annotation["exclusion_reason"]
        ).strip():
            raise ValueError(f"{label}/{candidate_id}: exclusion_reason is required")
        by_id[candidate_id] = row
    if len(annotator_ids) != 1:
        raise ValueError(f"{label}: expected one stable annotator_id, found {sorted(annotator_ids)}")
    return by_id, next(iter(annotator_ids))


def validate_export(
    export_path: Path,
    queue_path: Path,
    *,
    label: str = "annotation-export",
) -> dict[str, object]:
    export_rows = load_rows(export_path)
    export_by_id, annotator_id = _validate_export(export_rows, label)
    queue_rows = load_rows(queue_path)
    if not queue_rows:
        raise ValueError("expected queue is empty")
    queue_by_id: dict[str, dict[str, object]] = {}
    for row in queue_rows:
        candidate_id = row.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("expected queue contains an invalid candidate_id")
        if candidate_id in queue_by_id:
            raise ValueError(f"expected queue contains duplicate candidate_id {candidate_id}")
        queue_by_id[candidate_id] = row
    if set(export_by_id) != set(queue_by_id):
        missing = sorted(set(queue_by_id) - set(export_by_id))
        unexpected = sorted(set(export_by_id) - set(queue_by_id))
        raise ValueError(f"candidate sets differ; missing={missing}, unexpected={unexpected}")
    for candidate_id, export_row in export_by_id.items():
        exported_source = {key: value for key, value in export_row.items() if key != "annotation"}
        queued_source = {key: value for key, value in queue_by_id[candidate_id].items() if key != "annotation"}
        if exported_source != queued_source:
            raise ValueError(f"{label}/{candidate_id}: candidate payload differs from expected queue")
    annotations = [_annotation(row) for row in export_rows]
    return {
        "schema_version": 1,
        "valid": True,
        "annotator_id": annotator_id,
        "candidate_count": len(export_rows),
        "eligible": sum(annotation["eligible"] is True for annotation in annotations),
        "excluded": sum(annotation["eligible"] is False for annotation in annotations),
        "export": export_path.as_posix(),
        "export_sha256": _sha256(export_path),
        "queue": queue_path.as_posix(),
        "queue_sha256": _sha256(queue_path),
    }


def _decision(annotation: dict[str, object]) -> tuple[object, ...]:
    eligible = annotation["eligible"]
    if eligible is False:
        return (False, str(annotation["exclusion_reason"]).strip())
    return tuple(
        str(annotation[field]).strip() if field == "normalized_claim" else annotation[field]
        for field in DECISION_FIELDS[:-1]
    )


def _blinded_annotation(annotation: dict[str, object]) -> dict[str, object]:
    """Return an adjudication view without an independent reviewer's identity."""
    return {
        field: annotation.get(field)
        for field in DECISION_FIELDS
    }


def _write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _nominal_agreement(values_a: list[object], values_b: list[object]) -> dict[str, object]:
    if len(values_a) != len(values_b):
        raise ValueError("agreement vectors must have the same length")
    total = len(values_a)
    if total == 0:
        return {"n": 0, "percent_agreement": None, "cohen_kappa": None}
    observed = sum(a == b for a, b in zip(values_a, values_b, strict=True)) / total
    counts_a, counts_b = Counter(values_a), Counter(values_b)
    categories = set(counts_a) | set(counts_b)
    expected = sum((counts_a[value] / total) * (counts_b[value] / total) for value in categories)
    if expected == 1.0:
        kappa = 1.0 if observed == 1.0 else None
    else:
        kappa = (observed - expected) / (1 - expected)
    return {"n": total, "percent_agreement": observed, "cohen_kappa": kappa}


def annotation_agreement(
    a_by_id: dict[str, dict[str, object]],
    b_by_id: dict[str, dict[str, object]],
) -> dict[str, object]:
    ids = sorted(set(a_by_id) & set(b_by_id))
    annotations = [(_annotation(a_by_id[item]), _annotation(b_by_id[item])) for item in ids]
    both_eligible = [(a, b) for a, b in annotations if a["eligible"] is True and b["eligible"] is True]
    return {
        "eligibility": _nominal_agreement(
            [a["eligible"] for a, _ in annotations],
            [b["eligible"] for _, b in annotations],
        ),
        "claim_family_among_both_eligible": _nominal_agreement(
            [a["claim_family"] for a, _ in both_eligible],
            [b["claim_family"] for _, b in both_eligible],
        ),
        "supported_at_review_among_both_eligible": _nominal_agreement(
            [a["supported_at_review"] for a, _ in both_eligible],
            [b["supported_at_review"] for _, b in both_eligible],
        ),
        "unsupported_at_merge_among_both_eligible": _nominal_agreement(
            [a["unsupported_at_merge"] for a, _ in both_eligible],
            [b["unsupported_at_merge"] for _, b in both_eligible],
        ),
        "normalized_claim_exact_among_both_eligible": {
            "n": len(both_eligible),
            "percent_agreement": (
                sum(
                    str(a["normalized_claim"]).strip() == str(b["normalized_claim"]).strip()
                    for a, b in both_eligible
                )
                / len(both_eligible)
                if both_eligible
                else None
            ),
        },
    }


def adjudicate(
    annotator_a_path: Path,
    annotator_b_path: Path,
    resolved_path: Path,
    disagreements_path: Path,
    audit_path: Path,
    adjudications_path: Path | None = None,
) -> dict[str, object]:
    a_rows = load_rows(annotator_a_path)
    b_rows = load_rows(annotator_b_path)
    a_by_id, annotator_a = _validate_export(a_rows, "annotator-a")
    b_by_id, annotator_b = _validate_export(b_rows, "annotator-b")
    if annotator_a == annotator_b:
        raise ValueError("annotator exports must have distinct annotator_id values")
    if set(a_by_id) != set(b_by_id):
        missing_a = sorted(set(b_by_id) - set(a_by_id))
        missing_b = sorted(set(a_by_id) - set(b_by_id))
        raise ValueError(f"candidate sets differ; missing from A={missing_a}, missing from B={missing_b}")

    adjudications: dict[str, dict[str, object]] = {}
    adjudicator_id: str | None = None
    adjudications_hash: str | None = None
    if adjudications_path is not None:
        adjudication_rows = load_rows(adjudications_path)
        adjudications, adjudicator_id = _validate_export(adjudication_rows, "adjudicator")
        if adjudicator_id in {annotator_a, annotator_b}:
            raise ValueError("adjudicator_id must differ from both annotator_id values")
        adjudications_hash = _sha256(adjudications_path)

    agreements: list[dict[str, object]] = []
    disagreement_queue: list[dict[str, object]] = []
    unresolved_ids: list[str] = []
    adjudicated_count = 0
    input_hashes = {
        "annotator_a_sha256": _sha256(annotator_a_path),
        "annotator_b_sha256": _sha256(annotator_b_path),
    }
    if adjudications_hash:
        input_hashes["adjudications_sha256"] = adjudications_hash

    for candidate_id in sorted(a_by_id):
        a_row = a_by_id[candidate_id]
        b_row = b_by_id[candidate_id]
        annotation_a = _annotation(a_row)
        annotation_b = _annotation(b_row)
        if _decision(annotation_a) == _decision(annotation_b):
            row = dict(a_row)
            annotation = dict(annotation_a)
            annotation["annotator_id"] = None
            row["annotation"] = annotation
            row["annotation_provenance"] = {
                "status": "resolved",
                "resolution": "agreement",
                "annotator_ids": [annotator_a, annotator_b],
                "adjudicator_id": None,
                "input_hashes": input_hashes,
            }
            agreements.append(row)
            continue

        queue_row = dict(a_row)
        queue_row.pop("annotation_provenance", None)
        queue_row["annotation"] = {
            "eligible": None,
            "normalized_claim": None,
            "claim_family": None,
            "supported_at_review": None,
            "unsupported_at_merge": None,
            "exclusion_reason": None,
            "annotator_id": None,
        }
        blinded = [_blinded_annotation(annotation_a), _blinded_annotation(annotation_b)]
        # Avoid making one export consistently appear first while keeping the queue deterministic.
        if int(hashlib.sha256(candidate_id.encode()).hexdigest(), 16) % 2:
            blinded.reverse()
        queue_row["independent_annotations"] = blinded
        disagreement_queue.append(queue_row)
        adjudicated = adjudications.get(candidate_id)
        if adjudicated is None:
            unresolved_ids.append(candidate_id)
            continue
        row = dict(a_row)
        annotation = dict(_annotation(adjudicated))
        annotation["annotator_id"] = None
        row["annotation"] = annotation
        row["annotation_provenance"] = {
            "status": "resolved",
            "resolution": "adjudication",
            "annotator_ids": [annotator_a, annotator_b],
            "adjudicator_id": adjudicator_id,
            "input_hashes": input_hashes,
        }
        agreements.append(row)
        adjudicated_count += 1

    extraneous_adjudications = sorted(set(adjudications) - {str(row["candidate_id"]) for row in disagreement_queue})
    if extraneous_adjudications:
        raise ValueError(f"adjudications include non-disagreements: {extraneous_adjudications}")

    _write_jsonl(resolved_path, agreements)
    _write_jsonl(disagreements_path, disagreement_queue)
    audit: dict[str, object] = {
        "schema_version": 1,
        "input_candidates": len(a_by_id),
        "annotator_ids": [annotator_a, annotator_b],
        "exact_agreements": len(a_by_id) - len(disagreement_queue),
        "disagreements": len(disagreement_queue),
        "adjudicated": adjudicated_count,
        "unresolved": len(unresolved_ids),
        "unresolved_candidate_ids": unresolved_ids,
        "resolved_candidates": len(agreements),
        "eligible_resolved": sum(_annotation(row)["eligible"] is True for row in agreements),
        "excluded_resolved": sum(_annotation(row)["eligible"] is False for row in agreements),
        "independent_annotation_agreement": annotation_agreement(a_by_id, b_by_id),
        "input_hashes": input_hashes,
        "resolved_output": resolved_path.as_posix(),
        "disagreement_output": disagreements_path.as_posix(),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Merge independent Human PR annotations and adjudicate disagreements.")
    parser.add_argument("--annotator-a", type=Path, required=True)
    parser.add_argument("--annotator-b", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path)
    parser.add_argument("--resolved", type=Path, required=True)
    parser.add_argument("--disagreements", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = adjudicate(
        args.annotator_a,
        args.annotator_b,
        args.resolved,
        args.disagreements,
        args.audit,
        args.adjudications,
    )
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
