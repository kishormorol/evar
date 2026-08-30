from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def select(
    rows: list[dict[str, object]], *, per_language: int, max_per_repo: int, allow_underfilled: bool = False
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["language"])].append(row)
    selected: list[dict[str, object]] = []
    for language in sorted(grouped):
        counts: Counter[str] = Counter()
        candidates = sorted(
            grouped[language],
            key=lambda row: (-int(row["priority_score"]), str(row["candidate_id"])),
        )
        for row in candidates:
            repository = str(row["source_repository"])
            if counts[repository] >= max_per_repo:
                continue
            selected.append(row)
            counts[repository] += 1
            if counts.total() >= per_language:
                break
        if counts.total() < per_language and not allow_underfilled:
            raise ValueError(
                f"Could not select {per_language} {language} candidates with max_per_repo={max_per_repo}"
            )
    return selected


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Select a balanced Human PR annotation tranche.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-language", type=int, default=50)
    parser.add_argument("--max-per-repository", type=int, default=6)
    parser.add_argument("--allow-underfilled", action="store_true")
    args = parser.parse_args(argv)
    if args.per_language < 1 or args.max_per_repository < 1:
        parser.error("selection limits must be positive")
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = select(
        rows,
        per_language=args.per_language,
        max_per_repo=args.max_per_repository,
        allow_underfilled=args.allow_underfilled,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in selected),
        encoding="utf-8",
    )
    print(f"selected {len(selected)} candidates to {args.output}")


if __name__ == "__main__":
    main()
