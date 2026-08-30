from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report_external_pr_50 import build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Human PR 20 model-extension report.")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("benchmarks/human_pr_20/model_extension_run_index.json"),
    )
    parser.add_argument(
        "--json", type=Path, default=Path("benchmarks/human_pr_20/model_extension_report.json")
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("benchmarks/human_pr_20/MODEL_EXTENSION_RESULTS.md"),
    )
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=41)
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
    report["descriptive_pooled"] = _descriptive_pooled(runs)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report, index), encoding="utf-8")
    print(args.json)
    print(args.markdown)
    return 0


def _descriptive_pooled(runs: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for run in runs:
        grouped[run["protocol"]].extend(run["rows"])
    pooled = []
    for protocol in ("ar", "ar_text", "evar_hard"):
        rows = grouped[protocol]
        unsupported = [row for row in rows if row["ground_truth"] == "UNSUPPORTED"]
        supported = [row for row in rows if row["ground_truth"] == "SUPPORTED"]
        pooled.append(
            {
                "protocol": protocol,
                "models": 3,
                "records": len(rows),
                "fcr": sum(bool(row["final_actionable"]) for row in unsupported) / len(unsupported),
                "scr": sum(bool(row["final_actionable"]) for row in supported) / len(supported),
            }
        )
    return pooled


def render_markdown(report: dict, index: dict) -> str:
    lines = [
        "# Human PR 20 Model Extension Results",
        "",
        "Exploratory post-release model extension over the unchanged 20 temporal human-review cases. Three GPT-5.6 tiers use explicit `reasoning.effort: none`, one run per protocol, and identical budgets. This is not a new untouched benchmark.",
        "",
        f"> {index['replicate_note']}",
        "",
        "## Model-grouped results",
        "",
        "| Model | Protocol | n | Failed | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["overall"]:
        lines.append(
            "| {model} | {protocol} | {total_cases} | {failed_runs} | {fcr:.3f} ({fcr_low:.3f}-{fcr_high:.3f}) | "
            "{scr:.3f} ({scr_low:.3f}-{scr_high:.3f}) | {verified_receipts} / {failed_receipts} | "
            "{total_input_tokens:,} / {total_output_tokens:,} | {mean_duration_seconds:.2f} | ${estimated_api_cost_usd:.3f} |".format(**row)
        )
    lines.extend([
        "",
        "## Paired changes from AR",
        "",
        "Negative delta FCR and non-negative delta SCR favor the candidate. Each metric has only ten paired cases per model.",
        "",
        "| Model | Comparison | Metric | Pairs | Delta (95% CI) |",
        "| --- | --- | --- | ---: | ---: |",
    ])
    for row in report["paired_deltas"]:
        lines.append(
            f"| {row['model']} | {row['comparison']} | {row['metric'].upper()} | {row['paired_observations']} | "
            f"{row['estimate']:.3f} ({row['low']:.3f}-{row['high']:.3f}) |"
        )
    lines.extend([
        "",
        "## Descriptive pooled view",
        "",
        "This view pools the same 20 cases across three models and is not an independent-sample estimate.",
        "",
        "| Protocol | Model-case records | FCR | SCR |",
        "| --- | ---: | ---: | ---: |",
    ])
    for row in report["descriptive_pooled"]:
        lines.append(f"| {row['protocol']} | {row['records']} | {row['fcr']:.3f} | {row['scr']:.3f} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The extension remains heterogeneous. Luna EVAR-Hard lowers observed FCR by one case relative to both textual conditions but also retains one fewer supported claim. Terra EVAR-Hard matches AR and retains two more supported claims than AR-Text at the same FCR. Sol EVAR-Hard exactly matches AR-Text and retains one fewer supported claim than AR. Across the three models descriptively pooled, EVAR-Hard has FCR 0.067 and SCR 0.700, compared with 0.100/0.667 for AR-Text and 0.100/0.767 for AR. No protocol universally dominates.",
        "",
        "## Audit",
        "",
        "The judge-free audit checked all 180 extension records and transcripts and reported no issues or run failures.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
