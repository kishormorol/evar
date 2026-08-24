from __future__ import annotations

from dataclasses import dataclass

from evar.benchmark.schema import BenchmarkCase, GroundTruth
from evar.protocols.base import ProtocolResult


@dataclass(frozen=True)
class Metrics:
    true_positives: int
    false_positives: int
    actionable_count: int
    precision: float


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
