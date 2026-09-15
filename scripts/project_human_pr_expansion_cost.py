from __future__ import annotations

import argparse
import json
from pathlib import Path


DISPLAY_TO_SLUG = {
    "gpt-4.1": "gpt-4.1",
    "Claude Sonnet 5": "anthropic/claude-sonnet-5",
    "Gemini 3.1 Pro Preview": "google/gemini-3.1-pro-preview",
    "DeepSeek V4 Pro": "deepseek/deepseek-v4-pro-0813",
    "Kimi K3": "moonshotai/kimi-k3",
    "Qwen3.8 Max": "qwen/qwen3.8-max",
}


def historical_rates(report_paths: list[Path]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for path in report_paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for row in report.get("overall", []):
            display = str(row["model"])
            slug = DISPLAY_TO_SLUG.get(display)
            if slug is None:
                continue
            total = totals.setdefault(slug, {"attempts": 0.0, "cost": 0.0})
            total["attempts"] += float(row["total_cases"])
            total["cost"] += float(row["estimated_api_cost_usd"])
    return {
        slug: {
            "historical_attempts": values["attempts"],
            "historical_cost_usd": values["cost"],
            "estimated_cost_per_attempt_usd": values["cost"] / values["attempts"],
        }
        for slug, values in totals.items()
        if values["attempts"]
    }


def build_projection(
    rates: dict[str, dict[str, float]],
    *,
    cases: int = 600,
    protocols: int = 4,
    stability_cases: int = 120,
    additional_stability_repetitions: int = 2,
    contingency: float = 0.25,
) -> dict[str, object]:
    full_attempts = cases * protocols
    stability_attempts = stability_cases * protocols * additional_stability_repetitions
    per_model: list[dict[str, object]] = []
    for model, rate in sorted(rates.items()):
        projected = (full_attempts + stability_attempts) * rate["estimated_cost_per_attempt_usd"]
        per_model.append(
            {
                "model": model,
                **rate,
                "full_matrix_attempts": full_attempts,
                "additional_stability_attempts": stability_attempts,
                "projected_cost_usd": projected,
                "projected_cost_with_contingency_usd": projected * (1 + contingency),
            }
        )
    subtotal = sum(float(row["projected_cost_usd"]) for row in per_model)
    return {
        "schema_version": 1,
        "basis": (
            "Projection scales observed per-attempt token cost from frozen Human PR 20 runs. "
            "EVAR-BlindGate is assumed to cost approximately one ordinary two-call protocol arm."
        ),
        "cases": cases,
        "protocols": protocols,
        "stability_cases": stability_cases,
        "additional_stability_repetitions": additional_stability_repetitions,
        "full_matrix_attempts_per_model": full_attempts,
        "additional_stability_attempts_per_model": stability_attempts,
        "total_attempts": (full_attempts + stability_attempts) * len(per_model),
        "contingency_fraction": contingency,
        "per_model": per_model,
        "projected_subtotal_usd": subtotal,
        "projected_upper_bound_usd": subtotal * (1 + contingency),
        "authorization": "projection_only_not_authorization_to_run",
    }


def render_markdown(projection: dict[str, object]) -> str:
    lines = [
        "# Human PR expansion cost and execution plan",
        "",
        str(projection["basis"]),
        "",
        "| Model | Historical cost/attempt | Full attempts | Stability attempts | Projected | With contingency |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in projection["per_model"]:
        lines.append(
            f"| {row['model']} | ${row['estimated_cost_per_attempt_usd']:.4f} | "
            f"{row['full_matrix_attempts']} | {row['additional_stability_attempts']} | "
            f"${row['projected_cost_usd']:.2f} | "
            f"${row['projected_cost_with_contingency_usd']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"The complete plan contains **{projection['total_attempts']:,} protocol attempts**. "
            f"The empirical projection is **${projection['projected_subtotal_usd']:.2f}**, or "
            f"**${projection['projected_upper_bound_usd']:.2f}** with the frozen "
            f"{projection['contingency_fraction']:.0%} contingency.",
            "",
            "This is a planning estimate, not authorization to spend. Before execution, refresh exact model prices, run dry-run and benchmark preflight, verify available credit against the upper bound, and freeze the new price table. If the budget is smaller, revise the protocol prospectively before inspecting any powered model outcome; do not silently drop models or repetitions after results are visible.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Project powered Human PR model-run cost.")
    parser.add_argument(
        "--report",
        type=Path,
        action="append",
        default=[
            Path("benchmarks/human_pr_20/report.json"),
            Path("benchmarks/human_pr_20/cross_provider_report.json"),
        ],
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("benchmarks/human_pr_200/cost_projection.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("benchmarks/human_pr_200/COST_AND_EXECUTION_PLAN.md"),
    )
    args = parser.parse_args(argv)
    projection = build_projection(historical_rates(args.report))
    args.json.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(projection), encoding="utf-8")
    print(args.json)
    print(args.markdown)


if __name__ == "__main__":
    main()
