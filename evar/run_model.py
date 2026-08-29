from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evar.agents.model_critic import parse_critic_decision
from evar.agents.model_reviewer import ModelOutputError, parse_reviewer_receipts
from evar.benchmark.loader import BenchmarkValidationError, load_jsonl_cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate model adapter structured outputs.")
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--reviewer-output", type=Path)
    parser.add_argument("--critic-output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        cases = load_jsonl_cases(args.cases)
        reviewer_raw = _read_or_default(
            args.reviewer_output,
            json.dumps(
                {
                    "receipts": [
                        {
                            "claim_id": "dry-run",
                            "claim": "dry-run claim",
                            "evidence_type": "structural",
                            "file": "README.md",
                            "falsification_condition": "dry-run only",
                        }
                    ]
                }
            ),
        )
        critic_raw = _read_or_default(args.critic_output, '{"decision":"CHALLENGE_EVIDENCE"}')
        receipts = parse_reviewer_receipts(reviewer_raw)
        critic_decision = parse_critic_decision(critic_raw)
    except (OSError, BenchmarkValidationError, ModelOutputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "run_status": "ok",
                "dry_run": bool(args.dry_run),
                "case_count": len(cases),
                "parsed_receipts": len(receipts),
                "critic_decision": critic_decision.value,
            },
            sort_keys=True,
        )
    )
    return 0


def _read_or_default(path: Path | None, default: str) -> str:
    if path is None:
        return default
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
