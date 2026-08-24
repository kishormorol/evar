from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare EVAR pilot result JSONL files.")
    parser.add_argument("results", nargs="+", type=Path)
    args = parser.parse_args(argv)

    try:
        rows = [_summary(_load_jsonl(path)) for path in args.results]
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    headers = [
        "Protocol",
        "Supported claims",
        "Unsupported claims",
        "Accepted supported",
        "Accepted unsupported",
        "SCR",
        "FCR",
        "Invalid model outputs",
        "Verifier failures",
        "Mean input tokens",
        "Mean output tokens",
    ]
    print("\t".join(headers))
    for row in rows:
        print(
            "\t".join(
                [
                    str(row["protocol"]),
                    str(row["supported"]),
                    str(row["unsupported"]),
                    str(row["accepted_supported"]),
                    str(row["accepted_unsupported"]),
                    f"{row['scr']:.3f}",
                    f"{row['fcr']:.3f}",
                    str(row["invalid_model_outputs"]),
                    str(row["verifier_failures"]),
                    _fmt_optional(row["mean_input_tokens"]),
                    _fmt_optional(row["mean_output_tokens"]),
                ]
            )
        )
    return 0


def _summary(records: list[dict[str, Any]]) -> dict[str, object]:
    protocol_values = {str(record.get("protocol", "")) for record in records}
    protocol = protocol_values.pop() if len(protocol_values) == 1 else "mixed"
    completed = [record for record in records if record.get("run_status", "ok") == "ok"]
    supported = [record for record in completed if record.get("ground_truth") == "SUPPORTED"]
    unsupported = [record for record in completed if record.get("ground_truth") == "UNSUPPORTED"]
    accepted_supported = [record for record in supported if bool(record.get("final_actionable"))]
    accepted_unsupported = [record for record in unsupported if bool(record.get("final_actionable"))]
    input_tokens = _tokens(records, "input_tokens")
    output_tokens = _tokens(records, "output_tokens")
    return {
        "protocol": protocol,
        "supported": len(supported),
        "unsupported": len(unsupported),
        "accepted_supported": len(accepted_supported),
        "accepted_unsupported": len(accepted_unsupported),
        "scr": len(accepted_supported) / len(supported) if supported else 0.0,
        "fcr": len(accepted_unsupported) / len(unsupported) if unsupported else 0.0,
        "invalid_model_outputs": sum(
            1
            for record in records
            if record.get("run_status") == "failed"
            and record.get("failure", {}).get("type") == "ModelOutputError"
        ),
        "verifier_failures": sum(
            1
            for record in completed
            if record.get("verification_status") in ("FAILED", "UNVERIFIABLE")
        ),
        "mean_input_tokens": sum(input_tokens) / len(input_tokens) if input_tokens else None,
        "mean_output_tokens": sum(output_tokens) / len(output_tokens) if output_tokens else None,
    }


def _tokens(records: list[dict[str, Any]], key: str) -> list[int]:
    values: list[int] = []
    for record in records:
        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        for model_key in ("reviewer_model", "critic_model"):
            model = metadata.get(model_key)
            if isinstance(model, dict) and isinstance(model.get(key), int):
                values.append(model[key])
    return values


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: row must be a JSON object")
            records.append(record)
    return records


def _fmt_optional(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
