from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOS = ROOT / "repos"
CASES = ROOT / "cases.jsonl"


def main() -> None:
    REPOS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for family_index, family in enumerate(FAMILIES, start=1):
        for variant in range(1, 6):
            supported_id = (family_index - 1) * 10 + (variant * 2 - 1)
            unsupported_id = supported_id + 1
            rows.append(family["supported"](supported_id, variant))
            rows.append(family["unsupported"](unsupported_id, variant))

    with CASES.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _case(
    number: int,
    *,
    filename: str,
    source: str,
    task: str,
    claim: str,
    ground_truth: str,
    ground_truth_evidence: str,
    claim_family: str,
) -> dict[str, object]:
    case_id = f"manual50_{number:03d}_{claim_family}_{ground_truth.lower()}"
    repo = REPOS / f"case_{number:03d}"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(source, encoding="utf-8")
    return {
        "case_id": case_id,
        "repo_path": str(repo.relative_to(ROOT.parent.parent)).replace("\\", "/"),
        "task_description": task,
        "claim": claim,
        "ground_truth": ground_truth,
        "ground_truth_evidence": ground_truth_evidence,
        "validation_command": ["python", "-m", "unittest", "discover"],
        "claim_family": claim_family,
    }


def behavior_supported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="calculator.py",
        source=f"def divide_{variant}(a, b):\n    return a / b\n",
        task=f"Review divide_{variant} zero-division behavior.",
        claim=f"divide_{variant}(10, 0) raises ZeroDivisionError.",
        ground_truth="SUPPORTED",
        ground_truth_evidence=f"calculator.py implements divide_{variant} as a / b, so b == 0 raises ZeroDivisionError.",
        claim_family="behavior_inversion",
    )


def behavior_unsupported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="calculator.py",
        source=f"def divide_{variant}(a, b):\n    if b == 0:\n        return None\n    return a / b\n",
        task=f"Review divide_{variant} zero-division behavior.",
        claim=f"divide_{variant}(10, 0) raises ZeroDivisionError.",
        ground_truth="UNSUPPORTED",
        ground_truth_evidence=f"calculator.py returns None when b == 0 before division.",
        claim_family="behavior_inversion",
    )


def guard_supported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="payments.py",
        source=f"def send_charge_{variant}(amount):\n    return {{'charged': amount}}\n\n\ndef charge_{variant}(amount):\n    return send_charge_{variant}(amount)\n",
        task=f"Review charge_{variant} amount validation.",
        claim=f"charge_{variant}(amount) is missing a guard against negative amounts.",
        ground_truth="SUPPORTED",
        ground_truth_evidence=f"charge_{variant} sends the amount without checking amount < 0.",
        claim_family="missing_guard",
    )


def guard_unsupported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="payments.py",
        source=f"def send_charge_{variant}(amount):\n    return {{'charged': amount}}\n\n\ndef charge_{variant}(amount):\n    if amount < 0:\n        raise ValueError('amount must be non-negative')\n    return send_charge_{variant}(amount)\n",
        task=f"Review charge_{variant} amount validation.",
        claim=f"charge_{variant}(amount) is missing a guard against negative amounts.",
        ground_truth="UNSUPPORTED",
        ground_truth_evidence=f"charge_{variant} raises ValueError when amount < 0 before sending.",
        claim_family="missing_guard",
    )


def call_supported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="emails.py",
        source=f"def build_welcome_email_{variant}(user):\n    return f'Welcome {{user}}'\n\n\ndef build_password_reset_email_{variant}(user):\n    return f'Reset password for {{user}}'\n\n\ndef send(message):\n    return {{'sent': message}}\n\n\ndef send_welcome_email_{variant}(user):\n    return send(build_password_reset_email_{variant}(user))\n",
        task=f"Review send_welcome_email_{variant} call relationship.",
        claim=f"send_welcome_email_{variant}(user) calls build_password_reset_email_{variant}(user).",
        ground_truth="SUPPORTED",
        ground_truth_evidence=f"send_welcome_email_{variant} returns send(build_password_reset_email_{variant}(user)).",
        claim_family="incorrect_call_relationship",
    )


