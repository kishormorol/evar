from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from evar.eval.compare import main


class EvalCompareTests(unittest.TestCase):
    def test_compare_reports_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            records = [
                _record("AR", "SUPPORTED", True, input_tokens=10, output_tokens=5),
                _record("AR", "UNSUPPORTED", True, input_tokens=20, output_tokens=7),
                _record("AR", "UNSUPPORTED", False, run_status="failed", failure_type="ModelOutputError"),
            ]
            path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main([str(path)])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Protocol\tSupported claims\tUnsupported claims", output)
        self.assertIn("AR\t1\t1\t1\t1\t1.000\t1.000\t1\t0\t15.5\t6.0", output)


def _record(
    protocol: str,
    ground_truth: str,
    final_actionable: bool,
    *,
    run_status: str = "ok",
    failure_type: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "case_id": f"{protocol}-{ground_truth}-{final_actionable}",
        "protocol": protocol,
        "ground_truth": ground_truth,
        "final_actionable": final_actionable,
        "verification_status": "VERIFIED",
        "run_status": run_status,
        "metadata": {
            "reviewer_model": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            "critic_model": {"input_tokens": input_tokens + 1 if input_tokens is not None else None, "output_tokens": output_tokens},
        },
    }
    if failure_type is not None:
        record["failure"] = {"type": failure_type, "reason": "bad json"}
    return record
