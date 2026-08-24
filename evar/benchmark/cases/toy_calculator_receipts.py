from __future__ import annotations

from pathlib import Path

from evar.verifier.models import EvidenceReceipt, EvidenceType


TOY_REPO_PATH = Path(__file__).parent / "toy_calculator_repo"


SUPPORTED_RECEIPT = EvidenceReceipt(
    claim_id="claim_true_001",
    claim="divide(10, 0) raises ZeroDivisionError",
    evidence_type=EvidenceType.BEHAVIORAL,
    file="calculator.py",
    line_start=1,
    line_end=2,
    verification_command="python -m pytest test_supported.py -q",
    expected_exit_code=0,
    expected_stdout_contains="EVAR_WITNESS_PASS",
    falsification_condition="FAILED",
)


UNSUPPORTED_RECEIPT = EvidenceReceipt(
    claim_id="claim_false_001",
    claim="divide(10, 2) raises ZeroDivisionError",
    evidence_type=EvidenceType.BEHAVIORAL,
    file="calculator.py",
    line_start=1,
    line_end=2,
    verification_command="python -m pytest test_unsupported.py -q",
    expected_exit_code=0,
    expected_stdout_contains="EVAR_WITNESS_PASS",
    falsification_condition="FAILED",
)