def call_unsupported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="emails.py",
        source=f"def build_welcome_email_{variant}(user):\n    return f'Welcome {{user}}'\n\n\ndef build_password_reset_email_{variant}(user):\n    return f'Reset password for {{user}}'\n\n\ndef send(message):\n    return {{'sent': message}}\n\n\ndef send_welcome_email_{variant}(user):\n    return send(build_welcome_email_{variant}(user))\n",
        task=f"Review send_welcome_email_{variant} call relationship.",
        claim=f"send_welcome_email_{variant}(user) calls build_password_reset_email_{variant}(user).",
        ground_truth="UNSUPPORTED",
        ground_truth_evidence=f"send_welcome_email_{variant} calls build_welcome_email_{variant}, not build_password_reset_email_{variant}.",
        claim_family="incorrect_call_relationship",
    )


def causal_supported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="records.py",
        source=f"def merge_records_{variant}(records):\n    merged = []\n    for record in records:\n        merged.append(record)\n        merged.append(record)\n    return merged\n",
        task=f"Review duplicate rows from merge_records_{variant}.",
        claim=f"Duplicate rows are caused by merge_records_{variant} appending the same record twice.",
        ground_truth="SUPPORTED",
        ground_truth_evidence=f"merge_records_{variant} appends each record twice inside the loop.",
        claim_family="causal_mislocalization",
    )


def causal_unsupported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="records.py",
        source=f"def merge_records_{variant}(records):\n    merged = []\n    for record in records:\n        merged.append(record)\n    return merged\n",
        task=f"Review duplicate rows from merge_records_{variant}.",
        claim=f"Duplicate rows are caused by merge_records_{variant} appending the same record twice.",
        ground_truth="UNSUPPORTED",
        ground_truth_evidence=f"merge_records_{variant} appends each record once; duplicates must come from input.",
        claim_family="causal_mislocalization",
    )


def stale_supported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="cache.py",
        source=f"CACHED_VALUE_{variant} = 'old'\n\n\ndef compute_value_{variant}():\n    return 'new'\n\n\ndef refresh_cache_{variant}():\n    return CACHED_VALUE_{variant}\n",
        task=f"Review refresh_cache_{variant} invalidation behavior.",
        claim=f"refresh_cache_{variant} still reads stale values because it returns CACHED_VALUE_{variant} without recomputing.",
        ground_truth="SUPPORTED",
        ground_truth_evidence=f"refresh_cache_{variant} returns CACHED_VALUE_{variant} directly and never calls compute_value_{variant}.",
        claim_family="stale_evidence",
    )


def stale_unsupported(number: int, variant: int) -> dict[str, object]:
    return _case(
        number,
        filename="cache.py",
        source=f"CACHED_VALUE_{variant} = 'old'\n\n\ndef compute_value_{variant}():\n    return 'new'\n\n\ndef refresh_cache_{variant}():\n    return compute_value_{variant}()\n",
        task=f"Review refresh_cache_{variant} invalidation behavior.",
        claim=f"refresh_cache_{variant} still reads stale values because it returns CACHED_VALUE_{variant} without recomputing.",
        ground_truth="UNSUPPORTED",
        ground_truth_evidence=f"refresh_cache_{variant} calls compute_value_{variant} and returns a fresh value.",
        claim_family="stale_evidence",
    )


FAMILIES = [
    {"supported": behavior_supported, "unsupported": behavior_unsupported},
    {"supported": guard_supported, "unsupported": guard_unsupported},
    {"supported": call_supported, "unsupported": call_unsupported},
    {"supported": causal_supported, "unsupported": causal_unsupported},
    {"supported": stale_supported, "unsupported": stale_unsupported},
]


if __name__ == "__main__":
    main()
