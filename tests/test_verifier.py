from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from evar.verifier.models import EvidenceKind, EvidenceReceipt
from evar.verifier.verify import DeterministicVerifier


class VerifierTests(unittest.TestCase):
    def test_structural_verifier_accepts_matching_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.py"
            target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            receipt = EvidenceReceipt(
                kind=EvidenceKind.STRUCTURAL,
                target=target,
                claim="wrong operator",
                line_start=2,
                line_end=2,
                must_contain="return a - b",
            )

            result = DeterministicVerifier().verify(receipt)

        self.assertTrue(result.ok)
        self.assertIn("return a - b", result.details["excerpt"])

    def test_structural_verifier_rejects_non_matching_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.py"
            target.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            receipt = EvidenceReceipt(
                kind=EvidenceKind.STRUCTURAL,
                target=target,
                claim="wrong operator",
                line_start=2,
                line_end=2,
                must_contain="return a - b",
            )

            result = DeterministicVerifier().verify(receipt)

        self.assertFalse(result.ok)

    def test_behavioral_verifier_accepts_expected_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "probe.py"
            script.write_text("print('verified')\n", encoding="utf-8")
            receipt = EvidenceReceipt(
                kind=EvidenceKind.BEHAVIORAL,
                target=script,
                claim="probe prints marker",
                command=(sys.executable, str(script)),
                stdout_must_contain="verified",
            )

            result = DeterministicVerifier().verify(receipt)

        self.assertTrue(result.ok)
