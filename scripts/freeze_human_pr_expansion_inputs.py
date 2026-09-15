from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evar.config import load_config


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = Path("benchmarks/human_pr_200")
CONFIG_DIRS = (
    Path("configs/human_pr_expansion_full"),
    Path("configs/human_pr_expansion_stability"),
)
REQUIRED_METHOD_FILES = (
    BENCHMARK / "ANNOTATION_PROTOCOL.md",
    BENCHMARK / "PREREGISTRATION.md",
    BENCHMARK / "POWER_PLAN.md",
    BENCHMARK / "REVIEWER_HANDOFF.md",
    BENCHMARK / "ETHICS_AND_REVIEWER_GOVERNANCE.md",
    BENCHMARK / "INSTITUTIONAL_DETERMINATION_REQUEST.md",
    BENCHMARK / "REVIEWER_INFORMATION_SHEET.md",
    BENCHMARK / "REVIEWER_ACKNOWLEDGMENT_TEMPLATE.md",
    BENCHMARK / "RECRUITMENT_AND_QUALIFICATION.md",
    BENCHMARK / "POST_CLEARANCE_EXECUTION.md",
    Path("review/human_pr_200.html"),
    Path("review/assets/evar-review-walkthrough.gif"),
    Path("scripts/validate_human_pr_annotation_export.py"),
    Path("scripts/adjudicate_human_pr_annotations.py"),
    Path("scripts/select_human_pr_200.py"),
    Path("scripts/render_human_pr_200.py"),
    Path("scripts/audit_human_pr_200_contamination.py"),
    Path("scripts/freeze_human_pr_200_model_inputs.py"),
    Path("scripts/freeze_human_pr_expansion_prices.py"),
    Path("scripts/preflight_human_pr_expansion.py"),
    Path("scripts/plan_human_pr_200_power.py"),
)


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(root: Path = ROOT) -> dict[str, object]:
    queue_path = root / BENCHMARK / "annotation_queue_682.jsonl"
    candidate_path = root / BENCHMARK / "candidates_682.jsonl"
    queue = _load_jsonl(queue_path)
    candidates = _load_jsonl(candidate_path)
    if len(queue) != 682 or len(candidates) != 682:
        raise ValueError("the powered annotation freeze requires exactly 682 queue and candidate rows")

    queue_ids = [str(row.get("candidate_id", "")) for row in queue]
    candidate_ids = {str(row.get("candidate_id", "")) for row in candidates}
    if len(set(queue_ids)) != 682 or set(queue_ids) != candidate_ids:
        raise ValueError("queue and candidate identifiers must be unique and identical")

    annotation_fields = {
        "annotator_id",
        "claim_family",
        "eligible",
        "exclusion_reason",
        "normalized_claim",
        "supported_at_review",
        "unsupported_at_merge",
    }
    for row in queue:
        annotation = row.get("annotation")
        if not isinstance(annotation, dict) or set(annotation) != annotation_fields:
            raise ValueError(f"{row.get('candidate_id')}: unexpected annotation schema")
        if any(value is not None for value in annotation.values()):
            raise ValueError(f"{row.get('candidate_id')}: frozen queue must not contain decisions")

    files: dict[Path, str] = {
        queue_path: "annotation_queue",
        candidate_path: "candidate_provenance",
    }
    for relative in REQUIRED_METHOD_FILES:
        files[root / relative] = "method"
    configs: list[Path] = []
    for relative_dir in CONFIG_DIRS:
        configs.extend(sorted((root / relative_dir).glob("*.yaml")))
    if len(configs) != 12:
        raise ValueError("expected six full-matrix and six stability configurations")

    models: set[str] = set()
    for config_path in configs:
        config = load_config(config_path)
        if config.model.request_timeout_seconds != 120:
            raise ValueError(f"{config_path}: request timeout must be 120 seconds")
        if config.model.backend == "openrouter":
            if config.model.max_attempts != 2 or config.model.max_total_seconds != 250:
                raise ValueError(f"{config_path}: OpenRouter retry budget differs from preregistration")
        models.add(config.model.model)
        files[config_path] = "model_config"

    frozen_files: dict[str, dict[str, object]] = {}
    for path, category in sorted(files.items(), key=lambda item: item[0].as_posix()):
        if not path.is_file():
            raise FileNotFoundError(path)
        frozen_files[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "category": category,
            "sha256": _sha256(path),
        }

    languages = sorted({str(row.get("language", "unknown")) for row in queue})
    repositories = sorted({str(row.get("repository", "unknown")) for row in queue})
    try:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        source_commit = None

    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "study_status": "blocked_pending_institutional_determination_and_human_exports",
        "benchmark": {
            "candidate_count": len(candidates),
            "queue_count": len(queue),
            "repository_count": len(repositories),
            "languages": languages,
            "target_source_comments": 300,
            "target_temporal_cases": 600,
        },
        "experiment": {
            "confirmatory_model": "gpt-4.1",
            "confirmatory_comparison": (
                "EVAR-BlindGate role-aware soft versus hard actionability"
            ),
            "protocols": ["ar", "ar_text", "evar_hard", "evar_blind_gate"],
            "external_validity_models": sorted(models - {"gpt-4.1"}),
            "request_timeout_seconds": 120,
            "openrouter_max_attempts": 2,
            "openrouter_max_total_seconds": 250,
        },
        "files": frozen_files,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Freeze powered Human PR study inputs by hash.")
    parser.add_argument(
        "--output",
        type=Path,
        default=BENCHMARK / "study_input_freeze_manifest.json",
    )
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = build_manifest(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    print(f"hashed files: {len(manifest['files'])}")


if __name__ == "__main__":
    main()
