from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.verifier.models import EvidenceReceipt, EvidenceType, VerificationStatus
from evar.verifier.verify import verify_evidence


class VerifierTests(unittest.TestCase):
    def test_structural_verifier_accepts_expected_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            target = repo / "sample.py"
            target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.STRUCTURAL,
                file="sample.py",
                line_start=2,
                line_end=2,
                expected_stdout_contains="return a - b",
                falsification_condition="return a + b",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("return a - b", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_structural_verifier_accepts_dedented_multiline_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            target = repo / "sample.py"
            target.write_text(
                "def merge_records(records):\n"
                "    merged = []\n"
                "    for record in records:\n"
                "        merged.append(record)\n"
                "        merged.append(record)\n",
                encoding="utf-8",
            )
            receipt = _receipt(
                evidence_type=EvidenceType.STRUCTURAL,
                file="sample.py",
                line_start=3,
                line_end=5,
                expected_stdout_contains=(
                    "for record in records:\n"
                    "    merged.append(record)\n"
                    "    merged.append(record)"
                ),
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.exit_code, 0)

    def test_structural_verifier_rejects_missing_expected_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.STRUCTURAL,
                file="sample.py",
                line_start=2,
                line_end=2,
                expected_stdout_contains="return a - b",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Expected structural observation", result.reason)

    def test_structural_verifier_rejects_falsification_condition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.STRUCTURAL,
                file="sample.py",
                line_start=2,
                line_end=2,
                expected_stdout_contains="return",
                falsification_condition="return a + b",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertIn("Falsification", result.reason)

    def test_verifier_marks_missing_file_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipt = _receipt(
                evidence_type=EvidenceType.STRUCTURAL,
                file="missing.py",
                expected_stdout_contains="return",
            )

            result = verify_evidence(receipt, Path(tmp))

        self.assertEqual(result.status, VerificationStatus.UNVERIFIABLE)
        self.assertIsNone(result.exit_code)
        self.assertIn("does not exist", result.reason)

    def test_verifier_marks_missing_lines_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("only one line\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.STRUCTURAL,
                file="sample.py",
                line_start=2,
                line_end=3,
                expected_stdout_contains="anything",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.UNVERIFIABLE)
        self.assertIn("Requested lines", result.reason)

    def test_behavioral_verifier_executes_command_from_repo_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("# referenced file\n", encoding="utf-8")
            probe = repo / "probe.py"
            probe.write_text(
                "from pathlib import Path\n"
                "print(Path.cwd().name)\n"
                "print(Path('marker.txt').read_text())\n"
                "print('EVAR_WITNESS_PASS')\n",
                encoding="utf-8",
            )
            (repo / "marker.txt").write_text("verified from repo cwd", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=f"{sys.executable} probe.py",
                expected_exit_code=0,
                expected_stdout_contains="EVAR_WITNESS_PASS",
                falsification_condition="not from repo",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("verified from repo cwd", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_behavioral_verifier_handles_quoted_python_c_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("def ok():\n    return True\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=(
                    f'{sys.executable} -c "from sample import ok; '
                    "print('EVAR_WITNESS_PASS' if ok() else '')\""
                ),
                expected_exit_code=0,
                expected_stdout_contains="EVAR_WITNESS_PASS",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("EVAR_WITNESS_PASS", result.stdout)

    def test_behavioral_verifier_captures_stderr_and_exit_code_on_failed_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("# referenced file\n", encoding="utf-8")
            probe = repo / "probe.py"
            probe.write_text(
                "import sys\n"
                "print('real stdout')\n"
                "print('real stderr', file=sys.stderr)\n"
                "raise SystemExit(3)\n",
                encoding="utf-8",
            )
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=f"{sys.executable} probe.py",
                expected_exit_code=0,
                expected_stdout_contains="EVAR_WITNESS_PASS",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertEqual(result.exit_code, 3)
        self.assertIn("real stdout", result.stdout)
        self.assertIn("real stderr", result.stderr)

    def test_behavioral_verifier_does_not_trust_claimed_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("# referenced file\n", encoding="utf-8")
            probe = repo / "probe.py"
            probe.write_text("print('actual output')\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=f"{sys.executable} probe.py",
                expected_exit_code=0,
                expected_stdout_contains="EVAR_WITNESS_PASS reviewer claimed output",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertIn("actual output", result.stdout)
        self.assertNotIn("reviewer claimed output", result.stdout)

    def test_behavioral_verifier_marks_missing_command_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("# referenced file\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=None,
                expected_stdout_contains="EVAR_WITNESS_PASS",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.UNVERIFIABLE)
        self.assertIn("verification_command", result.reason)

    def test_behavioral_verifier_marks_timeout_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("# referenced file\n", encoding="utf-8")
            probe = repo / "probe.py"
            probe.write_text("import time\ntime.sleep(2)\nprint('late')\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=f"{sys.executable} probe.py",
                expected_exit_code=0,
                expected_stdout_contains="EVAR_WITNESS_PASS",
            )

            result = verify_evidence(receipt, repo, timeout_seconds=0.1)

        self.assertEqual(result.status, VerificationStatus.UNVERIFIABLE)
        self.assertIsNone(result.exit_code)
        self.assertIn("timed out", result.reason)

    def test_toy_supported_behavioral_claim_verifies(self) -> None:
        result = verify_evidence(SUPPORTED_RECEIPT, TOY_REPO_PATH)

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("EVAR_WITNESS_PASS", result.stdout)
        self.assertIn("command=", result.reason)

    def test_toy_unsupported_behavioral_claim_fails(self) -> None:
        result = verify_evidence(UNSUPPORTED_RECEIPT, TOY_REPO_PATH)

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Expected exit code", result.reason)

    def test_wrong_expected_stdout_fails(self) -> None:
        receipt = EvidenceReceipt(
            claim_id="toy-wrong-output",
            claim="divide(10, 0) raises ZeroDivisionError",
            evidence_type=EvidenceType.BEHAVIORAL,
            file="calculator.py",
            line_start=1,
            line_end=2,
            verification_command="python -m pytest test_supported.py -q",
            expected_exit_code=0,
            expected_stdout_contains="EVAR_WITNESS_PASS_MISSING",
            falsification_condition="FAILED",
        )

        result = verify_evidence(receipt, TOY_REPO_PATH)

        self.assertEqual(result.status, VerificationStatus.FAILED)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Expected stdout text", result.reason)

    def test_nonexistent_repo_path_is_unverifiable(self) -> None:
        result = verify_evidence(SUPPORTED_RECEIPT, TOY_REPO_PATH / "missing")

        self.assertEqual(result.status, VerificationStatus.UNVERIFIABLE)
        self.assertIn("Repository path does not exist", result.reason)

    def test_behavioral_verification_is_deterministic_under_repeated_execution(self) -> None:
        first = verify_evidence(SUPPORTED_RECEIPT, TOY_REPO_PATH)
        second = verify_evidence(SUPPORTED_RECEIPT, TOY_REPO_PATH)

        self.assertEqual(first.status, second.status)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, second.stderr)
        self.assertEqual(first.exit_code, second.exit_code)

    def test_behavioral_receipt_without_support_marker_is_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sample.py").write_text("# referenced file\n", encoding="utf-8")
            probe = repo / "probe.py"
            probe.write_text("print('plain output')\n", encoding="utf-8")
            receipt = _receipt(
                evidence_type=EvidenceType.BEHAVIORAL,
                file="sample.py",
                verification_command=f"{sys.executable} probe.py",
                expected_exit_code=0,
                expected_stdout_contains="plain output",
            )

            result = verify_evidence(receipt, repo)

        self.assertEqual(result.status, VerificationStatus.UNVERIFIABLE)
        self.assertIn("EVAR_WITNESS_PASS", result.reason)


def _receipt(
    *,
    evidence_type: EvidenceType,
    file: str,
    line_start: int = 1,
    line_end: int = 1,
    verification_command: str | None = None,
    expected_exit_code: int | None = None,
    expected_stdout_contains: str | None = None,
    falsification_condition: str = "",
) -> EvidenceReceipt:
    return EvidenceReceipt(
        claim_id="C001",
        claim="sample claim",
        evidence_type=evidence_type,
        file=file,
        line_start=line_start,
        line_end=line_end,
        verification_command=verification_command,
        expected_exit_code=expected_exit_code,
        expected_stdout_contains=expected_stdout_contains,
        falsification_condition=falsification_condition,
    )
