from __future__ import annotations

import unittest

from evar.eval.gate_ablation import replay_gate, summarize_gate_replay


def _row(
    case_id: str,
    ground_truth: str,
    *,
    verification: str,
    decision: str = "ACCEPT",
    role: str = "supports_claim",
    status: str = "ok",
) -> dict[str, object]:
    hard = status == "ok" and verification == "VERIFIED" and decision == "ACCEPT" and role == "supports_claim"
    return {
        "case_id": case_id,
        "protocol": "evar_hard",
        "ground_truth": ground_truth,
        "run_status": status,
        "final_actionable": hard,
        "findings": [
            {
                "critic_decision": decision,
                "evidence_receipt": {"evidence_role": role},
                "verification_result": {"status": verification},
            }
        ],
        "metadata": {"model": {"model": "test-model"}},
    }


class GateAblationTests(unittest.TestCase):
    def test_gate_replay_holds_model_outputs_fixed_and_changes_only_gate(self) -> None:
        decision = replay_gate(
            _row("supported", "SUPPORTED", verification="FAILED", decision="ACCEPT")
        )

        self.assertTrue(decision.critic_only)
        self.assertTrue(decision.role_aware_soft)
        self.assertFalse(decision.hard)

    def test_summary_reports_gate_effect_and_operating_points(self) -> None:
        summary = summarize_gate_replay(
            [
                _row("s1", "SUPPORTED", verification="VERIFIED"),
                _row("s2", "SUPPORTED", verification="FAILED"),
                _row("u1", "UNSUPPORTED", verification="FAILED"),
                _row("u2", "UNSUPPORTED", verification="VERIFIED", decision="COUNTEREXAMPLE"),
            ]
        )
        model = summary["models"]["test-model"]

        self.assertEqual(model["role_aware_soft"]["scr"], 1.0)
        self.assertEqual(model["hard"]["scr"], 0.5)
        self.assertEqual(model["role_aware_soft"]["fcr"], 0.5)
        self.assertEqual(model["hard"]["fcr"], 0.0)
        self.assertEqual(model["gate_effect"]["soft_accept_to_hard_reject"], 2)
        self.assertEqual(model["gate_effect"]["hard_accept_without_soft_accept"], 0)

    def test_gate_replay_rejects_a_record_that_violates_the_hard_gate(self) -> None:
        row = _row("bad", "SUPPORTED", verification="FAILED")
        row["final_actionable"] = True

        with self.assertRaisesRegex(ValueError, "violates"):
            replay_gate(row)


if __name__ == "__main__":
    unittest.main()
