from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evar import run


class RunCliTests(unittest.TestCase):
    def test_run_ar_outputs_jsonl_result(self) -> None:
        record = self._run_protocol("ar")

        self.assertEqual(record["protocol"], "AR")
        self.assertEqual(record["run_status"], "ok")
        self.assertEqual(record["case_id"], "case-1")
        self.assertEqual(record["claim_family"], "missing_guard")
        self.assertEqual(record["ground_truth"], "UNSUPPORTED")
        self.assertEqual(record["metrics"]["false_positives"], 1)
        self.assertIn("findings", record)

    def test_run_ar_text_outputs_jsonl_result(self) -> None:
        record = self._run_protocol("ar_text")

        self.assertEqual(record["protocol"], "AR-Text")
        self.assertEqual(record["metrics"]["false_positives"], 0)
        self.assertEqual(record["actionable_findings"], [])

    def test_run_evar_outputs_jsonl_result_with_verification_status(self) -> None:
        record = self._run_protocol("evar")

        self.assertEqual(record["protocol"], "EVAR-Hard")
        self.assertEqual(record["metrics"]["false_positives"], 0)
        self.assertEqual(record["actionable_findings"], [])
        self.assertEqual(record["verification_results"]["case-1"]["status"], "UNVERIFIABLE")
        self.assertGreaterEqual(len(record["interaction_log"]), 1)

    def test_run_logs_case_failure_without_dropping_example(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.jsonl"
            cases.write_text(json.dumps(_raw_case(Path(tmp))) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.object(run, "_build_protocol", return_value=_FailingProtocol()):
                with contextlib.redirect_stdout(stdout):
                    exit_code = run.main(["--protocol", "evar", "--cases", str(cases)])

        self.assertEqual(exit_code, 0)
        lines = [json.loads(line) for line in stdout.getvalue().splitlines() if line]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["run_status"], "failed")
        self.assertEqual(lines[0]["case_id"], "case-1")
        self.assertEqual(lines[0]["failure"]["type"], "RuntimeError")

    def _run_protocol(self, protocol: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.jsonl"
            cases.write_text(json.dumps(_raw_case(Path(tmp))) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = run.main(["--protocol", protocol, "--cases", str(cases)])

        self.assertEqual(exit_code, 0)
        lines = [line for line in stdout.getvalue().splitlines() if line]
        self.assertEqual(len(lines), 1)
        return json.loads(lines[0])


def _raw_case(repo: Path) -> dict[str, object]:
    return {
        "case_id": "case-1",
        "repo_path": str(repo),
        "task_description": "Review the guard.",
        "claim": "handler is missing an input guard",
        "ground_truth": "UNSUPPORTED",
        "ground_truth_evidence": "The guard exists in sample.py.",
        "validation_command": ["python", "-m", "unittest"],
        "claim_family": "missing_guard",
    }


class _FailingProtocol:
    def run(self, case: object) -> object:
        del case
        raise RuntimeError("intentional test failure")
