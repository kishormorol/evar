from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.freeze_human_pr_expansion_prices import build_price_freeze


class HumanPRExpansionPriceFreezeTests(unittest.TestCase):
    def _write_config(self, path: Path, model: str) -> None:
        path.write_text(
            "\n".join(
                [
                    "model:",
                    "  backend: openai",
                    f"  model: {model}",
                    "  temperature: 0.0",
                    "  max_output_tokens: 100",
                    "protocol:",
                    "  critic_rounds: 1",
                    "  verifier_timeout_seconds: 10",
                    "experiment:",
                    "  seed: 1",
                    "  repetitions: 1",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _write_prices(self, path: Path, models: list[str]) -> None:
        path.write_text(
            json.dumps(
                {
                    "observed_at": "2026-09-02",
                    "sources": ["https://example.com/official-prices"],
                    "prices": [
                        {
                            "model": model,
                            "input_usd_per_million_tokens": 1.0,
                            "output_usd_per_million_tokens": 2.0,
                        }
                        for model in models
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_freezes_exact_configured_models(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, prices = root / "model.yaml", root / "prices.json"
            self._write_config(config, "test-model")
            self._write_prices(prices, ["test-model"])
            freeze = build_price_freeze(prices, [config])
        self.assertEqual(freeze["status"], "frozen")
        self.assertEqual(freeze["models"], ["test-model"])

    def test_rejects_missing_or_negative_prices(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, prices = root / "model.yaml", root / "prices.json"
            self._write_config(config, "test-model")
            self._write_prices(prices, ["another-model"])
            with self.assertRaisesRegex(ValueError, "models differ"):
                build_price_freeze(prices, [config])
            self._write_prices(prices, ["test-model"])
            payload = json.loads(prices.read_text())
            payload["prices"][0]["input_usd_per_million_tokens"] = -1
            prices.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonnegative"):
                build_price_freeze(prices, [config])


if __name__ == "__main__":
    unittest.main()

