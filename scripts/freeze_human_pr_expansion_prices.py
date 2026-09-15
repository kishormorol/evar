from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from evar.config import load_config


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = Path("benchmarks/human_pr_200")
CONFIG_DIR = Path("configs/human_pr_expansion_full")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_price_freeze(input_path: Path, config_paths: list[Path]) -> dict[str, object]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    observed_at = source.get("observed_at")
    if not isinstance(observed_at, str):
        raise ValueError("observed_at must be an ISO date")
    try:
        date.fromisoformat(observed_at)
    except ValueError as error:
        raise ValueError("observed_at must be an ISO date") from error
    sources = source.get("sources")
    if not isinstance(sources, list) or not sources or any(
        not isinstance(item, str) or not item.startswith("https://") for item in sources
    ):
        raise ValueError("sources must contain at least one HTTPS pricing URL")
    rows = source.get("prices")
    if not isinstance(rows, list):
        raise ValueError("prices must be a list")
    by_model: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("model"), str):
            raise ValueError("every price row requires a model")
        model = str(row["model"])
        if model in by_model:
            raise ValueError(f"duplicate price for {model}")
        for field in ("input_usd_per_million_tokens", "output_usd_per_million_tokens"):
            value = row.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{model}: {field} must be a nonnegative number")
        by_model[model] = row

    configured = sorted({load_config(path).model.model for path in config_paths})
    if set(by_model) != set(configured):
        missing = sorted(set(configured) - set(by_model))
        unexpected = sorted(set(by_model) - set(configured))
        raise ValueError(f"price models differ from configs; missing={missing}, unexpected={unexpected}")
    return {
        "schema_version": 1,
        "status": "frozen",
        "observed_at": observed_at,
        "sources": sources,
        "models": configured,
        "prices": [by_model[model] for model in configured],
        "input": input_path.as_posix(),
        "input_sha256": _sha256(input_path),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate and freeze Human PR expansion prices.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=BENCHMARK / "price_freeze.json")
    args = parser.parse_args(argv)
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    output = args.output if args.output.is_absolute() else ROOT / args.output
    configs = sorted((ROOT / CONFIG_DIR).glob("*.yaml"))
    freeze = build_price_freeze(input_path, configs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()

