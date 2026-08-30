from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from evar.benchmark.loader import load_jsonl_cases


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "human_pr_20"
CASES_PATH = BENCHMARK / "cases.jsonl"


class HumanPR20FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines()]
        cls.cases = load_jsonl_cases(CASES_PATH)

    def test_fixture_is_balanced_and_loadable(self) -> None:
        self.assertEqual(len(self.cases), 20)
        self.assertEqual(Counter(row["ground_truth"] for row in self.raw), {"SUPPORTED": 10, "UNSUPPORTED": 10})

    def test_fixture_uses_ten_human_comments_from_five_new_repositories(self) -> None:
        urls = {row["source_comment_url"] for row in self.raw}
        repositories = {row["source_repository"] for row in self.raw}
        authors = {row["source_comment_author"] for row in self.raw}

        self.assertEqual(len(urls), 10)
        self.assertEqual(len(repositories), 5)
        self.assertFalse(any(author.endswith("[bot]") for author in authors))
        self.assertTrue({"cobaltt7", "bluetech", "nicoddemus", "willmcgugan", "Viicos", "Sanjays2402"} <= authors)

    def test_each_comment_forms_a_temporal_pair_with_changed_target_context(self) -> None:
        by_url: dict[str, list[dict[str, object]]] = {}
        for row in self.raw:
            by_url.setdefault(str(row["source_comment_url"]), []).append(row)

        for rows in by_url.values():
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["ground_truth"] for row in rows}, {"SUPPORTED", "UNSUPPORTED"})
            self.assertEqual(len({row["claim"] for row in rows}), 1)
            self.assertEqual({row["snapshot_kind"] for row in rows}, {"reviewed", "merged"})
            target_texts = []
            for row in rows:
                target = ROOT / str(row["repo_path"]) / str(row["target_context_file"])
                body = "\n".join(target.read_text(encoding="utf-8").splitlines()[4:])
                target_texts.append(body)
            self.assertNotEqual(target_texts[0], target_texts[1])

    def test_context_is_focused_multifile_and_contains_no_labels(self) -> None:
        companion_pairs = 0
        for row in self.raw:
            repo = ROOT / str(row["repo_path"])
            files = [path for path in repo.rglob("*") if path.is_file()]
            rendered = "\n".join(path.read_text(encoding="utf-8") for path in files)
            self.assertLess(len(rendered.encode("utf-8")), 30_000)
            self.assertNotIn("ground_truth", rendered)
            self.assertNotIn("SUPPORTED", rendered)
            self.assertNotIn("UNSUPPORTED", rendered)
            if row["companion_context_file"] is not None:
                companion_pairs += 1
        self.assertGreaterEqual(companion_pairs, 16)

    def test_provenance_is_complete(self) -> None:
        for row in self.raw:
            self.assertTrue(str(row["source_comment_url"]).startswith("https://github.com/"))
            self.assertEqual(len(str(row["source_commit"])), 40)
            self.assertTrue(str(row["source_comment_body"]).strip())
            self.assertGreater(int(row["source_comment_line"]), 0)


if __name__ == "__main__":
    unittest.main()
