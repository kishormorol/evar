from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from evar.eval.metrics import compute_fcr_scr
from evar.eval_table import main


class EvalMetricsTests(unittest.TestCase):
    def test_compute_fcr_scr_from_result_records(self) -> None:
        summary = compute_fcr_scr(
            [
                _record("AR", "SUPPORTED", actionable=True),
                _record("AR", "SUPPORTED", actionable=False),
                _record("AR", "UNSUPPORTED", actionable=True),
                _record("AR", "UNSUPPORTED", actionable=False),
            ]
        )

        self.assertEqual(summary.protocol, "AR")
        self.assertEqual(summary.total_cases, 4)
        self.assertEqual(summary.completed_cases, 4)
        self.assertEqual(summary.supported_cases, 2)
        self.assertEqual(summary.unsupported_cases, 2)
        self.assertEqual(summary.supported_actionable, 1)
        self.assertEqual(summary.unsupported_actionable, 1)
        self.assertEqual(summary.fcr, 0.5)
        self.assertEqual(summary.scr, 0.5)

    def test_compute_fcr_scr_excludes_failed_runs_from_denominators(self) -> None:
        summary = compute_fcr_scr(
            [
                _record("EVAR-Hard", "SUPPORTED", actionable=True),
                _record("EVAR-Hard", "SUPPORTED", actionable=False, run_status="failed"),
                _record("EVAR-Hard", "UNSUPPORTED", actionable=True, run_status="failed"),
            ]
        )

        self.assertEqual(summary.total_cases, 3)
        self.assertEqual(summary.completed_cases, 1)
        self.assertEqual(summary.failed_runs, 2)
        self.assertEqual(summary.supported_cases, 1)
        self.assertEqual(summary.unsupported_cases, 0)
        self.assertEqual(summary.fcr, 0.0)
        self.assertEqual(summary.scr, 1.0)

    def test_compute_fcr_scr_marks_mixed_protocols(self) -> None:
        summary = compute_fcr_scr(
            [
                _record("AR", "SUPPORTED", actionable=True),
                _record("EVAR-Hard", "UNSUPPORTED", actionable=False),
            ]
        )

        self.assertEqual(summary.protocol, "mixed")

    def test_eval_table_outputs_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            _write_jsonl(
                path,
                [
                    _record("AR", "SUPPORTED", actionable=True),
                    _record("AR", "UNSUPPORTED", actionable=True),
                ],
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--results", str(path), "--format", "table"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("protocol\tn\tcompleted\tfailed\tsupported\tunsupported\tFCR\tSCR", output)
        self.assertIn("AR\t2\t2\t0\t1\t1\t1.000\t1.000", output)

    def test_eval_table_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            _write_jsonl(path, [_record("EVAR-Hard", "UNSUPPORTED", actionable=False)])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--results", str(path), "--format", "json"])

        self.assertEqual(exit_code, 0)
        row = json.loads(stdout.getvalue())
        self.assertEqual(row["protocol"], "EVAR-Hard")
        self.assertEqual(row["fcr"], 0.0)
        self.assertEqual(row["scr"], 0.0)

    def test_eval_table_outputs_bootstrap_columns_and_paired_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ar_path = Path(tmp) / "ar.jsonl"
            evar_path = Path(tmp) / "evar.jsonl"
            _write_jsonl(
                ar_path,
                [
                    _record("AR", "UNSUPPORTED", actionable=True, case_id="u1"),
                    _record("AR", "SUPPORTED", actionable=True, case_id="s1"),
                ],
            )
            _write_jsonl(
                evar_path,
                [
                    _record("EVAR-Hard", "UNSUPPORTED", actionable=False, case_id="u1"),
                    _record("EVAR-Hard", "SUPPORTED", actionable=True, case_id="s1"),
                ],
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--results",
                        str(ar_path),
                        str(evar_path),
                        "--bootstrap",
                        "100",
                        "--seed",
                        "7",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("FCR_low", output)
        self.assertIn("comparison\tdelta_FCR", output)
        self.assertIn("EVAR-Hard-AR", output)


def _record(
    protocol: str,
    ground_truth: str,
    *,
    actionable: bool,
    run_status: str = "ok",
    case_id: str | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id or f"{protocol}-{ground_truth}-{actionable}-{run_status}",
        "protocol": protocol,
        "ground_truth": ground_truth,
        "actionable_findings": [{"id": "finding"}] if actionable else [],
        "run_status": run_status,
    }


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
