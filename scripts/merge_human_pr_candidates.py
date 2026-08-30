from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Merge immutable human PR candidate waves.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args(argv)

    rows: list[dict[str, object]] = []
    seen: dict[str, str] = {}
    seen_comments: dict[int, str] = {}
    seen_pulls: dict[str, str] = {}
    for input_path in args.inputs:
        for line in input_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            candidate_id = str(row["candidate_id"])
            comment_id = int(row["source_comment_id"])
            pull = str(row["source_pull_request"])
            row_hash = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            if candidate_id in seen:
                if seen[candidate_id] != row_hash:
                    raise ValueError(f"Conflicting candidate ID: {candidate_id}")
                continue
            if comment_id in seen_comments:
                raise ValueError(f"Duplicate source comment: {comment_id}")
            if pull in seen_pulls:
                raise ValueError(f"Multiple candidates from one pull request: {pull}")
            seen[candidate_id] = row_hash
            seen_comments[comment_id] = candidate_id
            seen_pulls[pull] = candidate_id
            rows.append(row)

    rows.sort(key=lambda row: (str(row["language"]), -int(row["priority_score"]), str(row["candidate_id"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    audit = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_files": [path.as_posix() for path in args.inputs],
        "candidate_count": len(rows),
        "repository_count": len({str(row["source_repository"]) for row in rows}),
        "pull_request_count": len(seen_pulls),
        "comment_count": len(seen_comments),
        "author_count": len({str(row["source_comment_author"]) for row in rows}),
        "language_counts": dict(sorted(Counter(str(row["language"]) for row in rows).items())),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"merged {len(rows)} candidates into {args.output}")


if __name__ == "__main__":
    main()
