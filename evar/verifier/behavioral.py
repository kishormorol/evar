from __future__ import annotations

import subprocess

from evar.verifier.models import EvidenceKind, EvidenceReceipt, VerificationResult


class BehavioralVerifier:
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    def verify(self, receipt: EvidenceReceipt) -> VerificationResult:
        if receipt.kind != EvidenceKind.BEHAVIORAL:
            return VerificationResult(False, receipt.kind, "Receipt is not behavioral evidence.")
        if receipt.command is None:
            return VerificationResult(False, receipt.kind, "Behavioral evidence requires a command.")

        try:
            completed = subprocess.run(
                receipt.command,
                cwd=receipt.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return VerificationResult(False, receipt.kind, f"Command failed to execute: {exc}")

        details = {
            "returncode": str(completed.returncode),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        if completed.returncode != receipt.expected_exit_code:
            return VerificationResult(False, receipt.kind, "Unexpected exit code.", details)
        if receipt.stdout_must_contain and receipt.stdout_must_contain not in completed.stdout:
            return VerificationResult(False, receipt.kind, "Required stdout text not found.", details)
        return VerificationResult(True, receipt.kind, "Behavioral evidence verified.", details)
