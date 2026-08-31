from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evar.audit_results import audit_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the canonical Human PR 20 cross-provider matrix."
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("benchmarks/human_pr_20/cross_provider_run_index.json"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("benchmarks/human_pr_20/cross_provider_freeze_manifest.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/human_pr_20/cross_provider_audit.json"),
    )
    args = parser.parse_args()

    index = json.loads(args.index.read_text(encoding="utf-8"))
    results = [Path(item["result"]) for item in index["canonical_runs"]]
    report = audit_results(
        Path("."),
        Path("benchmarks/human_pr_20/cases.jsonl"),
        args.manifest,
        results,
        allow_failed_runs=True,
    )
    args.output.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
