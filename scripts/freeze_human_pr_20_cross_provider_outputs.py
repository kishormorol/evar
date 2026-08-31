from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks/human_pr_20"
INDEX = BENCHMARK / "cross_provider_run_index.json"
OUTPUT = BENCHMARK / "cross_provider_results_manifest.json"


def _entry(path: Path, category: str) -> dict[str, object]:
    return {
        "bytes": path.stat().st_size,
        "category": category,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    files: dict[str, dict[str, object]] = {}
    rows = 0
    failures = 0
    transcript_paths: set[Path] = set()
    for run in index["canonical_runs"]:
        result = ROOT / run["result"]
        parsed = [json.loads(line) for line in result.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if len(parsed) != 20:
            raise ValueError(f"{result}: expected 20 rows, found {len(parsed)}")
        rows += len(parsed)
        failures += sum(row.get("run_status") != "ok" for row in parsed)
        files[result.relative_to(ROOT).as_posix()] = _entry(result, "result")
        for row in parsed:
            transcript = ROOT / row["transcript_path"]
            transcript_paths.add(transcript)
    for transcript in sorted(transcript_paths):
        files[transcript.relative_to(ROOT).as_posix()] = _entry(transcript, "transcript")

    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_index": INDEX.relative_to(ROOT).as_posix(),
        "attempted_decisions": rows,
        "valid_decisions": rows - failures,
        "failed_decisions": failures,
        "files": dict(sorted(files.items())),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))
    print(f"hashed files: {len(files)}")


if __name__ == "__main__":
    main()
