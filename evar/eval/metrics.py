from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evar.benchmark.schema import BenchmarkCase, GroundTruth
from evar.protocols.base import ProtocolResult
from evar.results import BenchmarkResultRecord


@dataclass(frozen=True)
class Metrics:
    true_positives: int
    false_positives: int
    actionable_count: int
    precision: float


@dataclass(frozen=True)
class AggregateMetrics:
    protocol: str
    total_cases: int
    completed_cases: int
    failed_runs: int
    supported_cases: int
    unsupported_cases: int
    supported_actionable: int
    unsupported_actionable: int
    fcr: float
    scr: float


@dataclass(frozen=True)
class EfficiencyMetrics:
    protocol: str
    total_cases: int
    measured_duration_cases: int
    total_duration_seconds: float
    mean_duration_seconds: float | None
    tokenized_cases: int
    total_input_tokens: int
    total_output_tokens: int
    mean_input_tokens: float | None
    mean_output_tokens: float | None


def compute_metrics(case: BenchmarkCase, result: ProtocolResult) -> Metrics:
    actionable_ids = [finding.id for finding in result.actionable_findings]
    true_positives = len(actionable_ids) if case.ground_truth == GroundTruth.SUPPORTED else 0
    false_positives = len(actionable_ids) if case.ground_truth == GroundTruth.UNSUPPORTED else 0
    actionable_count = len(actionable_ids)
    precision = true_positives / actionable_count if actionable_count else 0.0
    return Metrics(
        true_positives=true_positives,
        false_positives=false_positives,
        actionable_count=actionable_count,
        precision=precision,
    )


def compute_fcr_scr(records: list[dict[str, Any]]) -> AggregateMetrics:
    if not records:
        return AggregateMetrics(
            protocol="",
            total_cases=0,
            completed_cases=0,
            failed_runs=0,
            supported_cases=0,
            unsupported_cases=0,
            supported_actionable=0,
            unsupported_actionable=0,
            fcr=0.0,
            scr=0.0,
        )

    protocols = {str(record.get("protocol", "")) for record in records}
    protocol = protocols.pop() if len(protocols) == 1 else "mixed"

    completed = [record for record in records if record.get("run_status", "ok") == "ok"]
    supported = [record for record in completed if record.get("ground_truth") == GroundTruth.SUPPORTED.value]
    unsupported = [record for record in completed if record.get("ground_truth") == GroundTruth.UNSUPPORTED.value]
    supported_actionable = sum(1 for record in supported if _has_actionable_finding(record))
    unsupported_actionable = sum(1 for record in unsupported if _has_actionable_finding(record))

    return AggregateMetrics(
        protocol=protocol,
        total_cases=len(records),
        completed_cases=len(completed),
        failed_runs=len(records) - len(completed),
        supported_cases=len(supported),
        unsupported_cases=len(unsupported),
        supported_actionable=supported_actionable,
        unsupported_actionable=unsupported_actionable,
        fcr=unsupported_actionable / len(unsupported) if unsupported else 0.0,
        scr=supported_actionable / len(supported) if supported else 0.0,
    )


def compute_efficiency_metrics(records: list[dict[str, Any]]) -> EfficiencyMetrics:
    protocols = {str(record.get("protocol", "")) for record in records}
    protocol = protocols.pop() if len(protocols) == 1 else "mixed" if records else ""

    durations = [
        float(record["duration"])
        for record in records
        if isinstance(record.get("duration"), int | float)
        and not isinstance(record.get("duration"), bool)
    ]
    per_case_tokens = [_case_token_usage(record) for record in records]
    tokenized_cases = [usage for usage in per_case_tokens if usage is not None]
    total_input_tokens = sum(usage[0] for usage in tokenized_cases)
    total_output_tokens = sum(usage[1] for usage in tokenized_cases)

    return EfficiencyMetrics(
        protocol=protocol,
        total_cases=len(records),
        measured_duration_cases=len(durations),
        total_duration_seconds=sum(durations),
        mean_duration_seconds=sum(durations) / len(durations) if durations else None,
        tokenized_cases=len(tokenized_cases),
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        mean_input_tokens=total_input_tokens / len(tokenized_cases) if tokenized_cases else None,
        mean_output_tokens=total_output_tokens / len(tokenized_cases) if tokenized_cases else None,
    )


def _case_token_usage(record: dict[str, Any]) -> tuple[int, int] | None:
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return None
    input_tokens = 0
    output_tokens = 0
    observed = False
    for model_key in ("reviewer_model", "critic_model"):
        model = metadata.get(model_key)
        if not isinstance(model, dict):
            continue
        model_input = model.get("input_tokens")
        model_output = model.get("output_tokens")
        if isinstance(model_input, int) and not isinstance(model_input, bool):
            input_tokens += model_input
            observed = True
        if isinstance(model_output, int) and not isinstance(model_output, bool):
            output_tokens += model_output
            observed = True
    return (input_tokens, output_tokens) if observed else None


def _has_actionable_finding(record: dict[str, Any]) -> bool:
    if "final_actionable" in record:
        return bool(record["final_actionable"])
    actionable = record.get("actionable_findings", [])
    return isinstance(actionable, list) and len(actionable) > 0


def false_consensus_rate(results: list[BenchmarkResultRecord]) -> float:
    unsupported = [result for result in results if result.ground_truth == GroundTruth.UNSUPPORTED]
    if not unsupported:
        return 0.0
    accepted = [result for result in unsupported if result.final_actionable]
    return len(accepted) / len(unsupported)


def supported_claim_retention(results: list[BenchmarkResultRecord]) -> float:
    supported = [result for result in results if result.ground_truth == GroundTruth.SUPPORTED]
    if not supported:
        return 0.0
    accepted = [result for result in supported if result.final_actionable]
    return len(accepted) / len(supported)
