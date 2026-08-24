from __future__ import annotations

from evar.protocols.ar import AREvidenceProtocol
from evar.protocols.ar_text import ARTextEvidenceProtocol
from evar.protocols.evar import Critic, EVARHardEvidenceProtocol, Reviewer
from evar.verifier.verify import DeterministicVerifier


def create_protocol(
    name: str,
    reviewer: Reviewer,
    critic: Critic,
    *,
    verifier: DeterministicVerifier | None = None,
    metadata: dict[str, object] | None = None,
) -> object:
    if name == "ar":
        return AREvidenceProtocol(reviewer, critic, metadata=metadata)
    if name == "ar_text":
        return ARTextEvidenceProtocol(reviewer, critic, metadata=metadata)
    if name == "evar_hard":
        return EVARHardEvidenceProtocol(reviewer, critic, verifier=verifier, metadata=metadata)
    raise ValueError(f"Unknown protocol: {name}")


PROTOCOL_REGISTRY = {
    "ar": AREvidenceProtocol,
    "ar_text": ARTextEvidenceProtocol,
    "evar_hard": EVARHardEvidenceProtocol,
}
