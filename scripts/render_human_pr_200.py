from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path


FAMILIES = {
    "behavior_inversion",
    "missing_guard",
    "incorrect_call_relationship",
    "causal_mislocalization",
    "stale_evidence",
}


def load_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def accepted(row: dict[str, object]) -> bool:
    annotation = row.get("annotation")
    if not isinstance(annotation, dict):
        return False
    return (
        annotation.get("eligible") is True
        and isinstance(annotation.get("normalized_claim"), str)
        and bool(str(annotation["normalized_claim"]).strip())
        and annotation.get("claim_family") in FAMILIES
        and annotation.get("supported_at_review") is True
        and annotation.get("unsupported_at_merge") is True
    )


def render(rows: list[dict[str, object]], output_dir: Path) -> dict[str, object]:
    selected = [row for row in rows if accepted(row)]
    output_dir.mkdir(parents=True, exist_ok=True)
    repos_dir = output_dir / "repos"
    if repos_dir.exists():
        shutil.rmtree(repos_dir)
    repos_dir.mkdir(parents=True)
    cases: list[dict[str, object]] = []
    for pair_index, row in enumerate(selected, start=1):
        first = (pair_index - 1) * 2 + 1
        second = first + 1
        claim = str(row["annotation"]["normalized_claim"])
        for case_number, label, excerpt, commit, snapshot, paired in (
            (first, "SUPPORTED", row["review_excerpt"], row["review_commit"], "reviewed", second),
            (second, "UNSUPPORTED", row["merge_excerpt"], row["merge_commit"], "merged", first),
        ):
            case_id = f"humanpr200_{case_number:03d}"
            repo_path = Path("benchmarks/human_pr_200") / "repos" / f"case_{case_number:03d}"
            context_path = output_dir / "repos" / f"case_{case_number:03d}" / "context" / "target.txt"
            context_path.parent.mkdir(parents=True, exist_ok=True)
            context_path.write_text(str(excerpt), encoding="utf-8")
            cases.append(
                {
                    "case_id": case_id,
                    "repo_path": repo_path.as_posix(),
                    "task_description": "Evaluate a candidate finding derived from a public human pull-request review comment.",
                    "claim": claim,
                    "ground_truth": label,
                    "ground_truth_evidence": (
                        f"Human review thread {row['source_comment_url']}; exact {snapshot} snapshot {commit}."
                    ),
                    "validation_command": ["python", "-c", "print('context-only benchmark')"],
                    "claim_family": row["annotation"]["claim_family"],
                    "source_repository": row["source_repository"],
                    "source_commit": commit,
                    "source_pull_request": row["source_pull_request"],
                    "source_comment_url": row["source_comment_url"],
                    "source_comment_id": row["source_comment_id"],
                    "source_comment_author": row["source_comment_author"],
                    "source_comment_body": row["source_comment_body"],
                    "source_comment_path": row["source_comment_path"],
                    "source_comment_line": row["source_comment_line"],
                    "snapshot_kind": snapshot,
                    "paired_case_id": f"humanpr200_{paired:03d}",
                    "target_context_file": "context/target.txt",
                    "candidate_id": row["candidate_id"],
                }
            )
    cases_path = output_dir / "cases.jsonl"
    cases_path.write_text(
        "".join(json.dumps(case, sort_keys=True, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )
    return {
        "schema_version": 1,
        "candidate_count": len(rows),
        "accepted_source_comments": len(selected),
        "case_count": len(cases),
        "claim_family_counts": dict(Counter(str(row["annotation"]["claim_family"]) for row in selected)),
        "output": cases_path.as_posix(),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render adjudicated Human PR 200 candidates into paired cases.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args(argv)
    audit = render(load_rows(args.input), args.output_dir)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
