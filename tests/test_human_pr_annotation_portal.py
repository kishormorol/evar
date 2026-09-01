from __future__ import annotations

import unittest
from pathlib import Path


class HumanPRAnnotationPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = Path("review/human_pr_200.html").read_text(encoding="utf-8")

    def test_portal_explains_the_task_before_the_form(self) -> None:
        guide = self.html.index("Start here — what am I deciding?")
        decision = self.html.index("Your decision")

        self.assertLess(guide, decision)
        self.assertIn("Mark “Eligible” only when all are true", self.html)
        self.assertIn("Show a concrete example", self.html)
        self.assertIn("Show the five claim-family definitions", self.html)

    def test_portal_uses_plain_language_field_help(self) -> None:
        self.assertIn("Is this item eligible?", self.html)
        self.assertIn("Is that exact condition present before merge?", self.html)
        self.assertIn("Is that exact condition absent after merge?", self.html)
        self.assertIn("Find next incomplete", self.html)

    def test_portal_loads_full_blinded_queue(self) -> None:
        self.assertIn("annotation_queue_682.jsonl", self.html)
        self.assertNotIn("llm_annotations", self.html)
        self.assertIn("Independence rule", self.html)


if __name__ == "__main__":
    unittest.main()
