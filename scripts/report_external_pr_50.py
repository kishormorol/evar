from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from evar.eval.metrics import compute_efficiency_metrics, compute_fcr_scr


PRICE_PER_MILLION = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-5.6-luna": {"input": 0.20, "output": 1.20},
    "gpt-5.6-terra": {"input": 2.00, "output": 12.00},
    "gpt-5.6-sol": {"input": 4.00, "output": 20.00},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the frozen external_pr_50 report.")
    parser.add_argument("--index", type=Path, default=Path("benchmarks/external_pr_50/run_index.json"))
    parser.add_argument("--json", type=Path, default=Path("benchmarks/external_pr_50/report.json"))
    parser.add_argument("--markdown", type=Path, default=Path("benchmarks/external_pr_50/RESULTS.md"))
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    index = json.loads(args.index.read_text(encoding="utf-8"))
    runs = _load_runs(index)
    report = build_report(runs, bootstrap=args.bootstrap, seed=args.seed)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report, index), encoding="utf-8")
    print(args.json)
    print(args.markdown)
    return 0


def build_report(runs: list[dict[str, Any]], *, bootstrap: int, seed: int) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    run_rows: list[dict[str, Any]] = []
    for run in runs:
        rows = run["rows"]
        grouped[(run["model"], run["protocol"])].extend(rows)
        summary = asdict(compute_fcr_scr(rows))
        run_rows.append({
            "model": run["model"], "seed": run["seed"], "protocol": run["protocol"],
            "result": run["result"], **summary,
        })

    overall: list[dict[str, Any]] = []
    by_family: list[dict[str, Any]] = []
    for (model, protocol), rows in sorted(grouped.items()):
        overall.append(_summary_row(model, protocol, rows, bootstrap, seed))
        families = sorted({str(row.get("claim_family", "unknown")) for row in rows})
        for family in families:
            family_rows = [row for row in rows if row.get("claim_family") == family]
            by_family.append({
                "claim_family": family,
                **_summary_row(model, protocol, family_rows, bootstrap, seed),
            })

    comparisons: list[dict[str, Any]] = []
    for model in sorted({key[0] for key in grouped}):
        baseline = grouped[(model, "ar")]
        for protocol in ("ar_text", "evar_hard"):
            candidate = grouped[(model, protocol)]
            for metric in ("fcr", "scr"):
                estimate, low, high, pairs = _paired_cluster_ci(
                    baseline, candidate, metric, n=bootstrap, seed=seed
                )
                comparisons.append({
                    "model": model,
                    "comparison": f"{protocol}-ar",
                    "metric": metric,
                    "paired_observations": pairs,
                    "estimate": estimate,
                    "low": low,
                    "high": high,
                })

    return {
        "schema_version": 1,
        "bootstrap": {"samples": bootstrap, "seed": seed, "unit": "case_id cluster across replicates"},
        "pricing_usd_per_million_tokens": PRICE_PER_MILLION,
        "runs": sorted(run_rows, key=lambda row: (row["model"], row["seed"], row["protocol"])),
        "overall": overall,
        "by_family": by_family,
        "paired_deltas": comparisons,
    }


def _summary_row(
    model: str,
    protocol: str,
    rows: list[dict[str, Any]],
    bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    summary = asdict(compute_fcr_scr(rows))
    efficiency = asdict(compute_efficiency_metrics(rows))
    fcr_low, fcr_high = _cluster_rate_ci(rows, "fcr", n=bootstrap, seed=seed)
    scr_low, scr_high = _cluster_rate_ci(rows, "scr", n=bootstrap, seed=seed)
    pricing = PRICE_PER_MILLION[model]
    estimated_cost = (
        efficiency["total_input_tokens"] * pricing["input"]
        + efficiency["total_output_tokens"] * pricing["output"]
    ) / 1_000_000
    verified = sum(row.get("verification_status") == "VERIFIED" for row in rows)
    verification_failed = sum(row.get("verification_status") == "FAILED" for row in rows)
    return {
        "model": model,
        "protocol": protocol,
        **summary,
        "fcr_low": fcr_low,
        "fcr_high": fcr_high,
        "scr_low": scr_low,
        "scr_high": scr_high,
        "verified_receipts": verified,
        "failed_receipts": verification_failed,
        **{key: value for key, value in efficiency.items() if key != "protocol"},
        "estimated_api_cost_usd": estimated_cost,
    }


def _cluster_rate_ci(
    rows: list[dict[str, Any]], metric: str, *, n: int, seed: int
) -> tuple[float, float]:
    truth = "UNSUPPORTED" if metric == "fcr" else "SUPPORTED"
    eligible = [
        row for row in rows
        if row.get("run_status") == "ok" and row.get("ground_truth") == truth
    ]
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_case[str(row["case_id"])].append(row)
    case_ids = sorted(by_case)
    if not case_ids:
        return 0.0, 0.0
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n):
        sampled = [rng.choice(case_ids) for _ in case_ids]
        values = [bool(row.get("final_actionable")) for case_id in sampled for row in by_case[case_id]]
        samples.append(sum(values) / len(values))
    return _quantile(samples, 0.025), _quantile(samples, 0.975)


