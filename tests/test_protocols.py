from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evar.agents.critic import DummyCritic
from evar.agents.reviewer import DummyReviewer
from evar.benchmark.loader import load_dummy_case
from evar.protocols.ar import ARProtocol
from evar.protocols.ar_text import ARTextProtocol
from evar.protocols.base import AgentConfig, ProtocolBudget
from evar.protocols.evar import EVARHardProtocol
from evar.verifier.models import VerificationStatus


class ProtocolTests(unittest.TestCase):
    def test_protocols_share_config_and_budget(self) -> None:
        config = AgentConfig(model_name="dummy", temperature=0.0, seed=1)
        budget = ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1)
        reviewer = DummyReviewer()
        critic = DummyCritic()

        protocols = [
            ARProtocol(reviewer, critic, config, budget),
            ARTextProtocol(reviewer, critic, config, budget),
            EVARHardProtocol(reviewer, critic, config, budget),
        ]

        self.assertEqual({protocol.config for protocol in protocols}, {config})
        self.assertEqual({protocol.budget for protocol in protocols}, {budget})

    def test_dummy_end_to_end_protocols_run_without_llm(self) -> None:
        case = load_dummy_case().to_task_case()
        config = AgentConfig(model_name="dummy", temperature=0.0, seed=1)
        budget = ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1)
        reviewer = DummyReviewer()
        critic = DummyCritic()

        ar = ARProtocol(reviewer, critic, config, budget).run(case)
        ar_text = ARTextProtocol(reviewer, critic, config, budget).run(case)
        evar = EVARHardProtocol(reviewer, critic, config, budget).run(case)

        self.assertEqual([finding.id for finding in ar.actionable_findings], ["F001"])
        self.assertEqual([finding.id for finding in ar_text.actionable_findings], ["F001"])
        self.assertEqual([finding.id for finding in evar.actionable_findings], ["F001"])
        self.assertEqual(evar.verification_results["F001"].status, VerificationStatus.VERIFIED)

    def test_evar_hard_blocks_unverified_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = load_dummy_case(repo_root=Path(tmp)).to_task_case()
            config = AgentConfig(model_name="dummy", temperature=0.0, seed=1)
            budget = ProtocolBudget(review_turns=1, challenge_turns=1, revision_turns=1)

            result = EVARHardProtocol(DummyReviewer(), DummyCritic(), config, budget).run(case)

        self.assertEqual(result.actionable_findings, [])
        self.assertEqual(result.verification_results["F001"].status, VerificationStatus.UNVERIFIABLE)
