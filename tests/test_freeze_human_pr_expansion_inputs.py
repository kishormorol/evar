from __future__ import annotations

from scripts.freeze_human_pr_expansion_inputs import build_manifest


def test_powered_human_study_inputs_are_complete_and_label_free() -> None:
    manifest = build_manifest()

    assert manifest["study_status"].startswith("blocked_pending")
    assert manifest["benchmark"]["candidate_count"] == 682
    assert manifest["benchmark"]["queue_count"] == 682
    assert manifest["benchmark"]["repository_count"] == 63
    assert manifest["benchmark"]["target_temporal_cases"] == 600
    assert manifest["experiment"]["request_timeout_seconds"] == 120
    assert manifest["experiment"]["protocols"] == [
        "ar",
        "ar_text",
        "evar_hard",
        "evar_blind_gate",
    ]
    assert len(manifest["experiment"]["external_validity_models"]) == 5
    assert not any("llm_annotations" in path for path in manifest["files"])
    for required in (
        "benchmarks/human_pr_200/INSTITUTIONAL_DETERMINATION_REQUEST.md",
        "benchmarks/human_pr_200/REVIEWER_INFORMATION_SHEET.md",
        "benchmarks/human_pr_200/REVIEWER_ACKNOWLEDGMENT_TEMPLATE.md",
    ):
        assert required in manifest["files"]
