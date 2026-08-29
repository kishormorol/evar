from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evar.eval.bootstrap import bootstrap_paired_delta_ci, bootstrap_rate_ci
from evar.eval.metrics import compute_efficiency_metrics, compute_fcr_scr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute EVAR FCR/SCR metrics from result JSONL.")
    parser.add_argument("--results", required=True, nargs="+", type=Path)
    parser.add_argument("--format", choices=["json", "table"], default="table")
    parser.add_argument("--bootstrap", type=int, default=0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--by-family",
        action="store_true",
        help="Also report FCR/SCR grouped by claim_family.",
    )
    parser.add_argument(
        "--costs",
        action="store_true",
        help="Also report aggregate token usage and per-case duration.",
    )
    args = parser.parse_args(argv)

    try:
        result_sets = [_load_jsonl(path) for path in args.results]
        summaries = [compute_fcr_scr(records) for records in result_sets]
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows = [asdict(summary) for summary in summaries]
    _add_bootstrap_intervals(rows, result_sets, n=args.bootstrap, seed=args.seed)

    family_rows: list[dict[str, object]] = []
    if args.by_family:
        family_rows, family_result_sets = _family_summaries(result_sets, rows)
        _add_bootstrap_intervals(
            family_rows,
            family_result_sets,
            n=args.bootstrap,
            seed=args.seed,
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

    efficiency_rows = (
        [asdict(compute_efficiency_metrics(records)) for records in result_sets]
        if args.costs
        else []
    )

    if args.format == "json":
        for row in rows:
            print(json.dumps(row, sort_keys=True))
        for row in comparison_rows:
            print(json.dumps(row, sort_keys=True))
        for row in family_rows:
            print(json.dumps(row, sort_keys=True))
        for row in efficiency_rows:
            print(json.dumps({"scope": "efficiency", **row}, sort_keys=True))
    else:
        _print_table(rows, include_ci=bool(args.bootstrap))
        if comparison_rows:
            print()
            _print_comparison_table(comparison_rows)
        if family_rows:
            print()
            _print_family_table(family_rows, include_ci=bool(args.bootstrap))
        if efficiency_rows:
            print()
            _print_efficiency_table(efficiency_rows)
    return 0


def _add_bootstrap_intervals(
    rows: list[dict[str, object]],
    result_sets: list[list[dict[str, Any]]],
    *,
    n: int,
    seed: int,
) -> None:
    if not n:
        return
    for row, records in zip(rows, result_sets):
        fcr = bootstrap_rate_ci(records, "fcr", n=n, seed=seed)
        scr = bootstrap_rate_ci(records, "scr", n=n, seed=seed)
        row.update(
            {
                "fcr_low": fcr.low,
                "fcr_high": fcr.high,
                "scr_low": scr.low,
                "scr_high": scr.high,
            }
        )


def _family_summaries(
    result_sets: list[list[dict[str, Any]]],
    overall_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[list[dict[str, Any]]]]:
    families = sorted(
        {
            str(record.get("claim_family") or "unknown")
            for records in result_sets
            for record in records
        }
    )
    rows: list[dict[str, object]] = []
    grouped_result_sets: list[list[dict[str, Any]]] = []
    for family in families:
        for records, overall_row in zip(result_sets, overall_rows):
            family_records = [
                record
                for record in records
                if str(record.get("claim_family") or "unknown") == family
            ]
            row: dict[str, object] = asdict(compute_fcr_scr(family_records))
            row["protocol"] = overall_row["protocol"]
            row["claim_family"] = family
            rows.append(row)
            grouped_result_sets.append(family_records)
    return rows, grouped_result_sets


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


def _print_family_table(rows: list[dict[str, Any]], *, include_ci: bool = False) -> None:
    headers = [
        "claim_family",
        "protocol",
        "n",
        "completed",
        "failed",
        "supported",
        "unsupported",
        "FCR",
        "SCR",
    ]
    if include_ci:
        headers = [
            "claim_family",
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
            str(row["claim_family"]),
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


def _print_efficiency_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "protocol",
        "n",
        "duration_n",
        "total_seconds",
        "mean_seconds",
        "token_n",
        "input_tokens",
        "output_tokens",
        "mean_input_tokens",
        "mean_output_tokens",
    ]
    print("\t".join(headers))
    for row in rows:
        print(
            "\t".join(
                [
                    str(row["protocol"]),
                    str(row["total_cases"]),
                    str(row["measured_duration_cases"]),
                    f"{row['total_duration_seconds']:.3f}",
                    _format_optional_number(row["mean_duration_seconds"], precision=3),
                    str(row["tokenized_cases"]),
                    str(row["total_input_tokens"]),
                    str(row["total_output_tokens"]),
                    _format_optional_number(row["mean_input_tokens"], precision=1),
                    _format_optional_number(row["mean_output_tokens"], precision=1),
                ]
            )
        )


def _format_optional_number(value: object, *, precision: int) -> str:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f"{value:.{precision}f}"
    return "NA"


if __name__ == "__main__":
    raise SystemExit(main())
