from __future__ import annotations

import unittest

from scripts.report_human_pr_20_cross_provider import summarize_failures


class CrossProviderReportTests(unittest.TestCase):
    def test_failure_taxonomy_distinguishes_transport_from_model_output(self) -> None:
        runs = [{
            "model": "example-model",
            "rows": [
                {"run_status": "ok"},
                {
                    "run_status": "failed",
                    "failure": {"type": "URLError", "reason": "curl operation timed out"},
                },
                {
                    "run_status": "failed",
                    "failure": {"type": "ModelOutputError", "reason": "invalid schema"},
                },
                {
                    "run_status": "failed",
                    "failure": {"type": "RuntimeError", "reason": "other"},
                },
            ],
        }]

        self.assertEqual(
            summarize_failures(runs),
            [{
                "model": "example-model",
                "attempted": 4,
                "valid": 1,
                "transport_timeout": 1,
                "schema_or_parse": 1,
                "other": 1,
            }],
        )


if __name__ == "__main__":
    unittest.main()
