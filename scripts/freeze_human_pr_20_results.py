from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks/human_pr_20"
RESULTS = ROOT / "results/human_pr_20"


def main() -> None:
    index = json.loads((BENCHMARK / "run_index.json").read_text(encoding="utf-8"))
    categorized = {
        BENCHMARK / "run_index.json": "run_index",
        BENCHMARK / "audit_report.json": "audit",
        BENCHMARK / "report.json": "report",
        BENCHMARK / "RESULTS.md": "report",
    }
    for run in index["canonical_runs"]:
        result = ROOT / run["result"]
        categorized[result] = "canonical_result"
        first = json.loads(next(line for line in result.read_text(encoding="utf-8").splitlines() if line.strip()))
        for transcript in sorted((RESULTS / "transcripts" / first["run_id"]).glob("*.json")):
            categorized[transcript] = "canonical_transcript"

    files = {}
    for path, category in sorted(categorized.items(), key=lambda item: str(item[0])):
        if not path.is_file():
            raise FileNotFoundError(path)
        files[path.relative_to(ROOT).as_posix()] = {
            "category": category,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_freeze_manifest": "benchmarks/human_pr_20/freeze_manifest.json",
        "canonical_runs": len(index["canonical_runs"]),
        "canonical_records": 120,
        "files": files,
    }
    output = BENCHMARK / "results_manifest.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    print(f"hashed files: {len(files)}")


if __name__ == "__main__":
    main()
