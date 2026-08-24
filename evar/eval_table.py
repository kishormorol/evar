from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evar.eval.bootstrap import bootstrap_paired_delta_ci, bootstrap_rate_ci
from evar.eval.metrics import compute_fcr_scr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute EVAR FCR/SCR metrics from result JSONL.")
    parser.add_argument("--results", required=True, nargs="+", type=Path)
    parser.add_argument("--format", choices=["json", "table"], default="table")
    parser.add_argument("--bootstrap", type=int, default=0)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    try:
        result_sets = [_load_jsonl(path) for path in args.results]
        summaries = [compute_fcr_scr(records) for records in result_sets]
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows = [asdict(summary) for summary in summaries]
    if args.bootstrap:
        for row, records in zip(rows, result_sets):
            fcr = bootstrap_rate_ci(records, "fcr", n=args.bootstrap, seed=args.seed)
            scr = bootstrap_rate_ci(records, "scr", n=args.bootstrap, seed=args.seed)
            row.update(
                {
                    "fcr_low": fcr.low,
                    "fcr_high": fcr.high,
                    "scr_low": scr.low,
                    "scr_high": scr.high,
                }
            )

    comparison_rows: list[dict[str, object]] = []
    if args.bootstrap and len(result_sets) >= 2:
        base_records = result_sets[0]
        base_protocol = rows[0]["protocol"]
        for row, records in zip(rows[1:], result_sets[1:]):
            fcr_delta = bootstrap_paired_delta_ci(base_records, records, "fcr", n=args.bootstrap, seed=args.seed)
            scr_delta = bootstrap_paired_delta_ci(base_records, records, "scr", n=args.bootstrap, seed=args.seed)
            comparison_rows.append(
                {
                    "comparison": f"{row['protocol']}-{base_protocol}",
                    "delta_fcr": fcr_delta.estimate,
                    "delta_fcr_low": fcr_delta.low,
                    "delta_fcr_high": fcr_delta.high,
                    "delta_scr": scr_delta.estimate,
                    "delta_scr_low": scr_delta.low,
                    "delta_scr_high": scr_delta.high,
                }
            )

    if args.format == "json":
        for row in rows:
            print(json.dumps(row, sort_keys=True))
        for row in comparison_rows:
            print(json.dumps(row, sort_keys=True))
    else:
        _print_table(rows, include_ci=bool(args.bootstrap))
        if comparison_rows:
            print()
            _print_comparison_table(comparison_rows)
    return 0


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
                raise ValueError(f"{path}:{line_number}: result row must be a JSON object")
            records.append(record)
    return records


def _print_table(rows: list[dict[str, Any]], *, include_ci: bool = False) -> None:
    headers = ["protocol", "n", "completed", "failed", "supported", "unsupported", "FCR", "SCR"]
    if include_ci:
        headers = [
            "protocol",
            "n",
            "completed",
            "failed",
            "supported",
            "unsupported",
            "FCR",
            "FCR_low",
            "FCR_high",
            "SCR",
            "SCR_low",
            "SCR_high",
        ]
    print("\t".join(headers))
    for row in rows:
        values = [
            str(row["protocol"]),
            str(row["total_cases"]),
            str(row["completed_cases"]),
            str(row["failed_runs"]),
            str(row["supported_cases"]),
            str(row["unsupported_cases"]),
            f"{row['fcr']:.3f}",
        ]
        if include_ci:
            values.extend([f"{row['fcr_low']:.3f}", f"{row['fcr_high']:.3f}"])
        values.append(f"{row['scr']:.3f}")
        if include_ci:
            values.extend([f"{row['scr_low']:.3f}", f"{row['scr_high']:.3f}"])
        print("\t".join(values))


def _print_comparison_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "comparison",
        "delta_FCR",
        "delta_FCR_low",
        "delta_FCR_high",
        "delta_SCR",
        "delta_SCR_low",
        "delta_SCR_high",
    ]
    print("\t".join(headers))
    for row in rows:
        print(
            "\t".join(
                [
                    str(row["comparison"]),
                    f"{row['delta_fcr']:.3f}",
                    f"{row['delta_fcr_low']:.3f}",
                    f"{row['delta_fcr_high']:.3f}",
                    f"{row['delta_scr']:.3f}",
                    f"{row['delta_scr_low']:.3f}",
                    f"{row['delta_scr_high']:.3f}",
                ]
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
