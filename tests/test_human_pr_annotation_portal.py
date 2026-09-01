from __future__ import annotations

import unittest
from pathlib import Path


class HumanPRAnnotationPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = Path("review/human_pr_200.html").read_text(encoding="utf-8")

    def test_portal_explains_the_task_before_the_form(self) -> None:
        guide = self.html.index("Your one task")
        decision = self.html.index("Your answer")

        self.assertLess(guide, decision)
        self.assertIn("Was the problem described in the comment present", self.html)
        self.assertIn("Need help or an example?", self.html)
        self.assertNotIn('<details class="guide" open>', self.html)

    def test_portal_uses_plain_language_field_help(self) -> None:
        self.assertIn("Does this comment describe one specific code problem", self.html)
        self.assertIn("Can you see this problem in BEFORE?", self.html)
        self.assertIn("Is this problem gone in AFTER?", self.html)
        self.assertIn("Find unanswered item", self.html)

    def test_portal_reveals_only_relevant_follow_up_fields(self) -> None:
        self.assertIn('id="eligible-fields" class="followup" hidden', self.html)
        self.assertIn('id="ineligible-fields" class="field wide" hidden', self.html)
        self.assertIn("$('eligible-fields').hidden=eligible!=='true'", self.html)
        self.assertIn("$('ineligible-fields').hidden=eligible!=='false'", self.html)

    def test_navigation_returns_reviewer_to_the_next_item(self) -> None:
        self.assertIn("function showItem(index)", self.html)
        self.assertIn("scrollIntoView({behavior:'smooth',block:'start'})", self.html)
        self.assertIn("showItem(state.index+1)", self.html)

    def test_portal_loads_full_blinded_queue(self) -> None:
        self.assertIn("annotation_queue_682.jsonl", self.html)
        self.assertNotIn("llm_annotations", self.html)
        self.assertIn("Please work independently", self.html)


if __name__ == "__main__":
    unittest.main()
