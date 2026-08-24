from __future__ import annotations

import unittest

from evar.eval.bootstrap import bootstrap_paired_delta_ci, bootstrap_rate_ci, paired_delta


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_rate_ci_is_seeded_and_deterministic(self) -> None:
        records = [
            _record("AR", "UNSUPPORTED", "u1", actionable=True),
            _record("AR", "UNSUPPORTED", "u2", actionable=False),
            _record("AR", "UNSUPPORTED", "u3", actionable=True),
        ]

        first = bootstrap_rate_ci(records, "fcr", n=200, seed=11)
        second = bootstrap_rate_ci(records, "fcr", n=200, seed=11)

        self.assertEqual(first, second)
        self.assertEqual(first.estimate, 2 / 3)
        self.assertLessEqual(first.low, first.estimate)
        self.assertGreaterEqual(first.high, first.estimate)

    def test_paired_delta_uses_case_ids(self) -> None:
        ar = [
            _record("AR", "UNSUPPORTED", "u1", actionable=True),
            _record("AR", "UNSUPPORTED", "u2", actionable=True),
        ]
        evar = [
            _record("EVAR-Hard", "UNSUPPORTED", "u1", actionable=False),
            _record("EVAR-Hard", "UNSUPPORTED", "u2", actionable=True),
        ]

        self.assertEqual(paired_delta(ar, evar, "fcr"), -0.5)

    def test_bootstrap_paired_delta_ci_is_seeded(self) -> None:
        ar = [
            _record("AR", "SUPPORTED", "s1", actionable=True),
            _record("AR", "SUPPORTED", "s2", actionable=True),
        ]
        evar = [
            _record("EVAR-Hard", "SUPPORTED", "s1", actionable=True),
            _record("EVAR-Hard", "SUPPORTED", "s2", actionable=False),
        ]

        first = bootstrap_paired_delta_ci(ar, evar, "scr", n=200, seed=5)
        second = bootstrap_paired_delta_ci(ar, evar, "scr", n=200, seed=5)

        self.assertEqual(first, second)
        self.assertEqual(first.estimate, -0.5)


def _record(protocol: str, ground_truth: str, case_id: str, *, actionable: bool) -> dict[str, object]:
    return {
        "case_id": case_id,
        "protocol": protocol,
        "ground_truth": ground_truth,
        "actionable_findings": [{"id": "f"}] if actionable else [],
        "run_status": "ok",
    }
