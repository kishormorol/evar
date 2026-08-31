"""Summarize completed cross-provider JSONL runs without judging model outputs."""
from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from pathlib import Path


def summarize(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for filename in sorted(glob.glob(str(root / "*.jsonl"))):
        parsed = []
        for line in Path(filename).read_text(encoding="utf-8").splitlines():
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not parsed:
            continue
        metadata = parsed[0].get("metadata", {})
        model = metadata.get("model", {}).get("model", "unknown")
        rows.append({
            "file": str(Path(filename).relative_to(root.parent.parent)),
            "model": model,
            "protocol": parsed[0].get("protocol"),
            "rows": len(parsed),
            "ok": sum(row.get("run_status") == "ok" for row in parsed),
            "failed": sum(row.get("run_status") == "failed" for row in parsed),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = summarize(args.root)
    payload = {"source": str(args.root), "cells": rows, "totals": {
        "files": len(rows), "rows": sum(row["rows"] for row in rows),
        "ok": sum(row["ok"] for row in rows), "failed": sum(row["failed"] for row in rows),
    }}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
