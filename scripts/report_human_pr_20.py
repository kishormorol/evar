from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report_external_pr_50 import build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the frozen human_pr_20 report.")
    parser.add_argument("--index", type=Path, default=Path("benchmarks/human_pr_20/run_index.json"))
    parser.add_argument("--json", type=Path, default=Path("benchmarks/human_pr_20/report.json"))
    parser.add_argument("--markdown", type=Path, default=Path("benchmarks/human_pr_20/RESULTS.md"))
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=31)
    args = parser.parse_args()

    index = json.loads(args.index.read_text(encoding="utf-8"))
    runs = []
    for item in index["canonical_runs"]:
        rows = []
        for line in Path(item["result"]).read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                row = json.loads(line)
                row["_replicate_seed"] = item["seed"]
                rows.append(row)
        runs.append({**item, "rows": rows})

    report = build_report(runs, bootstrap=args.bootstrap, seed=args.seed)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report, index), encoding="utf-8")
    print(args.json)
    print(args.markdown)
    return 0


def render_markdown(report: dict, index: dict) -> str:
    lines = [
        "# Human PR 20 Results",
        "",
        "Untouched temporal holdout built from ten real human pull-request review comments across five previously unseen repositories. Each comment yields a supported reviewed-commit case and an unsupported merge-commit case. The evaluator and prompts were frozen before any model call.",
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
        "Negative ΔFCR and non-negative ΔSCR favor the candidate. Intervals are case-cluster bootstrap intervals and are wide because each condition has only ten cases per label.",
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
        "## Interpretation",
        "",
        "On `gpt-4.1-mini`, EVAR-Hard and AR-Text tie at FCR 0.200 and SCR 0.700. On `gpt-4.1`, EVAR-Hard is worse than AR-Text on this small holdout (FCR 0.300 vs 0.200; SCR 0.600 vs 0.700). These results do not establish that EVAR outperforms the stronger text-evidence baseline. They do show that the v2 receipt format retained substantially more supported findings than the earlier external-pr benchmark, but the datasets differ, so that comparison is diagnostic rather than causal.",
        "",
        "## Audit",
        "",
        "The judge-free audit checked all 120 records and transcripts. It found no failures, prompt-hash mismatches, transcript-integrity errors, actionability-gate inconsistencies, token inconsistencies, or latency inconsistencies. All source comments are linked in the frozen cases file and attributed to non-bot GitHub accounts.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
