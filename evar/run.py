from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from evar.agents.critic import DummyCritic
from evar.agents.model_critic import ModelCritic
from evar.agents.model_reviewer import ModelAgentConfig, ModelOutputError, ModelReviewer
from evar.agents.reviewer import DummyReviewer
from evar.benchmark.loader import BenchmarkValidationError, load_jsonl_cases
from evar.benchmark.schema import BenchmarkCase
from evar.config import PilotConfig, load_config
from evar.eval.metrics import compute_metrics
from evar.model_backend import DryRunBackend, ModelBackend, OpenAIResponsesBackend
from evar.protocols.ar import ARProtocol
from evar.protocols.ar_text import ARTextProtocol
from evar.protocols.base import AgentConfig, ProtocolBudget, BaseProtocol
from evar.protocols.evar import EVARHardProtocol
from evar.protocols.registry import create_protocol
from evar.verifier.verify import DeterministicVerifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run EVAR protocols over benchmark JSONL cases.")
    parser.add_argument("--protocol", required=True, choices=["ar", "ar_text", "evar", "evar_hard"])
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args(argv)

    try:
        cases = load_jsonl_cases(args.cases)
    except (OSError, BenchmarkValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.config is not None:
        try:
            config = load_config(args.config)
            return _run_configured(args.protocol, cases, config, args.output_dir, dry_run=args.dry_run)
        except (OSError, ValueError, RuntimeError) as exc:
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
    if protocol in ("evar", "evar_hard"):
        return EVARHardProtocol(reviewer, critic, config, budget)
    raise ValueError(f"Unsupported protocol: {protocol}")


def _run_configured(
    protocol_name: str,
    cases: list[BenchmarkCase],
    config: PilotConfig,
    output_dir: Path,
    *,
    dry_run: bool,
) -> int:
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    backend = _build_backend(config, dry_run=dry_run)
    normalized_protocol = "evar_hard" if protocol_name == "evar" else protocol_name
    agent_config = ModelAgentConfig(
        model_name=config.model.model,
        temperature=config.model.temperature,
        seed=config.experiment.seed,
        max_output_tokens=config.model.max_output_tokens,
    )
    reviewer = ModelReviewer(
        backend,
        agent_config,
        protocol=normalized_protocol,
        prompt_filename_override=config.protocol.reviewer_prompt,
        parse_retries=config.protocol.reviewer_parse_retries,
    )
    critic = ModelCritic(backend, agent_config, protocol=normalized_protocol)
    protocol = create_protocol(
        normalized_protocol,
        reviewer,
        critic,
        verifier=DeterministicVerifier(
            timeout_seconds=config.protocol.verifier_timeout_seconds
        ),
        metadata={
            "run_id": run_id,
            "critic_rounds": config.protocol.critic_rounds,
            "seed": config.experiment.seed,
        },
    )

    if dry_run:
        for case in cases:
            task = _claim_evaluation_task(case)
            try:
                protocol.run(task, case.repo_path)
            except ModelOutputError:
                pass
        _print_dry_run_prompts(backend)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_id}_{normalized_protocol}.jsonl"
    transcript_dir = output_dir / "transcripts" / run_id
    transcript_dir.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing results file: {output_path}")

    with output_path.open("w", encoding="utf-8") as handle:
        for case in cases:
            task = _claim_evaluation_task(case)
            started = time.perf_counter()
            try:
                result = protocol.run(task, case.repo_path)
                duration = time.perf_counter() - started
                transcript_path = _write_configured_transcript(
                    transcript_dir,
                    case,
                    normalized_protocol,
                    run_id,
                    result,
                )
                record = _configured_result_record(
                    case,
                    result,
                    normalized_protocol,
                    run_id,
                    duration,
                    reviewer,
                    critic,
                    config,
                    transcript_path,
                )
            except Exception as exc:
                duration = time.perf_counter() - started
                transcript_path = _write_failure_transcript(
                    transcript_dir,
                    case,
                    normalized_protocol,
                    run_id,
                    exc,
                    reviewer,
                    critic,
                )
                record = _configured_failure_record(
                    case,
                    normalized_protocol,
                    run_id,
                    duration,
                    exc,
                    reviewer,
                    critic,
                    config,
                    transcript_path,
                )
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(str(output_path))
    return 0


def _build_backend(config: PilotConfig, *, dry_run: bool) -> ModelBackend:
    if dry_run or config.model.backend == "dry_run":
        return DryRunBackend(model_name=config.model.model)
    if config.model.backend == "openai":
        return OpenAIResponsesBackend(
            model_name=config.model.model,
            temperature=config.model.temperature,
            max_output_tokens=config.model.max_output_tokens,
            reasoning_effort=config.model.reasoning_effort,
        )
    raise ValueError(f"Unsupported model backend: {config.model.backend}")


def _claim_evaluation_task(case: BenchmarkCase) -> str:
    return (
        f"Task description:\n{case.task_description}\n\n"
        f"Candidate claim:\n{case.claim}\n\n"
        f"Claim family:\n{case.claim_family.value}\n"
    )


