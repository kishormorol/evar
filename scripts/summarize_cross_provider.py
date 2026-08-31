"""Summarize completed cross-provider JSONL runs without judging model outputs."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path


def summarize_files(files: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for filename in sorted(files):
        parsed = []
        for line in filename.read_text(encoding="utf-8").splitlines():
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not parsed:
            continue
        metadata = parsed[0].get("metadata", {})
        model = metadata.get("model", {}).get("model", "unknown")
        rows.append({
            "file": str(filename),
            "model": model,
            "protocol": parsed[0].get("protocol"),
            "rows": len(parsed),
            "ok": sum(row.get("run_status") == "ok" for row in parsed),
            "failed": sum(row.get("run_status") == "failed" for row in parsed),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        files = [Path(path) for path in manifest["result_files"]]
        source = str(args.manifest)
    elif args.root:
        files = [Path(path) for path in glob.glob(str(args.root / "*.jsonl"))]
        source = str(args.root)
    else:
        parser.error("provide ROOT or --manifest")
    rows = summarize_files(files)
    payload = {"source": source, "cells": rows, "totals": {
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
