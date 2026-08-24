from __future__ import annotations

from evar.verifier.behavioral import BehavioralVerifier
from evar.verifier.models import EvidenceKind, EvidenceReceipt, VerificationResult
from evar.verifier.structural import StructuralVerifier


class DeterministicVerifier:
    """Dispatches structured receipts to deterministic non-LLM verifiers."""

    def __init__(
        self,
        structural: StructuralVerifier | None = None,
        behavioral: BehavioralVerifier | None = None,
    ) -> None:
        self.structural = structural or StructuralVerifier()
        self.behavioral = behavioral or BehavioralVerifier()

    def verify(self, receipt: EvidenceReceipt) -> VerificationResult:
        if receipt.kind == EvidenceKind.STRUCTURAL:
            return self.structural.verify(receipt)
        if receipt.kind == EvidenceKind.BEHAVIORAL:
            return self.behavioral.verify(receipt)
        return VerificationResult(False, receipt.kind, f"Unsupported evidence kind: {receipt.kind}")
