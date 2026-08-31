from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evar.audit_results import audit_results
from evar.freeze import build_manifest, write_manifest


class ResultAuditTests(unittest.TestCase):
    def test_valid_single_case_run_passes_judge_free_audit(self) -> None:
        configs = sorted(Path("configs/frozen_external_pr_50").glob("*.yaml"))
        manifest = build_manifest(Path("."), Path("benchmarks/external_pr_50/cases.jsonl"), configs)
        prompts = {
            Path(path).name: details["sha256"]
            for path, details in manifest["files"].items()
            if details["category"] == "prompt"
        }
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            cases = folder / "cases.jsonl"
            manifest_path = folder / "manifest.json"
            transcript = folder / "case.json"
            results = folder / "results.jsonl"
            case = {
                "case_id": "c1", "ground_truth": "SUPPORTED", "claim_family": "missing_guard"
            }
            cases.write_text(json.dumps(case) + "\n", encoding="utf-8")
            write_manifest(manifest, manifest_path)
            finding = {
                "actionable": True,
                "critic_decision": "ACCEPT",
                "verification_result": {"status": "VERIFIED"},
                "evidence_receipt": {"evidence_role": "supports_claim"},
            }
            transcript.write_text(json.dumps({
                "case_id": "c1", "run_id": "r1", "protocol": "evar_hard",
                "findings": [finding], "accepted_findings": [finding],
            }), encoding="utf-8")
            model = {
                "text": "{}", "input_tokens": 10, "output_tokens": 2,
                "latency_seconds": 0.1,
            }
            record = {
                "case_id": "c1", "run_id": "r1", "protocol": "evar_hard",
                "ground_truth": "SUPPORTED", "claim_family": "missing_guard",
                "run_status": "ok", "duration": 0.2, "final_actionable": True,
                "transcript_path": str(transcript),
                "metadata": {
                    "model": {"model": "gpt-4.1-mini"}, "experiment": {"seed": 7},
                    "reviewer_prompt": {"filename": "reviewer_evar_v1.txt", "sha256": prompts["reviewer_evar_v1.txt"]},
                    "critic_prompt": {"filename": "critic_evar_v1.txt", "sha256": prompts["critic_evar_v1.txt"]},
                    "reviewer_model": model, "critic_model": model,
                },
            }
            results.write_text(json.dumps(record) + "\n", encoding="utf-8")

            report = audit_results(Path("."), cases, manifest_path, [results])

            failed_record = {
                "case_id": "c1", "run_id": "r2", "protocol": "evar_hard",
                "ground_truth": "SUPPORTED", "claim_family": "missing_guard",
                "run_status": "failed", "failure": {"type": "ModelOutputError"},
                "metadata": {
                    "model": {"model": "gpt-4.1-mini"},
                    "experiment": {"seed": 7},
                },
            }
            results.write_text(json.dumps(failed_record) + "\n", encoding="utf-8")
            strict_failed_report = audit_results(Path("."), cases, manifest_path, [results])
            retained_failed_report = audit_results(
                Path("."), cases, manifest_path, [results], allow_failed_runs=True
            )

        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.records, 1)
        self.assertFalse(strict_failed_report.ok)
        self.assertEqual(strict_failed_report.issue_counts, {"FAILED_RUN": 1})
        self.assertTrue(retained_failed_report.ok, retained_failed_report.issues)
        self.assertEqual(retained_failed_report.run_summaries[0]["failed_records"], 1)


if __name__ == "__main__":
    unittest.main()
