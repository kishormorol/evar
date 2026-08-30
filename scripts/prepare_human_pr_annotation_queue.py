from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ANNOTATION_FIELDS = {
    "eligible": None,
    "normalized_claim": None,
    "claim_family": None,
    "supported_at_review": None,
    "unsupported_at_merge": None,
    "exclusion_reason": None,
    "annotator_id": None,
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Prepare a blinded human PR candidate annotation queue.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("Candidate input is empty")
    if len({row["candidate_id"] for row in rows}) != len(rows):
        raise ValueError("Candidate IDs are not unique")

    queue: list[dict[str, object]] = []
    for row in rows:
        queue.append(
            {
                "queue_id": hashlib.sha256(f"hpr200-annotation:{row['candidate_id']}".encode()).hexdigest()[:16],
                "candidate_id": row["candidate_id"],
                "language": row["language"],
                "source_repository": row["source_repository"],
                "source_pull_request": row["source_pull_request"],
                "source_pull_number": row["source_pull_number"],
                "source_pull_title": row["source_pull_title"],
                "source_pull_merged_at": row["source_pull_merged_at"],
                "source_comment_id": row["source_comment_id"],
                "source_comment_url": row["source_comment_url"],
                "source_comment_author": row["source_comment_author"],
                "source_comment_author_association": row["source_comment_author_association"],
                "source_comment_created_at": row["source_comment_created_at"],
                "source_comment_body": row["source_comment_body"],
                "source_comment_diff_hunk": row["source_comment_diff_hunk"],
                "source_comment_path": row["source_comment_path"],
                "source_comment_line": row["source_comment_line"],
                "review_commit": row["review_commit"],
                "merge_commit": row["merge_commit"],
                "merge_line": row["merge_line"],
                "review_file_sha256": row["review_file_sha256"],
                "merge_file_sha256": row["merge_file_sha256"],
                "review_excerpt": row["review_excerpt"],
                "merge_excerpt": row["merge_excerpt"],
                "annotation": dict(ANNOTATION_FIELDS),
            }
        )
    queue.sort(key=lambda row: str(row["queue_id"]))
    for position, row in enumerate(queue, start=1):
        row["blind_order"] = position

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in queue),
        encoding="utf-8",
    )
    print(f"wrote {len(queue)} blinded annotation records to {args.output}")


if __name__ == "__main__":
    main()
