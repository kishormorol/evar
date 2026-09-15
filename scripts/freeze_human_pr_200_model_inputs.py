from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from evar.config import load_config


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = Path("benchmarks/human_pr_200")
CONFIG_DIRS = (
    Path("configs/human_pr_expansion_full"),
    Path("configs/human_pr_expansion_stability"),
)


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_cases(rows: list[dict[str, object]], *, expected_cases: int = 600) -> dict[str, object]:
    if len(rows) != expected_cases:
        raise ValueError(f"expected {expected_cases} frozen cases; found {len(rows)}")
    by_id = {str(row.get("case_id", "")): row for row in rows}
    if "" in by_id or len(by_id) != len(rows):
        raise ValueError("case identifiers must be non-empty and unique")
    labels = Counter(str(row.get("ground_truth", "")) for row in rows)
    if labels != {"SUPPORTED": expected_cases // 2, "UNSUPPORTED": expected_cases // 2}:
        raise ValueError(f"expected a balanced temporal benchmark; found {dict(labels)}")
    candidate_counts = Counter(str(row.get("candidate_id", "")) for row in rows)
    if "" in candidate_counts or any(count != 2 for count in candidate_counts.values()):
        raise ValueError("every source candidate must produce exactly two cases")
    for case_id, row in by_id.items():
        paired_id = str(row.get("paired_case_id", ""))
        paired = by_id.get(paired_id)
        if paired is None or str(paired.get("paired_case_id", "")) != case_id:
            raise ValueError(f"{case_id}: paired_case_id is missing or non-reciprocal")
        if paired.get("candidate_id") != row.get("candidate_id") or paired.get("claim") != row.get("claim"):
            raise ValueError(f"{case_id}: temporal pair must preserve candidate and claim")
        if paired.get("ground_truth") == row.get("ground_truth"):
            raise ValueError(f"{case_id}: temporal pair must have opposite labels")
    return {
        "case_count": len(rows),
        "source_comment_count": len(candidate_counts),
        "label_counts": dict(labels),
    }


def build_manifest(root: Path = ROOT) -> dict[str, object]:
    cases_path = root / BENCHMARK / "frozen/cases.jsonl"
    selection_path = root / BENCHMARK / "final_300.jsonl"
    selection_manifest_path = root / BENCHMARK / "selection_manifest.json"
    contamination_path = root / BENCHMARK / "contamination_audit.json"
    summary = validate_cases(_load_jsonl(cases_path))

    contamination = json.loads(contamination_path.read_text(encoding="utf-8"))
    if contamination.get("passed") is not True:
        raise ValueError("contamination audit did not pass")
    if contamination.get("selected_sha256") != _sha256(selection_path):
        raise ValueError("contamination audit does not match final_300.jsonl")

    configs = [path for directory in CONFIG_DIRS for path in sorted((root / directory).glob("*.yaml"))]
    if len(configs) != 12:
        raise ValueError("expected six full-matrix and six stability configurations")
    models = sorted({load_config(path).model.model for path in configs})
    if len(models) != 6:
        raise ValueError(f"expected six distinct models; found {models}")

    categorized: dict[Path, str] = {
        cases_path: "cases",
        selection_path: "selection",
        selection_manifest_path: "selection_manifest",
        contamination_path: "contamination_audit",
    }
    categorized.update(
        {path: "snapshot" for path in sorted((root / BENCHMARK / "frozen/repos").rglob("*")) if path.is_file()}
    )
    categorized.update({path: "prompt" for path in sorted((root / "prompts").glob("*.txt"))})
    categorized.update({path: "config" for path in configs})
    categorized.update({path: "evaluator" for path in sorted((root / "evar").rglob("*.py"))})

    files: dict[str, dict[str, object]] = {}
    for path, category in sorted(categorized.items(), key=lambda item: item[0].as_posix()):
        if not path.is_file():
            raise FileNotFoundError(path)
        files[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "category": category,
            "sha256": _sha256(path),
        }
    try:
        source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        source_commit = None
    return {
        "schema_version": 1,
        "status": "frozen",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "benchmark": summary,
        "models": models,
        "protocols": ["ar", "ar_text", "evar_hard", "evar_blind_gate"],
        "files": files,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Freeze final Human PR 200 model inputs.")
    parser.add_argument("--output", type=Path, default=BENCHMARK / "model_input_freeze_manifest.json")
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = build_manifest(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    print(f"hashed files: {len(manifest['files'])}")


if __name__ == "__main__":
    main()

