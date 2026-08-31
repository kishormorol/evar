from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.render_human_pr_200 import accepted


def _stable_key(candidate_id: str, seed: int) -> str:
    return hashlib.sha256(f"human-pr-200:{seed}:{candidate_id}".encode()).hexdigest()


def select(
    rows: list[dict[str, object]],
    *,
    target: int = 300,
    max_per_repo: int = 6,
    min_repositories: int = 40,
    seed: int = 53,
) -> list[dict[str, object]]:
    eligible = [row for row in rows if accepted(row)]
    if len(eligible) < target:
        raise ValueError(f"need {target} resolved eligible candidates; found {len(eligible)}")
    repos = {str(row["source_repository"]) for row in eligible}
    if len(repos) < min_repositories:
        raise ValueError(f"need at least {min_repositories} repositories; found {len(repos)}")

    candidates = sorted(eligible, key=lambda row: _stable_key(str(row["candidate_id"]), seed))
    chosen: list[dict[str, object]] = []
    repo_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()

    def add(row: dict[str, object]) -> None:
        chosen.append(row)
        repo_counts[str(row["source_repository"])] += 1
        language_counts[str(row.get("language", "unknown"))] += 1
        family_counts[str(row["annotation"]["claim_family"])] += 1

    # Establish repository breadth before filling the remaining strata.
    for row in candidates:
        repo = str(row["source_repository"])
        if repo_counts[repo] == 0:
            add(row)
            if len(repo_counts) == min_repositories:
                break

    remaining = [row for row in candidates if row not in chosen]
    while len(chosen) < target:
        feasible = [row for row in remaining if repo_counts[str(row["source_repository"])] < max_per_repo]
        if not feasible:
            raise ValueError(
                f"cannot select {target} candidates with max_per_repo={max_per_repo}; selected {len(chosen)}"
            )
        row = min(
            feasible,
            key=lambda item: (
                language_counts[str(item.get("language", "unknown"))],
                family_counts[str(item["annotation"]["claim_family"])],
                repo_counts[str(item["source_repository"])],
                _stable_key(str(item["candidate_id"]), seed),
            ),
        )
        add(row)
        remaining.remove(row)
    return chosen


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Freeze the powered Human PR benchmark sample.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--target", type=int, default=300)
    parser.add_argument("--max-per-repo", type=int, default=6)
    parser.add_argument("--min-repositories", type=int, default=40)
    parser.add_argument("--seed", type=int, default=53)
    args = parser.parse_args(argv)
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    chosen = select(
        rows,
        target=args.target,
        max_per_repo=args.max_per_repo,
        min_repositories=args.min_repositories,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in chosen)
    args.output.write_text(payload, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "seed": args.seed,
        "source": args.input.as_posix(),
        "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "output": args.output.as_posix(),
        "output_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "source_comments": len(chosen),
        "rendered_cases": len(chosen) * 2,
        "repository_count": len({str(row["source_repository"]) for row in chosen}),
        "max_per_repo": max(Counter(str(row["source_repository"]) for row in chosen).values()),
        "language_counts": dict(Counter(str(row.get("language", "unknown")) for row in chosen)),
        "claim_family_counts": dict(Counter(str(row["annotation"]["claim_family"]) for row in chosen)),
        "candidate_ids": [str(row["candidate_id"]) for row in chosen],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
