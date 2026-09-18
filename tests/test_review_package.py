import importlib.util
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_review_package", ROOT / "scripts" / "make_review_package.py")
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)


class ReviewPackageTest(unittest.TestCase):
    def test_scanner_catches_the_author_and_their_sites(self):
        for text in ("Kishor Morol", "github.com/kishormorol/evar", "/Users/kishormorol/evar", "evar-research.elitelab-ai.chatgpt.site"):
            self.assertIsNotNone(pkg.IDENTIFYING.search(text), text)

    def test_scanner_leaves_ordinary_code_alone(self):
        self.assertIsNone(pkg.IDENTIFYING.search('@app.get("/users/me")'))

    def test_rewrites_match_the_lines_they_are_for(self):
        rules = {path: (pattern, repl) for path, pattern, repl in pkg.REWRITE}
        pattern, repl = rules["LICENSE"]
        self.assertEqual(re.sub(pattern, repl, "Copyright (c) 2026 Some Person"), "Copyright (c) 2026 Anonymous Authors")
        pattern, repl = rules["evar/model_backend.py"]
        self.assertNotIn("kishormorol", re.sub(pattern, repl, '"HTTP-Referer": "https://github.com/kishormorol/evar",'))

    def test_exclusions_cover_directories_and_files(self):
        self.assertTrue(pkg.excluded("site/app/page.tsx"))
        self.assertTrue(pkg.excluded("CITATION.cff"))
        self.assertFalse(pkg.excluded("sitemap.txt"))
        self.assertFalse(pkg.excluded("evar/model_backend.py"))

    def test_the_committed_tree_packages_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "package.zip"
            hits = pkg.build("HEAD", out)
            self.assertEqual(hits, [])
            names = zipfile.ZipFile(out).namelist()
            self.assertIn("evar-review-package/README_REVIEWERS.md", names)
            self.assertFalse(any(n.startswith("evar-review-package/site/") for n in names))
            self.assertNotIn("evar-review-package/CITATION.cff", names)


if __name__ == "__main__":
    unittest.main()
