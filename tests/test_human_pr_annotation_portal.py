from __future__ import annotations

import unittest
from pathlib import Path


class HumanPRAnnotationPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = Path("review/human_pr_200.html").read_text(encoding="utf-8")
        cls.walkthrough = Path("review/assets/evar-review-walkthrough.gif")

    def test_portal_explains_the_task_before_the_form(self) -> None:
        guide = self.html.index("What are you doing?")
        decision = self.html.index("Answer these questions")

        self.assertLess(guide, decision)
        self.assertIn("BEFORE</strong><br>The original code", self.html)
        self.assertIn("COMMENT</strong><br>A human points out a problem", self.html)
        self.assertIn("AFTER</strong><br>The final merged code", self.html)
        self.assertIn("Prefer text? Read the same example", self.html)
        self.assertNotIn('<details class="guide" open>', self.html)

    def test_portal_embeds_a_complete_animated_walkthrough(self) -> None:
        self.assertIn("Watch one complete example", self.html)
        self.assertIn('src="assets/evar-review-walkthrough.gif"', self.html)
        self.assertIn("This 21-second walkthrough", self.html)
        self.assertTrue(self.walkthrough.is_file())
        self.assertTrue(self.walkthrough.read_bytes().startswith((b"GIF87a", b"GIF89a")))

    def test_portal_uses_plain_language_field_help(self) -> None:
        self.assertIn("Can you identify one specific code problem", self.html)
        self.assertIn("Is this problem visible in BEFORE?", self.html)
        self.assertIn("Is this same problem gone in AFTER?", self.html)
        self.assertIn("Find unanswered item", self.html)

    def test_yes_no_questions_use_large_radio_choices(self) -> None:
        self.assertIn('id="eligible" class="field wide question first-question choice-field"', self.html)
        self.assertIn('type="radio" name="eligible" value="true"', self.html)
        self.assertIn('type="radio" name="supported" value="false"', self.html)
        self.assertIn('type="radio" name="unsupported" value="true"', self.html)
        self.assertIn("node.classList.contains('choice-field')", self.html)

    def test_code_snapshots_have_ide_style_highlighting(self) -> None:
        self.assertIn('id="review-lines" class="line-numbers"', self.html)
        self.assertIn('id="merge-lines" class="line-numbers"', self.html)
        self.assertIn('id="review-language" class="language-badge"', self.html)
        self.assertIn("function highlight(code,language)", self.html)
        self.assertIn("function escapeHtml(text)", self.html)
        self.assertIn(
            "renderCode('review',r.review_excerpt,r.language,r.source_comment_line)",
            self.html,
        )
        self.assertIn(".tok-keyword", self.html)
        self.assertIn(".tok-string", self.html)
        self.assertIn(".tok-comment", self.html)

    def test_code_snapshots_focus_on_the_reviewed_lines(self) -> None:
        self.assertIn("function parseExcerpt(excerpt)", self.html)
        self.assertIn("const windowSize=15", self.html)
        self.assertIn("Show full context (${lines.length} lines)", self.html)
        self.assertIn("Show focused 15-line view", self.html)
        self.assertIn("r.source_comment_line", self.html)
        self.assertIn("r.merge_line", self.html)
        self.assertIn(".code-line.anchor-line", self.html)

    def test_portal_reveals_only_relevant_follow_up_fields(self) -> None:
        self.assertIn('id="eligible-fields" class="followup" hidden', self.html)
        self.assertIn(
            'id="ineligible-fields" class="field wide question" hidden',
            self.html,
        )
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
