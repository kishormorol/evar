from __future__ import annotations

import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from evar.preflight import main, run_preflight


class PreflightTests(unittest.TestCase):
    def test_pilot_preflight_passes(self) -> None:
        report = run_preflight(Path("configs/pilot.yaml"), Path("benchmark/pilot_cases.jsonl"))

        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.cases, 10)
        self.assertIn("reviewer_evar_v1.txt", report.prompt_hashes)

    def test_missing_repo_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "cases.jsonl"
            case_path.write_text(json.dumps(_case(Path(tmp) / "missing")) + "\n", encoding="utf-8")

            report = run_preflight(Path("configs/pilot.yaml"), case_path)

        self.assertFalse(report.ok)
        self.assertTrue(any(issue.code == "REPO_MISSING" for issue in report.issues))

    def test_cli_returns_nonzero_on_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_path = Path(tmp) / "cases.jsonl"
            case_path.write_text(json.dumps(_case(Path(tmp) / "missing")) + "\n", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["--config", "configs/pilot.yaml", "--cases", str(case_path)])

        self.assertEqual(exit_code, 2)

    def test_repeated_experiment_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "repeated.yaml"
            text = Path("configs/pilot.yaml").read_text(encoding="utf-8")
            config.write_text(text.replace("repetitions: 1", "repetitions: 3"), encoding="utf-8")

            report = run_preflight(config, Path("benchmark/pilot_cases.jsonl"))

        self.assertTrue(report.ok, report.issues)


def _case(repo_path: Path) -> dict[str, object]:
    return {
        "case_id": "case-1",
        "repo_path": str(repo_path),
        "task_description": "Review the guard.",
        "claim": "handler is missing an input guard",
        "ground_truth": "UNSUPPORTED",
        "ground_truth_evidence": "The guard exists in sample.py.",
        "validation_command": ["python", "-m", "unittest"],
        "claim_family": "missing_guard",
    }
