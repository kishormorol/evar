from __future__ import annotations

from evar.agents.critic import DummyCritic
from evar.agents.reviewer import DummyReviewer
from evar.benchmark.loader import load_dummy_case
from evar.protocols.ar import ARProtocol
from evar.protocols.ar_text import ARTextProtocol
from evar.protocols.base import AgentConfig, ProtocolBudget
from evar.protocols.evar import EVARHardProtocol


def main() -> None:
    case = load_dummy_case().to_task_case()
    reviewer = DummyReviewer()
    critic = DummyCritic()
    config = AgentConfig(model_name="dummy-model", temperature=0.0, seed=7)
    budget = ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1)

    protocols = [
        ARProtocol(reviewer, critic, config, budget),
        ARTextProtocol(reviewer, critic, config, budget),
        EVARHardProtocol(reviewer, critic, config, budget),
    ]

    for protocol in protocols:
        result = protocol.run(case)
        actionable = [finding.id for finding in result.actionable_findings]
        print(f"{result.protocol_name}: actionable={actionable}")


if __name__ == "__main__":
    main()
