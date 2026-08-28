from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
REPOS = ROOT / "repos"
CASES = ROOT / "cases.jsonl"


def main() -> None:
    REPOS.mkdir(parents=True, exist_ok=True)
    rows = [
        _case(
            1,
            files=["evar/model_backend.py"],
            task="Review OpenAI backend API-key handling.",
            claim="OpenAIResponsesBackend raises RuntimeError when no API key is available.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="model_backend.py raises RuntimeError if self.api_key is falsy.",
            claim_family="missing_guard",
        ),
        _case(
            2,
            files=["evar/model_backend.py"],
            task="Review dry-run backend network behavior.",
            claim="DryRunBackend calls the OpenAI Responses API.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="DryRunBackend.generate returns local canned JSON and never uses urllib.",
            claim_family="incorrect_call_relationship",
        ),
        _case(
            3,
            files=["evar/agents/model_reviewer.py"],
            task="Review optional string parsing.",
            claim="_optional_string normalizes blank strings to None.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="model_reviewer.py returns None when value is a string whose stripped content is empty.",
            claim_family="behavior_inversion",
        ),
        _case(
            4,
            files=["evar/agents/model_reviewer.py"],
            task="Review reviewer receipt validation.",
            claim="parse_reviewer_receipts accepts unknown evidence_type values.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="_parse_receipt constructs EvidenceType(...) and raises ModelOutputError for unsupported values.",
            claim_family="missing_guard",
        ),
        _case(
            5,
            files=["evar/eval/metrics.py"],
            task="Review configured-result aggregation.",
            claim="compute_fcr_scr counts final_actionable records when no actionable_findings list is present.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="_has_actionable_finding returns bool(record['final_actionable']) when that key exists.",
            claim_family="stale_evidence",
        ),
        _case(
            6,
            files=["evar/eval/metrics.py"],
            task="Review failed-run aggregation.",
            claim="compute_fcr_scr includes failed runs in completed-case denominators.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="compute_fcr_scr filters completed records to rows whose run_status is ok before computing denominators.",
            claim_family="behavior_inversion",
        ),
        _case(
            7,
            files=["evar/verifier/verify.py"],
            task="Review verifier process execution.",
            claim="execute_command intentionally invokes subprocess.run with shell=False.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="verify.py passes shell=False in subprocess.run.",
            claim_family="incorrect_call_relationship",
        ),
        _case(
            8,
            files=["evar/verifier/verify.py"],
            task="Review verifier working directory.",
            claim="execute_command runs verification commands from the caller process working directory instead of the case repo.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="verify.py passes cwd=repo_path to subprocess.run.",
            claim_family="causal_mislocalization",
        ),
        _case(
            9,
            files=["evar/run.py"],
            task="Review configured run transcript output.",
            claim="_run_configured writes per-case transcript JSON files under results/transcripts.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="_run_configured creates output_dir / 'transcripts' / run_id and writes transcript files.",
            claim_family="stale_evidence",
        ),
        _case(
            10,
            files=["evar/run.py"],
            task="Review configured run overwrite policy.",
            claim="_run_configured overwrites an existing result JSONL file if run_id collides.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="_run_configured raises RuntimeError when output_path already exists.",
            claim_family="missing_guard",
        ),
    ]
    with CASES.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _case(
    number: int,
    *,
    files: list[str],
    task: str,
    claim: str,
    ground_truth: str,
    ground_truth_evidence: str,
    claim_family: str,
) -> dict[str, object]:
    repo = REPOS / f"case_{number:03d}"
    repo.mkdir(parents=True, exist_ok=True)
    for relative in files:
        source = PROJECT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return {
        "case_id": f"real10_{number:03d}_{claim_family}_{ground_truth.lower()}",
        "repo_path": str(repo.relative_to(PROJECT)).replace("\\", "/"),
        "task_description": task,
        "claim": claim,
        "ground_truth": ground_truth,
        "ground_truth_evidence": ground_truth_evidence,
        "validation_command": ["python", "-m", "unittest", "discover"],
        "claim_family": claim_family,
    }


if __name__ == "__main__":
    main()
