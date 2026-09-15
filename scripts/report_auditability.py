from __future__ import annotations

import argparse
import json
from pathlib import Path

from evar.eval.auditability import auditability_summary


def load_indexed_records(indices: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index_path in indices:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for run in index.get("canonical_runs", []):
            result_path = Path(str(run["result"]))
            rows.extend(
                json.loads(line)
                for line in result_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Summarize measurable EVAR auditability coverage.")
    parser.add_argument("--index", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    summary = auditability_summary(load_indexed_records(args.index), project_root=Path("."))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
