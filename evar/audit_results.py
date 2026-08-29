from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from evar.freeze import verify_manifest


@dataclass(frozen=True)
class AuditIssue:
    code: str
    location: str
    message: str


@dataclass(frozen=True)
class AuditReport:
    ok: bool
    expected_cases_per_run: int
    result_files: int
    records: int
    run_summaries: list[dict[str, Any]]
    issue_counts: dict[str, int]
    issues: list[AuditIssue]


def audit_results(
    project_root: Path,
    cases_path: Path,
    manifest_path: Path,
    result_paths: Iterable[Path],
) -> AuditReport:
    root = project_root.resolve()
    cases = {str(row["case_id"]): row for row in _load_jsonl(cases_path)}
    issues = [AuditIssue("FREEZE_MISMATCH", str(manifest_path), error)
              for error in verify_manifest(root, manifest_path)]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prompt_hashes = {
        Path(path).name: details["sha256"]
        for path, details in manifest["files"].items()
        if details.get("category") == "prompt"
    }

    paths = list(result_paths)
    total_records = 0
    summaries: list[dict[str, Any]] = []
    for path in paths:
        records = _load_jsonl(path)
        total_records += len(records)
        issues.extend(_audit_result_file(root, path, records, cases, prompt_hashes))
        signatures = Counter(
            (
                str(row.get("protocol")),
                str(_nested(row, "metadata", "model", "model")),
                str(_nested(row, "metadata", "experiment", "seed")),
            )
            for row in records
        )
        summaries.append(
            {
                "path": str(path),
                "records": len(records),
                "run_signatures": [
                    {"protocol": key[0], "model": key[1], "seed": key[2], "records": count}
                    for key, count in sorted(signatures.items())
                ],
                "failed_records": sum(row.get("run_status") != "ok" for row in records),
            }
        )

    counts = Counter(issue.code for issue in issues)
    return AuditReport(
        ok=not issues,
        expected_cases_per_run=len(cases),
        result_files=len(paths),
        records=total_records,
        run_summaries=summaries,
        issue_counts=dict(sorted(counts.items())),
        issues=issues,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit EVAR result and transcript artifacts without a judge model.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("results", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit_results(args.project_root, args.cases, args.manifest, args.results)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0 if report.ok else 2


def _audit_result_file(
    root: Path,
    path: Path,
    records: list[dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    prompt_hashes: dict[str, str],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    ids = [str(row.get("case_id")) for row in records]
    counts = Counter(ids)
    for case_id, count in sorted(counts.items()):
        if count > 1:
            issues.append(AuditIssue("DUPLICATE_CASE", str(path), f"{case_id} appears {count} times"))
    for case_id in sorted(cases.keys() - counts.keys()):
        issues.append(AuditIssue("MISSING_CASE", str(path), case_id))
    for case_id in sorted(counts.keys() - cases.keys()):
        issues.append(AuditIssue("UNEXPECTED_CASE", str(path), case_id))

    signatures = {
        (row.get("run_id"), row.get("protocol"), _nested(row, "metadata", "model", "model"),
         _nested(row, "metadata", "experiment", "seed"))
        for row in records
    }
    if len(signatures) != 1:
        issues.append(AuditIssue("MIXED_RUN", str(path), f"found {len(signatures)} run signatures"))

    for index, row in enumerate(records, 1):
        location = f"{path}:{index}"
        case_id = str(row.get("case_id"))
        expected = cases.get(case_id)
        if expected is None:
            continue
        for key in ("ground_truth", "claim_family"):
            if row.get(key) != expected.get(key):
                issues.append(AuditIssue("CASE_METADATA_MISMATCH", location, key))
        if row.get("run_status") != "ok":
            issues.append(AuditIssue("FAILED_RUN", location, str(row.get("failure"))))
            continue
        if not isinstance(row.get("duration"), (int, float)) or row["duration"] < 0:
            issues.append(AuditIssue("BAD_DURATION", location, repr(row.get("duration"))))
        _audit_prompts(row, prompt_hashes, location, issues)
        _audit_model_usage(row, location, issues)
        _audit_transcript(root, row, location, issues)
    return issues


def _audit_prompts(
    row: dict[str, Any], prompt_hashes: dict[str, str], location: str, issues: list[AuditIssue]
) -> None:
    for role in ("reviewer_prompt", "critic_prompt"):
        metadata = _nested(row, "metadata", role)
        if not isinstance(metadata, dict):
            issues.append(AuditIssue("PROMPT_METADATA_MISSING", location, role))
            continue
        filename = metadata.get("filename")
        if prompt_hashes.get(str(filename)) != metadata.get("sha256"):
            issues.append(AuditIssue("PROMPT_HASH_MISMATCH", location, str(filename)))


def _audit_model_usage(row: dict[str, Any], location: str, issues: list[AuditIssue]) -> None:
    for role in ("reviewer_model", "critic_model"):
        model = _nested(row, "metadata", role)
        if not isinstance(model, dict):
            issues.append(AuditIssue("MODEL_METADATA_MISSING", location, role))
            continue
        for key in ("input_tokens", "output_tokens"):
            if not isinstance(model.get(key), int) or model[key] < 0:
                issues.append(AuditIssue("TOKEN_USAGE_MISSING", location, f"{role}.{key}"))
        if not isinstance(model.get("latency_seconds"), (int, float)) or model["latency_seconds"] < 0:
            issues.append(AuditIssue("MODEL_LATENCY_MISSING", location, role))


def _audit_transcript(root: Path, row: dict[str, Any], location: str, issues: list[AuditIssue]) -> None:
    raw_path = row.get("transcript_path")
    if not isinstance(raw_path, str):
        issues.append(AuditIssue("TRANSCRIPT_MISSING", location, "no transcript_path"))
        return
    transcript_path = Path(raw_path)
    if not transcript_path.is_absolute():
        transcript_path = root / transcript_path
    if not transcript_path.is_file():
        issues.append(AuditIssue("TRANSCRIPT_MISSING", location, raw_path))
        return
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    for key in ("case_id", "run_id", "protocol"):
        if transcript.get(key) != row.get(key):
            issues.append(AuditIssue("TRANSCRIPT_METADATA_MISMATCH", location, key))
    findings = transcript.get("findings")
    if not isinstance(findings, list) or len(findings) != 1:
        issues.append(AuditIssue("FINDING_COUNT", location, repr(len(findings) if isinstance(findings, list) else None)))
        return
    accepted = transcript.get("accepted_findings")
    accepted_count = len(accepted) if isinstance(accepted, list) else -1
    if bool(row.get("final_actionable")) != (accepted_count > 0):
        issues.append(AuditIssue("ACTIONABLE_MISMATCH", location, f"accepted={accepted_count}"))
    finding = findings[0]
    if not isinstance(finding, dict):
        issues.append(AuditIssue("FINDING_SHAPE", location, "finding is not an object"))
        return
    if bool(finding.get("actionable")):
        if finding.get("critic_decision") != "ACCEPT":
            issues.append(AuditIssue("ACTIONABLE_WITHOUT_ACCEPT", location, repr(finding.get("critic_decision"))))
        protocol = str(row.get("protocol"))
        if protocol == "evar_hard":
            if _nested(finding, "verification_result", "status") != "VERIFIED":
                issues.append(AuditIssue("ACTIONABLE_WITHOUT_VERIFICATION", location, "status is not VERIFIED"))
            if _nested(finding, "evidence_receipt", "evidence_role") != "supports_claim":
                issues.append(AuditIssue("ACTIONABLE_WITHOUT_SUPPORT_ROLE", location, "role is not supports_claim"))
        if protocol == "ar_text" and not isinstance(finding.get("text_evidence"), dict):
            issues.append(AuditIssue("ACTIONABLE_WITHOUT_TEXT_EVIDENCE", location, "missing text_evidence"))
    if any("judge" in str(key).lower() for key in _walk_keys(transcript)):
        issues.append(AuditIssue("JUDGE_METADATA_PRESENT", location, "transcript contains judge-labeled metadata"))


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: row must be an object")
        rows.append(row)
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
