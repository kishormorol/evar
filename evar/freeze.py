from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
EVALUATOR_PATHS = ("evar",)


def build_manifest(
    project_root: Path,
    cases_path: Path,
    config_paths: Iterable[Path],
) -> dict[str, Any]:
    root = project_root.resolve()
    cases_file = _relative(root, cases_path)
    configs = [_relative(root, path) for path in config_paths]
    rows = _load_jsonl(root / cases_file)

    categorized: dict[str, str] = {cases_file: "cases"}
    for path in configs:
        categorized[path] = "config"
    for path in sorted((root / "prompts").glob("*.txt")):
        categorized[_relative(root, path)] = "prompt"
    for item in EVALUATOR_PATHS:
        path = root / item
        candidates = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for candidate in candidates:
            categorized[_relative(root, candidate)] = "evaluator"
    for row in rows:
        repo = root / str(row["repo_path"])
        for path in sorted(repo.rglob("*")):
            if path.is_file():
                categorized[_relative(root, path)] = "snapshot"

    files = {
        path: {
            "category": categorized[path],
            "sha256": _sha256(root / path),
            "bytes": (root / path).stat().st_size,
        }
        for path in sorted(categorized)
    }
    sources = sorted(
        {
            (str(row.get("source_repository", "")), str(row.get("source_commit", "")))
            for row in rows
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_at_freeze": _git_head(root),
        "benchmark": {
            "cases_file": cases_file,
            "case_count": len(rows),
            "label_counts": dict(sorted(Counter(str(row["ground_truth"]) for row in rows).items())),
            "claim_family_counts": dict(
                sorted(Counter(str(row["claim_family"]) for row in rows).items())
            ),
            "source_repository_counts": dict(
                sorted(Counter(str(row.get("source_repository", "")) for row in rows).items())
            ),
            "source_commits": [
                {"repository": repository, "commit": commit}
                for repository, commit in sources
            ],
        },
        "experiment": {
            "configs": configs,
            "protocols": ["ar", "ar_text", "evar_hard"],
            "judge_model": None,
        },
        "files": files,
    }


def write_manifest(manifest: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(project_root: Path, manifest_path: Path) -> list[str]:
    root = project_root.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        return [f"unsupported manifest schema: {manifest.get('schema_version')!r}"]
    errors: list[str] = []
    files = manifest.get("files")
    if not isinstance(files, dict):
        return ["manifest files must be an object"]
    for relative, expected in sorted(files.items()):
        if not isinstance(relative, str) or not isinstance(expected, dict):
            errors.append(f"invalid file entry: {relative!r}")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"missing: {relative}")
            continue
        actual = _sha256(path)
        if actual != expected.get("sha256"):
            errors.append(f"hash mismatch: {relative}")
        if path.stat().st_size != expected.get("bytes"):
            errors.append(f"size mismatch: {relative}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify an EVAR experiment freeze manifest.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--project-root", type=Path, default=Path("."))
    create.add_argument("--cases", type=Path, required=True)
    create.add_argument("--config", action="append", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--project-root", type=Path, default=Path("."))
    verify.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            manifest = build_manifest(args.project_root, args.cases, args.config)
            write_manifest(manifest, args.output)
            print(args.output)
            return 0
        errors = verify_manifest(args.project_root, args.manifest)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    print("freeze manifest: OK")
    return 0


def _relative(root: Path, path: Path) -> str:
    resolved = path if path.is_absolute() else root / path
    return resolved.resolve().relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: row must be an object")
        rows.append(row)
    return rows


def _git_head(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


if __name__ == "__main__":
    raise SystemExit(main())
