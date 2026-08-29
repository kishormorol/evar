from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evar.freeze import build_manifest, verify_manifest, write_manifest


class FreezeManifestTests(unittest.TestCase):
    def test_manifest_covers_and_verifies_frozen_inputs(self) -> None:
        configs = sorted(Path("configs/frozen_external_pr_50").glob("*.yaml"))
        manifest = build_manifest(Path("."), Path("benchmarks/external_pr_50/cases.jsonl"), configs)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            write_manifest(manifest, path)
            errors = verify_manifest(Path("."), path)

        self.assertEqual(errors, [])
        self.assertEqual(manifest["benchmark"]["case_count"], 50)
        self.assertEqual(manifest["benchmark"]["label_counts"], {"SUPPORTED": 25, "UNSUPPORTED": 25})
        categories = {details["category"] for details in manifest["files"].values()}
        self.assertEqual(categories, {"cases", "config", "evaluator", "prompt", "snapshot"})
        self.assertEqual(sum(d["category"] == "snapshot" for d in manifest["files"].values()), 50)

    def test_verify_reports_tampered_hash(self) -> None:
        configs = sorted(Path("configs/frozen_external_pr_50").glob("*.yaml"))
        manifest = build_manifest(Path("."), Path("benchmarks/external_pr_50/cases.jsonl"), configs)
        manifest["files"]["prompts/reviewer_ar_v1.txt"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = verify_manifest(Path("."), path)

        self.assertIn("hash mismatch: prompts/reviewer_ar_v1.txt", errors)


if __name__ == "__main__":
    unittest.main()
