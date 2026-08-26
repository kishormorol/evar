from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from evar.benchmark.loader import BenchmarkValidationError, load_jsonl_cases
from evar.benchmark.schema import BenchmarkCase
from evar.config import PilotConfig, load_config
from evar.prompts import load_prompt, prompt_filename
from evar.run import _claim_evaluation_task


PROTOCOLS = ("ar", "ar_text", "evar_hard")
PROMPT_ROLES = ("reviewer", "critic")


@dataclass(frozen=True)
class PreflightIssue:
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class PreflightReport:
    cases: int
    issues: list[PreflightIssue]
    prompt_hashes: dict[str, str]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def run_preflight(config_path: Path, cases_path: Path) -> PreflightReport:
    issues: list[PreflightIssue] = []
    prompt_hashes: dict[str, str] = {}

    config = _load_config(config_path, issues)
    cases = _load_cases(cases_path, issues)
    if config is not None:
        _check_config(config, issues)
    _check_prompts(prompt_hashes, issues)
    for case in cases:
        _check_case(case, issues)

    return PreflightReport(cases=len(cases), issues=issues, prompt_hashes=prompt_hashes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preflight-check EVAR experiment inputs without model calls.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    args = parser.parse_args(argv)

    report = run_preflight(args.config, args.cases)
    _print_report(report)
    return 0 if report.ok else 2


def _load_config(path: Path, issues: list[PreflightIssue]) -> PilotConfig | None:
    try:
        return load_config(path)
    except (OSError, KeyError, ValueError) as exc:
        issues.append(PreflightIssue("error", "CONFIG_INVALID", f"{path}: {exc}"))
        return None


def _load_cases(path: Path, issues: list[PreflightIssue]) -> list[BenchmarkCase]:
    try:
        return load_jsonl_cases(path)
    except (OSError, BenchmarkValidationError) as exc:
        issues.append(PreflightIssue("error", "CASES_INVALID", f"{path}: {exc}"))
        return []


def _check_config(config: PilotConfig, issues: list[PreflightIssue]) -> None:
    if config.protocol.critic_rounds != 1:
        issues.append(
            PreflightIssue(
                "error",
                "CRITIC_ROUNDS_UNSUPPORTED",
                "Initial pilot requires protocol.critic_rounds == 1.",
            )
        )
    if config.protocol.verifier_timeout_seconds <= 0:
        issues.append(
            PreflightIssue("error", "BAD_VERIFIER_TIMEOUT", "verifier_timeout_seconds must be positive.")
        )
    if config.experiment.repetitions != 1:
        issues.append(
            PreflightIssue("error", "REPETITIONS_UNSUPPORTED", "Initial pilot requires experiment.repetitions == 1.")
        )
    if config.model.temperature != 0.0:
        issues.append(
            PreflightIssue("warning", "NONZERO_TEMPERATURE", "Pilot config uses nonzero temperature.")
        )
    if config.model.backend not in {"dry_run", "openai"}:
        issues.append(
            PreflightIssue("error", "UNKNOWN_BACKEND", f"Unsupported backend: {config.model.backend}")
        )


def _check_prompts(prompt_hashes: dict[str, str], issues: list[PreflightIssue]) -> None:
    for protocol in PROTOCOLS:
        for role in PROMPT_ROLES:
            filename = prompt_filename(role, protocol)
            try:
                prompt = load_prompt(filename)
            except OSError as exc:
                issues.append(PreflightIssue("error", "PROMPT_MISSING", f"{filename}: {exc}"))
                continue
            prompt_hashes[filename] = prompt.sha256
            lowered = prompt.text.lower()
            if "ground truth" not in lowered and "ground_truth" not in lowered:
                issues.append(
                    PreflightIssue(
                        "warning",
                        "PROMPT_NO_LEAKAGE_REMINDER",
                        f"{filename} does not explicitly mention ground-truth exclusion.",
                    )
                )


def _check_case(case: BenchmarkCase, issues: list[PreflightIssue]) -> None:
    repo_path = case.repo_path
    if not repo_path.exists():
        issues.append(
            PreflightIssue("error", "REPO_MISSING", f"{case.case_id}: repo_path does not exist: {repo_path}")
        )
    if not case.validation_command:
        issues.append(
            PreflightIssue("error", "VALIDATION_COMMAND_MISSING", f"{case.case_id}: validation_command is empty.")
        )
    task = _claim_evaluation_task(case)
    forbidden = {
        "ground_truth": "ground_truth field name",
        case.ground_truth.value: "ground_truth label",
        case.ground_truth_evidence: "ground_truth_evidence",
    }
    for value, label in forbidden.items():
        if value and value in task:
            issues.append(
                PreflightIssue("error", "PROMPT_LEAKAGE", f"{case.case_id}: task leaks {label}.")
            )


def _print_report(report: PreflightReport) -> None:
    print(f"cases: {report.cases}")
    print(f"status: {'OK' if report.ok else 'FAILED'}")
    print("prompt_hashes:")
    for filename in sorted(report.prompt_hashes):
        print(f"  {filename}: {report.prompt_hashes[filename]}")
    if report.issues:
        print("issues:")
        for issue in report.issues:
            print(f"  {issue.severity.upper()} {issue.code}: {issue.message}")
    else:
        print("issues: none")


if __name__ == "__main__":
    raise SystemExit(main())