def _paired_cluster_ci(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    metric: str,
    *,
    n: int,
    seed: int,
) -> tuple[float, float, float, int]:
    truth = "UNSUPPORTED" if metric == "fcr" else "SUPPORTED"
    a = {
        (int(row["_replicate_seed"]), str(row["case_id"])): row
        for row in baseline
        if row.get("run_status") == "ok" and row.get("ground_truth") == truth
    }
    b = {
        (int(row["_replicate_seed"]), str(row["case_id"])): row
        for row in candidate
        if row.get("run_status") == "ok" and row.get("ground_truth") == truth
    }
    pairs = {key: (a[key], b[key]) for key in sorted(a.keys() & b.keys())}
    by_case: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for (_, case_id), pair in pairs.items():
        by_case[case_id].append(pair)
    case_ids = sorted(by_case)
    if not case_ids:
        return 0.0, 0.0, 0.0, 0

    def delta(selected: Iterable[str]) -> float:
        selected_pairs = [pair for case_id in selected for pair in by_case[case_id]]
        base_rate = sum(bool(pair[0].get("final_actionable")) for pair in selected_pairs) / len(selected_pairs)
        candidate_rate = sum(bool(pair[1].get("final_actionable")) for pair in selected_pairs) / len(selected_pairs)
        return candidate_rate - base_rate

    estimate = delta(case_ids)
    rng = random.Random(seed)
    samples = [delta(rng.choices(case_ids, k=len(case_ids))) for _ in range(n)]
    return estimate, _quantile(samples, 0.025), _quantile(samples, 0.975), len(pairs)


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def _load_runs(index: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for item in index["canonical_runs"]:
        rows = []
        for line in Path(item["result"]).read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                row = json.loads(line)
                row["_replicate_seed"] = item["seed"]
                rows.append(row)
        runs.append({**item, "rows": rows})
    return runs


def render_markdown(report: dict[str, Any], index: dict[str, Any]) -> str:
    lines = [
        "# External PR 50 Results",
        "",
        "Frozen evaluation over 50 commit-grounded claim cases, two models, three protocols, and two independent replicate labels. Confidence intervals use 10,000 case-cluster bootstrap samples.",
        "",
        f"> {index['replicate_note']}",
        "",
        "## Aggregate results",
        "",
        "| Model | Protocol | n | Failed | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["overall"]:
        lines.append(
            "| {model} | {protocol} | {total_cases} | {failed_runs} | {fcr:.3f} ({fcr_low:.3f}–{fcr_high:.3f}) | "
            "{scr:.3f} ({scr_low:.3f}–{scr_high:.3f}) | {verified_receipts} / {failed_receipts} | "
            "{total_input_tokens:,} / {total_output_tokens:,} | {mean_duration_seconds:.2f} | ${estimated_api_cost_usd:.3f} |".format(**row)
        )
    lines.extend([
        "",
        "## Paired deltas from AR",
        "",
        "Negative ΔFCR and non-negative ΔSCR favor the candidate protocol.",
        "",
        "| Model | Comparison | Metric | Pairs | Delta (95% CI) |",
        "| --- | --- | --- | ---: | ---: |",
    ])
    for row in report["paired_deltas"]:
        lines.append(
            f"| {row['model']} | {row['comparison']} | {row['metric'].upper()} | {row['paired_observations']} | "
            f"{row['estimate']:.3f} ({row['low']:.3f}–{row['high']:.3f}) |"
        )
    lines.extend([
        "",
        "## Per-family results",
        "",
        "| Model | Protocol | Family | n | FCR | SCR |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ])
    for row in report["by_family"]:
        lines.append(
            f"| {row['model']} | {row['protocol']} | {row['claim_family']} | {row['total_cases']} | {row['fcr']:.3f} | {row['scr']:.3f} |"
        )
    lines.extend([
        "",
        "## Audit and exclusions",
        "",
        "The judge-free audit checked all 600 canonical records and their transcripts. It reported one `ModelOutputError` in the mini EVAR-Hard seed-7 run and the associated missing failed-row experiment metadata. No prompt-hash, transcript-integrity, actionability-gate, token, or latency inconsistency was detected.",
        "",
        f"Four infrastructure-invalid attempts are preserved under `results/external_pr_50/excluded/` and excluded for the reasons recorded in `{Path('benchmarks/external_pr_50/run_index.json')}`.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
