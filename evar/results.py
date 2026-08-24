from __future__ import annotations

from dataclasses import dataclass, field

from evar.benchmark.schema import GroundTruth
from evar.protocols.evar import CriticDecision, ProtocolResult


@dataclass(frozen=True)
class BenchmarkResultRecord:
    case_id: str
    protocol: str
    ground_truth: GroundTruth
    final_actionable: bool
    verification_status: str | None
    critic_decision: CriticDecision | None
    transcript_path: str | None
    duration: float
    metadata: dict[str, object] = field(default_factory=dict)


def result_record_from_protocol_result(
    *,
    case_id: str,
    ground_truth: GroundTruth,
    result: ProtocolResult,
    transcript_path: str | None = None,
    duration: float = 0.0,
    metadata: dict[str, object] | None = None,
) -> BenchmarkResultRecord:
    first = result.findings[0] if result.findings else None
    return BenchmarkResultRecord(
        case_id=case_id,
        protocol=str(result.metadata.get("protocol", "")),
        ground_truth=ground_truth,
        final_actionable=bool(result.accepted_findings),
        verification_status=first.verification_result.status.value if first else None,
        critic_decision=first.critic_decision if first else None,
        transcript_path=transcript_path,
        duration=duration,
        metadata=dict(metadata or {}),
    )
