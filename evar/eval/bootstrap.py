from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Literal

from evar.eval.metrics import compute_fcr_scr


MetricName = Literal["fcr", "scr"]


@dataclass(frozen=True)
class ConfidenceInterval:
    estimate: float
    low: float
    high: float


@dataclass(frozen=True)
class PairedDeltaInterval:
    metric: MetricName
    estimate: float
    low: float
    high: float


def bootstrap_rate_ci(
    records: list[dict[str, Any]],
    metric: MetricName,
    *,
    n: int = 10000,
    seed: int = 7,
    alpha: float = 0.05,
) -> ConfidenceInterval:
    _validate_bootstrap_args(metric, n, alpha)
    eligible = _eligible_records(records, metric)
    estimate = _metric_value(records, metric)
    if not eligible:
        return ConfidenceInterval(estimate=estimate, low=0.0, high=0.0)

    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        resample = [rng.choice(eligible) for _ in eligible]
        samples.append(_metric_value(resample, metric))
    return ConfidenceInterval(
        estimate=estimate,
        low=_quantile(samples, alpha / 2),
        high=_quantile(samples, 1 - alpha / 2),
    )


def paired_delta(
    records_a: list[dict[str, Any]],
    records_b: list[dict[str, Any]],
    metric: MetricName,
) -> float:
    _validate_metric(metric)
    pairs = _paired_records(records_a, records_b, metric)
    if not pairs:
        return 0.0
    a_records = [pair[0] for pair in pairs]
    b_records = [pair[1] for pair in pairs]
    return _metric_value(b_records, metric) - _metric_value(a_records, metric)


def bootstrap_paired_delta_ci(
    records_a: list[dict[str, Any]],
    records_b: list[dict[str, Any]],
    metric: MetricName,
    *,
    n: int = 10000,
    seed: int = 7,
    alpha: float = 0.05,
) -> PairedDeltaInterval:
    _validate_bootstrap_args(metric, n, alpha)
    pairs = _paired_records(records_a, records_b, metric)
    estimate = paired_delta(records_a, records_b, metric)
    if not pairs:
        return PairedDeltaInterval(metric=metric, estimate=estimate, low=0.0, high=0.0)

    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        resample = [rng.choice(pairs) for _ in pairs]
        a_records = [pair[0] for pair in resample]
        b_records = [pair[1] for pair in resample]
        samples.append(_metric_value(b_records, metric) - _metric_value(a_records, metric))
    return PairedDeltaInterval(
        metric=metric,
        estimate=estimate,
        low=_quantile(samples, alpha / 2),
        high=_quantile(samples, 1 - alpha / 2),
    )


def _eligible_records(records: list[dict[str, Any]], metric: MetricName) -> list[dict[str, Any]]:
    truth = "UNSUPPORTED" if metric == "fcr" else "SUPPORTED"
    return [
        record
        for record in records
        if record.get("run_status", "ok") == "ok" and record.get("ground_truth") == truth
    ]


def _paired_records(
    records_a: list[dict[str, Any]],
    records_b: list[dict[str, Any]],
    metric: MetricName,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    truth = "UNSUPPORTED" if metric == "fcr" else "SUPPORTED"
    by_id_a = {
        str(record.get("case_id")): record
        for record in records_a
        if record.get("run_status", "ok") == "ok" and record.get("ground_truth") == truth
    }
    by_id_b = {
        str(record.get("case_id")): record
        for record in records_b
        if record.get("run_status", "ok") == "ok" and record.get("ground_truth") == truth
    }
    return [(by_id_a[case_id], by_id_b[case_id]) for case_id in sorted(by_id_a.keys() & by_id_b.keys())]


def _metric_value(records: list[dict[str, Any]], metric: MetricName) -> float:
    summary = compute_fcr_scr(records)
    return summary.fcr if metric == "fcr" else summary.scr


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = q * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _validate_bootstrap_args(metric: MetricName, n: int, alpha: float) -> None:
    _validate_metric(metric)
    if n < 1:
        raise ValueError("n must be positive")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")


def _validate_metric(metric: MetricName) -> None:
    if metric not in ("fcr", "scr"):
        raise ValueError("metric must be 'fcr' or 'scr'")
