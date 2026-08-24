from __future__ import annotations

from pathlib import Path

from evar.verifier.models import EvidenceReceipt, VerificationResult
from evar.verifier.verify import verify_evidence


class BehavioralVerifier:
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    def verify(self, receipt: EvidenceReceipt, repo_path: Path) -> VerificationResult:
        return verify_evidence(receipt, repo_path, timeout_seconds=self.timeout_seconds)
