from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report_external_pr_50 import build_report


def _load_runs(index: dict[str, object]) -> list[dict[str, object]]:
    runs = []
    for item in index["canonical_runs"]:
        rows = [json.loads(line) for line in Path(item["result"]).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if len(rows) != 20:
            raise ValueError(f"{item['result']}: expected 20 rows, found {len(rows)}")
        for row in rows:
            row["_replicate_seed"] = item["seed"]
        runs.append({**item, "rows": rows})
    return runs


def render_markdown(report: dict[str, object], index: dict[str, object]) -> str:
    lines = [
        "# Human PR 20 Cross-Provider Results",
        "",
        "Matched 300-attempt comparison on the unchanged 20-case temporal holdout. Every attempted row is retained. Quality metrics are shown only for 20/20-valid cells; incomplete cells are operational reliability evidence.",
        "",
        f"> {index['replicate_note']}",
        "",
        "| Model | Protocol | Valid / attempted | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["overall"]:
        complete = row["failed_runs"] == 0
        fcr = f"{row['fcr']:.3f} ({row['fcr_low']:.3f}-{row['fcr_high']:.3f})" if complete else "--"
        scr = f"{row['scr']:.3f} ({row['scr_low']:.3f}-{row['scr_high']:.3f})" if complete else "--"
        lines.append(
            f"| {row['model']} | {row['protocol']} | {row['completed_cases']} / {row['total_cases']} | {fcr} | {scr} | "
            f"{row['verified_receipts']} / {row['failed_receipts']} | {row['total_input_tokens']:,} / {row['total_output_tokens']:,} | "
            f"{row['mean_duration_seconds']:.2f} | ${row['estimated_api_cost_usd']:.3f} |"
        )
    lines.extend([
        "",
        "## Paired changes from AR",
        "",
        "Each interval resamples the ten temporal source-comment pairs. Negative FCR and non-negative SCR deltas favor the candidate protocol.",
        "",
        "| Model | Comparison | Metric | Pairs | Delta (95% CI) |",
        "| --- | --- | --- | ---: | ---: |",
    ])
    complete_models = {
        model for model in {row["model"] for row in report["overall"]}
        if all(row["failed_runs"] == 0 for row in report["overall"] if row["model"] == model)
    }
    for row in report["paired_deltas"]:
        if row["model"] not in complete_models:
            continue
        lines.append(
            f"| {row['model']} | {row['comparison']} | {row['metric'].upper()} | {row['paired_observations']} | "
            f"{row['estimate']:.3f} ({row['low']:.3f}-{row['high']:.3f}) |"
        )
    lines.extend([
        "",
        "## Operational accounting",
        "",
        f"Across all cells, {report['completed_attempts']} of {report['attempted_decisions']} attempts produced valid decisions and {report['failed_attempts']} failed before scoring. Failures remain in denominators for reliability but not in FCR/SCR denominators. Because missingness is model-dependent, we do not pool the surviving decisions.",
    ])
    lines.extend([
        "",
        "## Scope",
        "",
        "This is a model-diversity extension, not a new-data extension. It improves cross-provider validity but does not increase the number of independent human review comments. The larger Human PR 200 pool remains unlabeled until two independent experts and a third adjudicator complete the frozen protocol.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the complete Human PR 20 cross-provider report.")
    parser.add_argument("--index", type=Path, default=Path("benchmarks/human_pr_20/cross_provider_run_index.json"))
    parser.add_argument("--json", type=Path, default=Path("benchmarks/human_pr_20/cross_provider_report.json"))
    parser.add_argument("--markdown", type=Path, default=Path("benchmarks/human_pr_20/CROSS_PROVIDER_RESULTS.md"))
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=53)
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    runs = _load_runs(index)
    report = build_report(runs, bootstrap=args.bootstrap, seed=args.seed)
    report["attempted_decisions"] = sum(row["total_cases"] for row in report["overall"])
    report["completed_attempts"] = sum(row["completed_cases"] for row in report["overall"])
    report["failed_attempts"] = sum(row["failed_runs"] for row in report["overall"])
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report, index), encoding="utf-8")
    print(args.json)
    print(args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
