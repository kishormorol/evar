from __future__ import annotations

from pathlib import Path

from evar.verifier.models import EvidenceReceipt, VerificationResult
from evar.verifier.verify import verify_evidence


class StructuralVerifier:
    def verify(self, receipt: EvidenceReceipt, repo_path: Path) -> VerificationResult:
        return verify_evidence(receipt, repo_path)
