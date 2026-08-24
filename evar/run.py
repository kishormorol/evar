from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from evar.agents.critic import DummyCritic
from evar.agents.reviewer import DummyReviewer
from evar.benchmark.loader import BenchmarkValidationError, load_jsonl_cases
from evar.benchmark.schema import BenchmarkCase
from evar.eval.metrics import compute_metrics
from evar.protocols.ar import ARProtocol
from evar.protocols.ar_text import ARTextProtocol
from evar.protocols.base import AgentConfig, ProtocolBudget, BaseProtocol
from evar.protocols.evar import EVARHardProtocol


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run EVAR protocols over benchmark JSONL cases.")
    parser.add_argument("--protocol", required=True, choices=["ar", "ar_text", "evar"])
    parser.add_argument("--cases", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        cases = load_jsonl_cases(args.cases)
    except (OSError, BenchmarkValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    config = AgentConfig(model_name="dummy-model", temperature=0.0, seed=7)
    budget = ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1)
    reviewer = DummyReviewer()
    critic = DummyCritic()

    for case in cases:
        protocol = _build_protocol(args.protocol, reviewer, critic, config, budget)
        try:
            result = protocol.run(case.to_task_case())
            record = _result_record(case, result)
        except Exception as exc:
            record = _failure_record(case, args.protocol, config, budget, exc)
        print(json.dumps(record, sort_keys=True))
    return 0


def _build_protocol(
    protocol: str,
    reviewer: DummyReviewer,
    critic: DummyCritic,
    config: AgentConfig,
    budget: ProtocolBudget,
) -> BaseProtocol:
    if protocol == "ar":
        return ARProtocol(reviewer, critic, config, budget)
    if protocol == "ar_text":
        return ARTextProtocol(reviewer, critic, config, budget)
    if protocol == "evar":
        return EVARHardProtocol(reviewer, critic, config, budget)
    raise ValueError(f"Unsupported protocol: {protocol}")


def _result_record(case: BenchmarkCase, result: object) -> dict[str, object]:
    metrics = compute_metrics(case, result)
    return {
        "case_id": case.case_id,
        "protocol": result.protocol_name,
        "repo_path": str(case.repo_path),
        "task_description": case.task_description,
        "claim": case.claim,
        "claim_family": case.claim_family.value,
        "ground_truth": case.ground_truth.value,
        "ground_truth_evidence": case.ground_truth_evidence,
        "validation_command": list(case.validation_command),
        "findings": _json_safe(result.findings),
        "actionable_findings": _json_safe(result.actionable_findings),
        "verification_results": _json_safe(result.verification_results),
        "interaction_log": _json_safe(result.interaction_log),
        "metrics": _json_safe(metrics),
        "budget": _json_safe(result.budget),
        "model_config": _json_safe(result.config),
        "run_status": "ok",
    }


def _failure_record(
    case: BenchmarkCase,
    protocol: str,
    config: AgentConfig,
    budget: ProtocolBudget,
    exc: Exception,
) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "protocol": protocol,
        "repo_path": str(case.repo_path),
        "task_description": case.task_description,
        "claim": case.claim,
        "claim_family": case.claim_family.value,
        "ground_truth": case.ground_truth.value,
        "ground_truth_evidence": case.ground_truth_evidence,
        "validation_command": list(case.validation_command),
        "findings": [],
        "actionable_findings": [],
        "verification_results": {},
        "interaction_log": [],
        "metrics": None,
        "budget": _json_safe(budget),
        "model_config": _json_safe(config),
        "run_status": "failed",
        "failure": {
            "type": type(exc).__name__,
            "reason": str(exc),
        },
    }


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
