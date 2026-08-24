from __future__ import annotations

from evar.benchmark.cases.toy_calculator_receipts import (
    SUPPORTED_RECEIPT,
    TOY_REPO_PATH,
    UNSUPPORTED_RECEIPT,
)
from evar.protocols.evar import CriticDecision, FakeCritic, FakeReviewer
from evar.protocols.registry import create_protocol


def main() -> None:
    rows = []
    for label, receipt in [
        ("SUPPORTED CLAIM", SUPPORTED_RECEIPT),
        ("UNSUPPORTED CLAIM WITH CRITIC ACCEPTANCE", UNSUPPORTED_RECEIPT),
    ]:
        rows.append((label, "", ""))
        for protocol_name, display in [
            ("ar", "AR"),
            ("ar_text", "AR-Text"),
            ("evar_hard", "EVAR-Hard"),
        ]:
            protocol = create_protocol(
                protocol_name,
                FakeReviewer([receipt]),
                FakeCritic(CriticDecision.ACCEPT),
            )
            result = protocol.run("Review calculator behavior.", TOY_REPO_PATH)
            final = "ACTIONABLE" if result.accepted_findings else "REJECTED"
            rows.append(("", display, final))

    for section, protocol, final in rows:
        if section:
            print(section)
        else:
            print(f"{protocol:<10} -> {final}")


if __name__ == "__main__":
    main()
