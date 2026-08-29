from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from evar.eval.metrics import compute_efficiency_metrics, compute_fcr_scr
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

    def test_compute_efficiency_metrics_sums_model_tokens_per_case(self) -> None:
        summary = compute_efficiency_metrics(
            [
                _record(
                    "AR",
                    "SUPPORTED",
                    actionable=True,
                    duration=1.25,
                    reviewer_tokens=(100, 20),
                    critic_tokens=(50, 10),
                ),
                _record(
                    "AR",
                    "UNSUPPORTED",
                    actionable=False,
                    duration=0.75,
                    reviewer_tokens=(80, 15),
                    critic_tokens=(40, 5),
                ),
            ]
        )

        self.assertEqual(summary.protocol, "AR")
        self.assertEqual(summary.measured_duration_cases, 2)
        self.assertEqual(summary.total_duration_seconds, 2.0)
        self.assertEqual(summary.mean_duration_seconds, 1.0)
        self.assertEqual(summary.tokenized_cases, 2)
        self.assertEqual(summary.total_input_tokens, 270)
        self.assertEqual(summary.total_output_tokens, 50)
        self.assertEqual(summary.mean_input_tokens, 135.0)
        self.assertEqual(summary.mean_output_tokens, 25.0)

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

    def test_eval_table_outputs_metrics_by_claim_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ar_path = Path(tmp) / "ar.jsonl"
            evar_path = Path(tmp) / "evar.jsonl"
            _write_jsonl(
                ar_path,
                [
                    _record("AR", "SUPPORTED", actionable=True, claim_family="missing_guard"),
                    _record("AR", "UNSUPPORTED", actionable=True, claim_family="missing_guard"),
                    _record("AR", "UNSUPPORTED", actionable=False, claim_family="stale_evidence"),
                ],
            )
            _write_jsonl(
                evar_path,
                [
                    _record("EVAR-Hard", "SUPPORTED", actionable=True, claim_family="missing_guard"),
                    _record("EVAR-Hard", "UNSUPPORTED", actionable=False, claim_family="missing_guard"),
                    _record("EVAR-Hard", "UNSUPPORTED", actionable=False, claim_family="stale_evidence"),
                ],
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--results",
                        str(ar_path),
                        str(evar_path),
                        "--by-family",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("claim_family\tprotocol\tn\tcompleted", output)
        self.assertIn("missing_guard\tAR\t2\t2\t0\t1\t1\t1.000\t1.000", output)
        self.assertIn("missing_guard\tEVAR-Hard\t2\t2\t0\t1\t1\t0.000\t1.000", output)
        self.assertIn("stale_evidence\tAR\t1\t1\t0\t0\t1\t0.000\t0.000", output)

    def test_eval_table_outputs_json_family_rows_with_bootstrap_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            _write_jsonl(
                path,
                [
                    _record("EVAR-Hard", "SUPPORTED", actionable=True, claim_family="missing_guard"),
                    _record("EVAR-Hard", "UNSUPPORTED", actionable=False, claim_family="missing_guard"),
                ],
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--results",
                        str(path),
                        "--format",
                        "json",
                        "--by-family",
                        "--bootstrap",
                        "20",
                    ]
                )

        self.assertEqual(exit_code, 0)
        rows = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertNotIn("claim_family", rows[0])
        self.assertEqual(rows[1]["claim_family"], "missing_guard")
        self.assertEqual(rows[1]["protocol"], "EVAR-Hard")
        self.assertEqual(rows[1]["fcr_low"], 0.0)
        self.assertEqual(rows[1]["scr_high"], 1.0)

    def test_eval_table_outputs_cost_and_latency_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            _write_jsonl(
                path,
                [
                    _record(
                        "EVAR-Hard",
                        "SUPPORTED",
                        actionable=True,
                        duration=1.5,
                        reviewer_tokens=(100, 20),
                        critic_tokens=(50, 10),
                    ),
                    _record(
                        "EVAR-Hard",
                        "UNSUPPORTED",
                        actionable=False,
                        duration=0.5,
                        reviewer_tokens=(80, 10),
                        critic_tokens=(20, 5),
                    ),
                ],
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--results", str(path), "--costs"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("protocol\tn\tduration_n\ttotal_seconds\tmean_seconds", output)
        self.assertIn("EVAR-Hard\t2\t2\t2.000\t1.000\t2\t250\t45\t125.0\t22.5", output)


def _record(
    protocol: str,
    ground_truth: str,
    *,
    actionable: bool,
    run_status: str = "ok",
    case_id: str | None = None,
    claim_family: str | None = None,
    duration: float | None = None,
    reviewer_tokens: tuple[int, int] | None = None,
    critic_tokens: tuple[int, int] | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "case_id": case_id or f"{protocol}-{ground_truth}-{actionable}-{run_status}",
        "protocol": protocol,
        "ground_truth": ground_truth,
        "actionable_findings": [{"id": "finding"}] if actionable else [],
        "run_status": run_status,
    }
    if claim_family is not None:
        record["claim_family"] = claim_family
    if duration is not None:
        record["duration"] = duration
    if reviewer_tokens is not None or critic_tokens is not None:
        record["metadata"] = {
            "reviewer_model": _token_metadata(reviewer_tokens),
            "critic_model": _token_metadata(critic_tokens),
        }
    return record


def _token_metadata(tokens: tuple[int, int] | None) -> dict[str, int] | None:
    if tokens is None:
        return None
    return {"input_tokens": tokens[0], "output_tokens": tokens[1]}


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
