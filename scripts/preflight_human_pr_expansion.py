from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _jsonl_count(path: Path) -> int | None:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def check_readiness(root: Path = ROOT) -> dict[str, object]:
    benchmark = root / "benchmarks/human_pr_200"
    blockers: list[dict[str, str]] = []

    ethics = benchmark / "ETHICS_AND_REVIEWER_GOVERNANCE.md"
    if not ethics.is_file() or "- Status: **pending**" in ethics.read_text(encoding="utf-8"):
        blockers.append(
            {
                "code": "ETHICS_DETERMINATION_PENDING",
                "required_action": "Record the lead institution's determination before final annotation.",
            }
        )

    resolved = benchmark / "resolved_annotations.jsonl"
    if _jsonl_count(resolved) is None:
        blockers.append(
            {
                "code": "HUMAN_EXPORTS_MISSING",
                "required_action": f"Create and validate {resolved.relative_to(root)}.",
            }
        )

    selection = benchmark / "final_300.jsonl"
    if _jsonl_count(selection) != 300:
        blockers.append(
            {
                "code": "SELECTION_MISSING",
                "required_action": f"Create a validated 300-row {selection.relative_to(root)}.",
            }
        )

    cases = benchmark / "frozen/cases.jsonl"
    if _jsonl_count(cases) != 600:
        blockers.append(
            {
                "code": "FROZEN_CASES_MISSING",
                "required_action": f"Create a validated 600-row {cases.relative_to(root)}.",
            }
        )

    contamination_path = benchmark / "contamination_audit.json"
    contamination = _load_json(contamination_path)
    if (
        contamination is None
        or contamination.get("passed") is not True
        or contamination.get("selected_sha256") != _sha256(selection)
    ):
        blockers.append(
            {
                "code": "CONTAMINATION_AUDIT_MISSING",
                "required_action": f"Create a passing audit for the exact {selection.relative_to(root)}.",
            }
        )

    model_freeze_path = benchmark / "model_input_freeze_manifest.json"
    model_freeze = _load_json(model_freeze_path)
    frozen_cases = (
        model_freeze.get("files", {}).get("benchmarks/human_pr_200/frozen/cases.jsonl", {})
        if isinstance(model_freeze, dict) and isinstance(model_freeze.get("files"), dict)
        else {}
    )
    if (
        model_freeze is None
        or model_freeze.get("status") != "frozen"
        or not isinstance(frozen_cases, dict)
        or frozen_cases.get("sha256") != _sha256(cases)
    ):
        blockers.append(
            {
                "code": "MODEL_INPUT_FREEZE_MISSING",
                "required_action": f"Freeze the exact final cases in {model_freeze_path.relative_to(root)}.",
            }
        )

    price_path = benchmark / "price_freeze.json"
    price_freeze = _load_json(price_path)
    frozen_models = set(model_freeze.get("models", [])) if isinstance(model_freeze, dict) else set()
    priced_models = set(price_freeze.get("models", [])) if isinstance(price_freeze, dict) else set()
    if (
        price_freeze is None
        or price_freeze.get("status") != "frozen"
        or not frozen_models
        or priced_models != frozen_models
    ):
        blockers.append(
            {
                "code": "PRICE_FREEZE_MISSING",
                "required_action": f"Freeze current prices for every model in {price_path.relative_to(root)}.",
            }
        )

    input_manifest = benchmark / "study_input_freeze_manifest.json"
    cost_projection = benchmark / "cost_projection.json"
    for code, path in (
        ("STUDY_INPUT_FREEZE_MISSING", input_manifest),
        ("COST_PROJECTION_MISSING", cost_projection),
    ):
        if not path.is_file():
            blockers.append(
                {"code": code, "required_action": f"Generate {path.relative_to(root)}."}
            )

    return {
        "schema_version": 1,
        "ready_for_paid_runs": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "required_protocols": ["ar", "ar_text", "evar_hard", "evar_blind_gate"],
        "note": "This preflight never treats advisory LLM annotations as human labels.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check powered Human PR readiness.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("benchmarks/human_pr_200/readiness_report.json"),
    )
    args = parser.parse_args(argv)
    report = check_readiness(ROOT)
    output = args.report if args.report.is_absolute() else ROOT / args.report
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ready_for_paid_runs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
