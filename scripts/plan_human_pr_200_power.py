from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def pilot_discordance(index_path: Path) -> list[dict[str, object]]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    cells: dict[tuple[str, str], dict[str, dict[str, object]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for item in index["canonical_runs"]:
        protocol = str(item["protocol"])
        if protocol not in {"ar_text", "evar_hard"}:
            continue
        for row in _load_jsonl(Path(str(item["result"]))):
            if row.get("run_status") != "ok":
                continue
            cells[(str(item["model"]), str(row["ground_truth"]))][protocol][str(row["case_id"])] = row

    summary: list[dict[str, object]] = []
    for (model, label), protocols in sorted(cells.items()):
        ar_text = protocols.get("ar_text", {})
        evar_hard = protocols.get("evar_hard", {})
        paired = sorted(set(ar_text) & set(evar_hard))
        discordant = sum(
            bool(ar_text[case_id]["final_actionable"]) != bool(evar_hard[case_id]["final_actionable"])
            for case_id in paired
        )
        summary.append(
            {
                "model": model,
                "label": label,
                "pairs": len(paired),
                "discordant": discordant,
                "discordance_rate": discordant / len(paired) if paired else 0.0,
                "wilson_upper_95": wilson_upper(discordant, len(paired)),
            }
        )
    return summary


def wilson_upper(successes: int, total: int, confidence: float = 0.95) -> float:
    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must be between zero and total")
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = proportion + z * z / (2 * total)
    radius = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
    return min(1.0, (centre + radius) / denominator)


def _binomial_pmf(k: int, n: int, probability: float) -> float:
    if k < 0 or k > n:
        return 0.0
    if probability == 0.0:
        return 1.0 if k == 0 else 0.0
    if probability == 1.0:
        return 1.0 if k == n else 0.0
    log_probability = (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * math.log(probability)
        + (n - k) * math.log1p(-probability)
    )
    return math.exp(log_probability)


def _binomial_cdf(k: int, n: int, probability: float) -> float:
    return min(1.0, math.fsum(_binomial_pmf(value, n, probability) for value in range(k + 1)))


def exact_mcnemar_power(
    pairs: int,
    discordance_rate: float,
    absolute_difference: float,
    alpha: float = 0.05,
) -> float:
    """Unconditional power of the exact two-sided McNemar test.

    ``absolute_difference`` is |p10 - p01| and ``discordance_rate`` is p10 + p01.
    The calculation averages the conditional exact test over the number of discordant
    pairs rather than treating that number as fixed.
    """
    if pairs < 1:
        raise ValueError("pairs must be positive")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    if not 0 <= absolute_difference <= discordance_rate <= 1:
        raise ValueError("require 0 <= absolute_difference <= discordance_rate <= 1")
    if discordance_rate == 0:
        return 0.0

    directional_probability = (discordance_rate + absolute_difference) / (2 * discordance_rate)
    power = 0.0
    for discordant_pairs in range(1, pairs + 1):
        lower = -1
        for candidate in range(discordant_pairs // 2 + 1):
            null_tail = 2 * _binomial_cdf(candidate, discordant_pairs, 0.5)
            if null_tail <= alpha:
                lower = candidate
        if lower < 0:
            continue
        upper = discordant_pairs - lower
        reject_probability = _binomial_cdf(lower, discordant_pairs, directional_probability)
        reject_probability += 1 - _binomial_cdf(upper - 1, discordant_pairs, directional_probability)
        power += _binomial_pmf(discordant_pairs, pairs, discordance_rate) * reject_probability
    return min(1.0, max(0.0, power))


def build_plan(
    index_path: Path,
    *,
    absolute_difference: float,
    alpha: float,
    sample_sizes: list[int],
) -> dict[str, object]:
    pilot = pilot_discordance(index_path)
    planning_rates: dict[str, float] = {}
    for label in ("SUPPORTED", "UNSUPPORTED"):
        candidates = [float(row["wilson_upper_95"]) for row in pilot if row["label"] == label]
        if not candidates:
            raise ValueError(f"pilot contains no paired {label} observations")
        planning_rates[label] = max(candidates)
    power = [
        {
            "pairs_per_label": pairs,
            **{
                label.lower(): exact_mcnemar_power(pairs, rate, absolute_difference, alpha)
                for label, rate in planning_rates.items()
            },
        }
        for pairs in sample_sizes
    ]
    return {
        "schema_version": 1,
        "pilot_index": index_path.as_posix(),
        "comparison": "AR-Text versus EVAR-Hard",
        "test": "exact two-sided McNemar",
        "alpha": alpha,
        "absolute_paired_difference": absolute_difference,
        "discordance_planning_rule": "maximum model-specific 95% Wilson upper bound by label",
        "pilot": pilot,
        "planning_discordance_rate": planning_rates,
        "power": power,
    }


def render_markdown(plan: dict[str, object]) -> str:
    lines = [
        "# Human PR 200 paired-power plan",
        "",
        "This prospective calculation uses only the frozen Human PR 20 outcomes. It does not inspect Human PR 200 labels or model results. The primary comparison is AR-Text versus EVAR-Hard, tested separately within supported and unsupported temporal cases with an exact two-sided McNemar test.",
        "",
        f"The smallest effect of practical interest is an absolute paired rate difference of {plan['absolute_paired_difference']:.2f}, with alpha = {plan['alpha']:.3f}. To avoid treating ten-case pilot discordance as precise, the planning rate for each label is the largest model-specific 95% Wilson upper bound.",
        "",
        "## Frozen pilot inputs",
        "",
        "| Model | Label | Discordant / pairs | Rate | 95% Wilson upper |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in plan["pilot"]:
        lines.append(
            f"| {row['model']} | {row['label']} | {row['discordant']} / {row['pairs']} | "
            f"{row['discordance_rate']:.3f} | {row['wilson_upper_95']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Prospective power curve",
            "",
            "| Independent source comments (pairs per label) | Supported-case power | Unsupported-case power |",
            "| ---: | ---: | ---: |",
        ]
    )
    for row in plan["power"]:
        lines.append(
            f"| {row['pairs_per_label']} | {row['supported']:.3f} | {row['unsupported']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The final acquisition target must be chosen before model calls. If no feasible row reaches the desired power for both labels, the study must either acquire more independently adjudicated comments or explicitly present the corresponding endpoint as estimation rather than a powered superiority test. Repeated model calls reduce Monte Carlo uncertainty but do not increase the number of independent source comments.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan exact paired power for Human PR 200.")
    parser.add_argument("--index", type=Path, default=Path("benchmarks/human_pr_20/run_index.json"))
    parser.add_argument("--absolute-difference", type=float, default=0.15)
    parser.add_argument("--alpha", type=float, default=0.025)
    parser.add_argument("--sample-sizes", default="100,150,200,250,300,350,400,500")
    parser.add_argument("--json", type=Path, default=Path("benchmarks/human_pr_200/power_plan.json"))
    parser.add_argument("--markdown", type=Path, default=Path("benchmarks/human_pr_200/POWER_PLAN.md"))
    args = parser.parse_args(argv)
    sample_sizes = sorted({int(value) for value in args.sample_sizes.split(",") if value.strip()})
    if not sample_sizes or sample_sizes[0] < 1:
        raise ValueError("sample sizes must be positive")
    plan = build_plan(
        args.index,
        absolute_difference=args.absolute_difference,
        alpha=args.alpha,
        sample_sizes=sample_sizes,
    )
    args.json.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(plan), encoding="utf-8")
    print(args.json)
    print(args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
