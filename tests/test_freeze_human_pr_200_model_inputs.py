from __future__ import annotations

import unittest

from scripts.freeze_human_pr_200_model_inputs import validate_cases


def temporal_pair() -> list[dict[str, object]]:
    return [
        {
            "case_id": "case-1",
            "paired_case_id": "case-2",
            "candidate_id": "candidate-1",
            "claim": "The parser accepts an empty name.",
            "ground_truth": "SUPPORTED",
        },
        {
            "case_id": "case-2",
            "paired_case_id": "case-1",
            "candidate_id": "candidate-1",
            "claim": "The parser accepts an empty name.",
            "ground_truth": "UNSUPPORTED",
        },
    ]


class HumanPR200ModelInputFreezeTests(unittest.TestCase):
    def test_accepts_reciprocal_balanced_pair(self) -> None:
        summary = validate_cases(temporal_pair(), expected_cases=2)
        self.assertEqual(summary["source_comment_count"], 1)
        self.assertEqual(summary["label_counts"], {"SUPPORTED": 1, "UNSUPPORTED": 1})

    def test_rejects_changed_claim_and_nonreciprocal_pair(self) -> None:
        rows = temporal_pair()
        rows[1]["claim"] = "A different claim"
        with self.assertRaisesRegex(ValueError, "preserve candidate and claim"):
            validate_cases(rows, expected_cases=2)
        rows = temporal_pair()
        rows[1]["paired_case_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "non-reciprocal"):
            validate_cases(rows, expected_cases=2)


if __name__ == "__main__":
    unittest.main()