def _configured_result_record(
    case: BenchmarkCase,
    result: object,
    protocol: str,
    run_id: str,
    duration: float,
    reviewer: ModelReviewer,
    critic: ModelCritic,
    config: PilotConfig,
    transcript_path: Path,
) -> dict[str, object]:
    first = result.findings[0] if result.findings else None
    return {
        "case_id": case.case_id,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "claim_family": case.claim_family.value,
        "ground_truth": case.ground_truth.value,
        "final_actionable": bool(result.accepted_findings),
        "finding_count": len(result.findings),
        "accepted_finding_count": len(result.accepted_findings),
        "findings": _json_safe(result.findings),
        "verification_status": first.verification_result.status.value if first else None,
        "critic_decision": first.critic_decision.value if first else None,
        "transcript_path": str(transcript_path),
        "duration": duration,
        "metadata": {
            "model": _json_safe(config.model),
            "protocol": _json_safe(config.protocol),
            "experiment": _json_safe(config.experiment),
            "reviewer_prompt": {
                "filename": reviewer.prompt_template.filename,
                "sha256": reviewer.prompt_template.sha256,
            },
            "critic_prompt": {
                "filename": critic.prompt_template.filename,
                "sha256": critic.prompt_template.sha256,
            },
            "reviewer_model": _response_summary(reviewer.last_responses),
            "critic_model": _response_summary(critic.responses[-1:]),
        },
        "run_status": "ok",
    }


def _configured_failure_record(
    case: BenchmarkCase,
    protocol: str,
    run_id: str,
    duration: float,
    exc: Exception,
    reviewer: ModelReviewer,
    critic: ModelCritic,
    config: PilotConfig,
    transcript_path: Path,
) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "claim_family": case.claim_family.value,
        "ground_truth": case.ground_truth.value,
        "final_actionable": False,
        "verification_status": None,
        "critic_decision": None,
        "transcript_path": str(transcript_path),
        "duration": duration,
        "metadata": {
            "model": _json_safe(config.model),
            "reviewer_prompt": {
                "filename": reviewer.prompt_template.filename,
                "sha256": reviewer.prompt_template.sha256,
            },
            "critic_prompt": {
                "filename": critic.prompt_template.filename,
                "sha256": critic.prompt_template.sha256,
            },
            "reviewer_model": _response_summary(reviewer.last_responses),
            "critic_model": _response_summary(critic.responses[-1:]),
        },
        "run_status": "failed",
        "failure": {"type": type(exc).__name__, "reason": str(exc)},
    }


def _write_configured_transcript(
    transcript_dir: Path,
    case: BenchmarkCase,
    protocol: str,
    run_id: str,
    result: object,
) -> Path:
    transcript_path = transcript_dir / f"{case.case_id}.json"
    payload = {
        "case_id": case.case_id,
        "run_id": run_id,
        "protocol": protocol,
        "repo_path": str(case.repo_path),
        "task_description": case.task_description,
        "claim": case.claim,
        "claim_family": case.claim_family.value,
        "ground_truth": case.ground_truth.value,
        "ground_truth_evidence": case.ground_truth_evidence,
        "findings": _json_safe(getattr(result, "findings", [])),
        "accepted_findings": _json_safe(getattr(result, "accepted_findings", [])),
        "rejected_findings": _json_safe(getattr(result, "rejected_findings", [])),
        "transcript": _json_safe(getattr(result, "transcript", [])),
        "metadata": _json_safe(getattr(result, "metadata", {})),
    }
    transcript_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return transcript_path


def _write_failure_transcript(
    transcript_dir: Path,
    case: BenchmarkCase,
    protocol: str,
    run_id: str,
    exc: Exception,
    reviewer: ModelReviewer,
    critic: ModelCritic,
) -> Path:
    transcript_path = transcript_dir / f"{case.case_id}.json"
    payload = {
        "case_id": case.case_id,
        "run_id": run_id,
        "protocol": protocol,
        "repo_path": str(case.repo_path),
        "task_description": case.task_description,
        "claim": case.claim,
        "claim_family": case.claim_family.value,
        "ground_truth": case.ground_truth.value,
        "ground_truth_evidence": case.ground_truth_evidence,
        "reviewer_model": _response_summary(reviewer.responses[-1:]),
        "critic_model": _response_summary(critic.responses[-1:]),
        "failure": {"type": type(exc).__name__, "reason": str(exc)},
    }
    transcript_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return transcript_path


def _response_summary(responses: list[object]) -> dict[str, object] | None:
    if not responses:
        return None
    response = responses[-1]
    input_tokens = [item.input_tokens for item in responses if item.input_tokens is not None]
    output_tokens = [item.output_tokens for item in responses if item.output_tokens is not None]
    return {
        "text": response.text,
        "parsed_output": _json_safe(response.parsed_output),
        "model_name": response.model_name,
        "input_tokens": sum(input_tokens) if input_tokens else None,
        "output_tokens": sum(output_tokens) if output_tokens else None,
        "latency_seconds": sum(item.latency_seconds for item in responses),
        "attempt_count": len(responses),
    }


def _print_dry_run_prompts(backend: ModelBackend) -> None:
    calls = getattr(backend, "calls", [])
    for index, call in enumerate(calls, start=1):
        print(f"--- PROMPT {index} SYSTEM ---")
        print(call.system_prompt)
        print(f"--- PROMPT {index} USER ---")
        print(call.user_prompt)
        print(f"--- PROMPT {index} RESPONSE_SCHEMA ---")
        print(json.dumps(call.response_schema, sort_keys=True))


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
