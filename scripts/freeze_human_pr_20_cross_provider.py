from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evar.benchmark.loader import load_jsonl_cases
from evar.config import load_config


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks/human_pr_20"
CONFIG_DIR = ROOT / "configs/cross_provider_human_pr_20"
OUTPUT = BENCHMARK / "cross_provider_freeze_manifest.json"


def main() -> None:
    cases_path = BENCHMARK / "cases.jsonl"
    configs = sorted(CONFIG_DIR.glob("*.yaml"))
    categorized: dict[Path, str] = {cases_path: "cases"}
    categorized.update({path: "snapshot" for path in sorted((BENCHMARK / "repos").rglob("*")) if path.is_file()})
    categorized.update({path: "prompt" for path in sorted((ROOT / "prompts").glob("*.txt"))})
    categorized.update({path: "config" for path in configs})
    categorized.update({path: "evaluator" for path in sorted((ROOT / "evar").rglob("*.py"))})

    files: dict[str, dict[str, object]] = {}
    for path, category in sorted(categorized.items(), key=lambda item: str(item[0])):
        if not path.is_file():
            raise FileNotFoundError(path)
        files[path.relative_to(ROOT).as_posix()] = {
            "bytes": path.stat().st_size,
            "category": category,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    cases = load_jsonl_cases(cases_path)
    model_configs = [load_config(path) for path in configs]
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evaluator_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "benchmark": {
            "name": "human_pr_20",
            "cases": len(cases),
            "supported": sum(case.ground_truth.value == "SUPPORTED" for case in cases),
            "unsupported": sum(case.ground_truth.value == "UNSUPPORTED" for case in cases),
        },
        "experiment": {
            "backend": "openrouter",
            "endpoint": "https://openrouter.ai/api/v1/chat/completions",
            "models": [config.model.model for config in model_configs],
            "protocols": ["ar", "ar_text", "evar_hard"],
            "reasoning_effort": "low",
            "temperature": None,
            "max_output_tokens": 1200,
            "seed_label": 53,
            "attempted_decisions": len(cases) * len(configs) * 3,
            "provider_require_parameters": True,
        },
        "method_sources": [
            "https://openrouter.ai/docs/quickstart",
            "https://openrouter.ai/docs/guides/features/structured-outputs",
            "https://openrouter.ai/api/v1/models",
        ],
        "files": files,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))
    print(f"hashed files: {len(files)}")


if __name__ == "__main__":
    main()
