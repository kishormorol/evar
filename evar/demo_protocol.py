from __future__ import annotations

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.protocols.evar import CriticDecision, EVARHardEvidenceProtocol, FakeCritic, FakeReviewer


def main() -> None:
    protocol = EVARHardEvidenceProtocol(
        FakeReviewer([SUPPORTED_RECEIPT, UNSUPPORTED_RECEIPT]),
        FakeCritic(
            {
                SUPPORTED_RECEIPT.claim_id: CriticDecision.ACCEPT,
                UNSUPPORTED_RECEIPT.claim_id: CriticDecision.ACCEPT,
            }
        ),
    )
    result = protocol.run("Review calculator behavior.", TOY_REPO_PATH)

    truth = {
        SUPPORTED_RECEIPT.claim_id: "SUPPORTED",
        UNSUPPORTED_RECEIPT.claim_id: "UNSUPPORTED",
    }
    for finding in result.findings:
        final = "ACTIONABLE" if finding.actionable else "REJECTED"
        print(finding.claim_id)
        print(f"Ground truth: {truth[finding.claim_id]}")
        print(f"Verifier: {finding.verification_result.status.value}")
        print(f"Critic: {finding.critic_decision.value}")
        print(f"Final: {final}")
        if (
            finding.verification_result.status.value == "FAILED"
            and finding.critic_decision == CriticDecision.ACCEPT
            and not finding.actionable
        ):
            print("Agents agree, but the evidence fails, therefore the finding cannot become actionable.")
        print()


if __name__ == "__main__":
    main()
