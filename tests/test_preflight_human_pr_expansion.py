from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.preflight_human_pr_expansion import check_readiness


class HumanPRExpansionPreflightTests(unittest.TestCase):
    def test_current_study_fails_closed_without_human_exports(self) -> None:
        report = check_readiness()
        codes = {blocker["code"] for blocker in report["blockers"]}

        self.assertFalse(report["ready_for_paid_runs"])
        self.assertIn("ETHICS_DETERMINATION_PENDING", codes)
        self.assertIn("HUMAN_EXPORTS_MISSING", codes)
        self.assertIn("FROZEN_CASES_MISSING", codes)
        self.assertIn("PRICE_FREEZE_MISSING", codes)
        self.assertNotIn("ADVISORY_LLM_LABELS_MISSING", codes)

    def test_placeholder_outputs_do_not_satisfy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benchmark = root / "benchmarks/human_pr_200"
            (benchmark / "frozen").mkdir(parents=True)
            (benchmark / "ETHICS_AND_REVIEWER_GOVERNANCE.md").write_text(
                "- Status: **approved**\n", encoding="utf-8"
            )
            (benchmark / "resolved_annotations.jsonl").write_text("{}\n", encoding="utf-8")
            (benchmark / "final_300.jsonl").write_text("{}\n", encoding="utf-8")
            (benchmark / "frozen/cases.jsonl").write_text("{}\n", encoding="utf-8")
            for name in (
                "contamination_audit.json",
                "model_input_freeze_manifest.json",
                "price_freeze.json",
                "study_input_freeze_manifest.json",
                "cost_projection.json",
            ):
                (benchmark / name).write_text(json.dumps({"status": "frozen"}), encoding="utf-8")
            report = check_readiness(root)
        codes = {blocker["code"] for blocker in report["blockers"]}
        self.assertIn("SELECTION_MISSING", codes)
        self.assertIn("FROZEN_CASES_MISSING", codes)
        self.assertIn("CONTAMINATION_AUDIT_MISSING", codes)
        self.assertIn("MODEL_INPUT_FREEZE_MISSING", codes)
        self.assertIn("PRICE_FREEZE_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
