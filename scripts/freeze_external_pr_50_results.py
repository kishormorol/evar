from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "benchmarks/external_pr_50/run_index.json"
OUTPUT = ROOT / "benchmarks/external_pr_50/results_manifest.json"


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    categorized: dict[Path, str] = {
        INDEX: "run_index",
        ROOT / "benchmarks/external_pr_50/audit_report.json": "audit",
        ROOT / "benchmarks/external_pr_50/report.json": "report",
        ROOT / "benchmarks/external_pr_50/RESULTS.md": "report",
    }
    for run in index["canonical_runs"]:
        result = ROOT / run["result"]
        categorized[result] = "canonical_result"
        run_id = _run_id(result)
        for transcript in sorted((ROOT / "results/external_pr_50/transcripts" / run_id).glob("*.json")):
            categorized[transcript] = "canonical_transcript"
    for attempt in index["excluded_attempts"]:
        result = ROOT / attempt["result"]
        categorized[result] = "excluded_result"
        run_id = _run_id(result)
        for transcript in sorted((ROOT / "results/external_pr_50/excluded/transcripts" / run_id).glob("*.json")):
            categorized[transcript] = "excluded_transcript"

    files: dict[str, dict[str, Any]] = {}
    for path, category in sorted(categorized.items(), key=lambda item: str(item[0])):
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = {
            "category": category,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_freeze_manifest": "benchmarks/external_pr_50/freeze_manifest.json",
        "canonical_runs": len(index["canonical_runs"]),
        "excluded_attempts": len(index["excluded_attempts"]),
        "canonical_records": 600,
        "files": files,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))
    print(f"hashed files: {len(files)}")


def _run_id(result: Path) -> str:
    first = json.loads(next(line for line in result.read_text(encoding="utf-8").splitlines() if line.strip()))
    return str(first["run_id"])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
