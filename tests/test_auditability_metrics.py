from __future__ import annotations

import unittest

from evar.eval.auditability import auditability_summary
from evar.eval.gate_ablation import exact_mcnemar_p_value


class AuditabilityMetricsTests(unittest.TestCase):
    def test_complete_verified_actionable_row_is_traceable(self) -> None:
        row = {
            "run_status": "ok",
            "protocol": "evar_blind_gate",
            "transcript_path": "record.json",
            "final_actionable": True,
            "findings": [
                {
                    "critic_decision": "ACCEPT",
                    "evidence_receipt": {
                        "claim_id": "one",
                        "claim": "claim",
                        "evidence_type": "structural",
                        "evidence_role": "supports_claim",
                        "file": "code.py",
                        "falsification_condition": "line absent",
                    },
                    "verification_result": {"status": "VERIFIED"},
                }
            ],
        }

        summary = auditability_summary([row])

        self.assertEqual(summary["transcript_coverage"], 1.0)
        self.assertEqual(summary["receipt_schema_coverage"], 1.0)
        self.assertEqual(summary["verifier_outcome_coverage"], 1.0)
        self.assertEqual(summary["actionable_with_machine_checked_receipt"], 1)
        self.assertEqual(summary["machine_checked_receipt_coverage_for_hard_actionable"], 1.0)
        self.assertEqual(summary["hard_gate_invariant_violations"], 0)

    def test_failed_rows_require_type_and_reason_for_attribution(self) -> None:
        summary = auditability_summary(
            [
                {"run_status": "failed", "failure": {"type": "Timeout", "reason": "120s"}},
                {"run_status": "failed", "failure": {"type": "Parse", "reason": ""}},
            ]
        )

        self.assertEqual(summary["typed_failure_coverage"], 0.5)
        self.assertEqual(summary["failure_types"], {"Parse": 1, "Timeout": 1})

    def test_exact_mcnemar_is_two_sided_and_handles_no_discordance(self) -> None:
        self.assertEqual(exact_mcnemar_p_value(0, 0), 1.0)
        self.assertEqual(exact_mcnemar_p_value(1, 0), 1.0)
        self.assertEqual(exact_mcnemar_p_value(2, 0), 0.5)
        with self.assertRaises(ValueError):
            exact_mcnemar_p_value(-1, 0)


if __name__ == "__main__":
    unittest.main()
