from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.adjudicate_human_pr_annotations import validate_export


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate one completed Human PR annotation export before handoff."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    summary = validate_export(args.input, args.queue)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
