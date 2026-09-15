from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class GateReplayDecision:
    case_id: str
    model: str
    ground_truth: str
    critic_only: bool
    role_aware_soft: bool
    hard: bool
    verification_status: str
    evidence_role: str
    critic_decision: str


def replay_gate(record: dict[str, object]) -> GateReplayDecision:
    if record.get("run_status") != "ok":
        raise ValueError("gate replay requires a completed result row")
    if record.get("protocol") != "evar_hard":
        raise ValueError("gate replay requires an evar_hard result row")
    findings = record.get("findings")
    if not isinstance(findings, list) or len(findings) != 1 or not isinstance(findings[0], dict):
        raise ValueError("gate replay requires exactly one structured finding")
    finding = findings[0]
    receipt = finding.get("evidence_receipt")
    verification = finding.get("verification_result")
    if not isinstance(receipt, dict) or not isinstance(verification, dict):
        raise ValueError("gate replay requires a receipt and verification result")

    critic_decision = str(finding.get("critic_decision", ""))
    evidence_role = str(receipt.get("evidence_role", ""))
    verification_status = str(verification.get("status", ""))
    critic_only = critic_decision == "ACCEPT"
    role_aware_soft = critic_only and evidence_role == "supports_claim"
    hard = role_aware_soft and verification_status == "VERIFIED"

    metadata = record.get("metadata")
    model = "unknown"
    if isinstance(metadata, dict):
        model_config = metadata.get("model")
        if isinstance(model_config, dict):
            model = str(model_config.get("model", model))
    decision = GateReplayDecision(
        case_id=str(record.get("case_id", "")),
        model=model,
        ground_truth=str(record.get("ground_truth", "")),
        critic_only=critic_only,
        role_aware_soft=role_aware_soft,
        hard=hard,
        verification_status=verification_status,
        evidence_role=evidence_role,
        critic_decision=critic_decision,
    )
    if bool(record.get("final_actionable")) != decision.hard:
        raise ValueError(f"{decision.case_id}: recorded actionability violates the hard-gate replay")
    return decision


def summarize_gate_replay(records: Iterable[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[GateReplayDecision]] = defaultdict(list)
    failed_rows = 0
    for record in records:
        if record.get("run_status") != "ok":
            failed_rows += 1
            continue
        decision = replay_gate(record)
        grouped[decision.model].append(decision)

    models: dict[str, object] = {}
    for model, decisions in sorted(grouped.items()):
        models[model] = {
            "completed": len(decisions),
            "critic_only": _operating_point(decisions, "critic_only"),
            "role_aware_soft": _operating_point(decisions, "role_aware_soft"),
            "hard": _operating_point(decisions, "hard"),
            "gate_effect": {
                "soft_accept_to_hard_reject": sum(d.role_aware_soft and not d.hard for d in decisions),
                "hard_accept_without_soft_accept": sum(d.hard and not d.role_aware_soft for d in decisions),
            },
            "paired_tests": {
                label.lower(): _paired_test(
                    [decision for decision in decisions if decision.ground_truth == label]
                )
                for label in ("SUPPORTED", "UNSUPPORTED")
            },
        }
    return {
        "schema_version": 1,
        "design": (
            "Counterfactual replay of completed EVAR-Hard rows. Receipt, verifier output, "
            "and critic decision are held fixed; only the actionability rule changes."
        ),
        "failed_rows_excluded": failed_rows,
        "models": models,
    }


def exact_mcnemar_p_value(soft_only: int, hard_only: int) -> float:
    if soft_only < 0 or hard_only < 0:
        raise ValueError("discordant counts must be nonnegative")
    discordant = soft_only + hard_only
    if discordant == 0:
        return 1.0
    smaller = min(soft_only, hard_only)
    lower_tail = math.fsum(
        math.comb(discordant, value) * (0.5**discordant)
        for value in range(smaller + 1)
    )
    return min(1.0, 2 * lower_tail)


def _paired_test(decisions: list[GateReplayDecision]) -> dict[str, object]:
    soft_only = sum(decision.role_aware_soft and not decision.hard for decision in decisions)
    hard_only = sum(decision.hard and not decision.role_aware_soft for decision in decisions)
    return {
        "pairs": len(decisions),
        "soft_only": soft_only,
        "hard_only": hard_only,
        "exact_two_sided_mcnemar_p": exact_mcnemar_p_value(soft_only, hard_only),
    }


def _operating_point(
    decisions: list[GateReplayDecision],
    field: str,
) -> dict[str, object]:
    supported = [d for d in decisions if d.ground_truth == "SUPPORTED"]
    unsupported = [d for d in decisions if d.ground_truth == "UNSUPPORTED"]
    supported_actionable = sum(bool(getattr(d, field)) for d in supported)
    unsupported_actionable = sum(bool(getattr(d, field)) for d in unsupported)
    return {
        "supported_actionable": supported_actionable,
        "supported_total": len(supported),
        "scr": supported_actionable / len(supported) if supported else None,
        "unsupported_actionable": unsupported_actionable,
        "unsupported_total": len(unsupported),
        "fcr": unsupported_actionable / len(unsupported) if unsupported else None,
    }
