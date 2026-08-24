from __future__ import annotations

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.verifier.verify import verify_evidence


def main() -> None:
    supported = verify_evidence(SUPPORTED_RECEIPT, TOY_REPO_PATH)
    unsupported = verify_evidence(UNSUPPORTED_RECEIPT, TOY_REPO_PATH)

    print(SUPPORTED_RECEIPT.claim_id)
    print("Ground truth: SUPPORTED")
    print(f"Verification: {supported.status.value}")
    print()
    print(UNSUPPORTED_RECEIPT.claim_id)
    print("Ground truth: UNSUPPORTED")
    print(f"Verification: {unsupported.status.value}")


if __name__ == "__main__":
    main()
