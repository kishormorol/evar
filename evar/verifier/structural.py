from __future__ import annotations

from evar.verifier.models import EvidenceKind, EvidenceReceipt, VerificationResult


class StructuralVerifier:
    def verify(self, receipt: EvidenceReceipt) -> VerificationResult:
        if receipt.kind != EvidenceKind.STRUCTURAL:
            return VerificationResult(False, receipt.kind, "Receipt is not structural evidence.")
        if not receipt.target.exists():
            return VerificationResult(False, receipt.kind, f"Target does not exist: {receipt.target}")
        if receipt.line_start is None or receipt.line_end is None:
            return VerificationResult(False, receipt.kind, "Structural evidence requires line range.")
        if receipt.line_start < 1 or receipt.line_end < receipt.line_start:
            return VerificationResult(False, receipt.kind, "Invalid line range.")

        lines = receipt.target.read_text(encoding="utf-8").splitlines()
        if receipt.line_end > len(lines):
            return VerificationResult(False, receipt.kind, "Line range exceeds file length.")

        excerpt = "\n".join(lines[receipt.line_start - 1 : receipt.line_end])
        if receipt.must_contain and receipt.must_contain not in excerpt:
            return VerificationResult(
                False,
                receipt.kind,
                "Required text not found in structural excerpt.",
                {"excerpt": excerpt},
            )
        return VerificationResult(True, receipt.kind, "Structural evidence verified.", {"excerpt": excerpt})
