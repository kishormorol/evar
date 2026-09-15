from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = Path("benchmarks/human_pr_200")


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_repository(value: object) -> str:
    return str(value or "").strip().lower().removesuffix(".git").rstrip("/")


def _duplicates(rows: list[dict[str, object]], field: str) -> list[str]:
    counts = Counter(str(row.get(field, "")).strip() for row in rows)
    return sorted(value for value, count in counts.items() if value and count > 1)


def build_audit(
    selected_path: Path,
    protected_paths: list[Path],
    *,
    expected_selected: int = 300,
) -> dict[str, object]:
    selected = _load_jsonl(selected_path)
    protected = [row for path in protected_paths for row in _load_jsonl(path)]

    duplicate_fields = {
        field: _duplicates(selected, field)
        for field in ("candidate_id", "source_comment_url", "source_pull_request")
    }
    duplicate_fields = {field: values for field, values in duplicate_fields.items() if values}

    selected_repositories = {
        _normalized_repository(row.get("source_repository")) for row in selected
    } - {""}
    protected_repositories = {
        _normalized_repository(row.get("source_repository")) for row in protected
    } - {""}

    overlap_fields: dict[str, list[str]] = {}
    for field in ("candidate_id", "source_comment_url", "source_pull_request"):
        left = {str(row.get(field, "")).strip() for row in selected} - {""}
        right = {str(row.get(field, "")).strip() for row in protected} - {""}
        shared = sorted(left & right)
        if shared:
            overlap_fields[field] = shared
    repository_overlap = sorted(selected_repositories & protected_repositories)
    if repository_overlap:
        overlap_fields["source_repository"] = repository_overlap

    malformed_temporal_pairs = sorted(
        str(row.get("candidate_id", "<missing>"))
        for row in selected
        if not str(row.get("review_commit", "")).strip()
        or not str(row.get("merge_commit", "")).strip()
        or row.get("review_commit") == row.get("merge_commit")
    )
    passed = (
        len(selected) == expected_selected
        and not duplicate_fields
        and not overlap_fields
        and not malformed_temporal_pairs
    )
    return {
        "schema_version": 1,
        "passed": passed,
        "selected_count": len(selected),
        "expected_selected_count": expected_selected,
        "selected": selected_path.as_posix(),
        "selected_sha256": _sha256(selected_path),
        "protected_inputs": {
            path.as_posix(): _sha256(path) for path in protected_paths
        },
        "duplicate_identifiers": duplicate_fields,
        "protected_overlap": overlap_fields,
        "malformed_temporal_pairs": malformed_temporal_pairs,
        "definition": (
            "Fails on duplicate selected candidate/comment/PR identifiers, overlap with the "
            "protected Human PR holdout at candidate/comment/PR/repository level, unequal "
            "review and merge snapshots, or a non-300 selection."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Human PR 200 split contamination.")
    parser.add_argument("--selected", type=Path, default=BENCHMARK / "final_300.jsonl")
    parser.add_argument(
        "--protected",
        type=Path,
        action="append",
        default=[Path("benchmarks/human_pr_20/cases.jsonl")],
    )
    parser.add_argument("--output", type=Path, default=BENCHMARK / "contamination_audit.json")
    args = parser.parse_args(argv)
    selected = args.selected if args.selected.is_absolute() else ROOT / args.selected
    protected = [path if path.is_absolute() else ROOT / path for path in args.protected]
    output = args.output if args.output.is_absolute() else ROOT / args.output
    audit = build_audit(selected, protected)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return 0 if audit["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

