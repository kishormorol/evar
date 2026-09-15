from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from evar.model_backend import ModelBackend, OpenAIResponsesBackend


ANNOTATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "eligible": {"type": "boolean"},
        "normalized_claim": {"type": ["string", "null"]},
        "claim_family": {
            "type": ["string", "null"],
            "enum": [
                "behavior_inversion",
                "missing_guard",
                "incorrect_call_relationship",
                "causal_mislocalization",
                "stale_evidence",
                None,
            ],
        },
        "supported_at_review": {"type": ["boolean", "null"]},
        "unsupported_at_merge": {"type": ["boolean", "null"]},
        "rationale": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "eligible",
        "normalized_claim",
        "claim_family",
        "supported_at_review",
        "unsupported_at_merge",
        "rationale",
        "confidence",
    ],
}

SYSTEM_PROMPT = """You are an advisory benchmark annotator for EVAR. Inspect one public human pull-request review comment and two exact file excerpts: the reviewed snapshot and the later merged snapshot. Decide whether the comment expresses a self-contained, technically checkable claim. If eligible, rewrite it as a short declarative claim and classify it into one of the five allowed families. Then decide whether that claim is true in the reviewed excerpt and false in the merged excerpt. Do not assume that a code change proves the comment's claim. Reject subjective style-only comments, claims needing unavailable systems, and claims that are not temporally resolved. Your output is advisory; do not mention or invent benchmark ground-truth labels. Return only the requested JSON object."""


def user_prompt(row: dict[str, object]) -> str:
    return (
        f"Language: {row['language']}\n"
        f"Repository: {row['source_repository']}\n"
        f"Pull request: {row['source_pull_request']}\n"
        f"Comment body:\n{row['source_comment_body']}\n\n"
        f"Target path: {row['source_comment_path']}:{row['source_comment_line']}\n"
        f"Reviewed snapshot ({row['review_commit']}):\n{row['review_excerpt']}\n\n"
        f"Merged snapshot ({row['merge_commit']}):\n{row['merge_excerpt']}\n"
    )


def annotate(
    rows: list[dict[str, object]],
    *,
    backend: ModelBackend,
    output: Path,
    max_attempts_per_candidate: int = 4,
    retry_delay_seconds: float = 5.0,
    inter_request_delay_seconds: float = 0.0,
) -> None:
    if max_attempts_per_candidate < 1:
        raise ValueError("max_attempts_per_candidate must be positive")
    if retry_delay_seconds < 0 or inter_request_delay_seconds < 0:
        raise ValueError("annotation delays must be nonnegative")

    successful_records: dict[str, dict[str, object]] = {}
    existing_record_count = 0
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_record_count += 1
                record = json.loads(line)
                if record.get("status") == "ok":
                    successful_records.setdefault(str(record["candidate_id"]), record)
    output.parent.mkdir(parents=True, exist_ok=True)
    if existing_record_count != len(successful_records):
        clean_output = "".join(
            json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
            for record in successful_records.values()
        )
        output.write_text(clean_output, encoding="utf-8")
    completed = set(successful_records)
    prompt_hash = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()
    with output.open("a", encoding="utf-8") as handle:
        for index, row in enumerate(rows, start=1):
            candidate_id = str(row["candidate_id"])
            if candidate_id in completed:
                continue
            started = time.perf_counter()
            status = "ok"
            error: str | None = None
            response = None
            parsed = None
            for attempt in range(max_attempts_per_candidate):
                try:
                    response = backend.generate(
                        SYSTEM_PROMPT,
                        user_prompt(row),
                        response_schema=ANNOTATION_SCHEMA,
                    )
                    parsed = response.parsed_output
                    if not isinstance(parsed, dict):
                        raise ValueError("LLM returned no parsed annotation object")
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code != 429 or attempt + 1 >= max_attempts_per_candidate:
                        status = "failed"
                        error = f"{type(exc).__name__}: {exc}"
                        break
                    delay = min(30.0, retry_delay_seconds * (2**attempt))
                    print(
                        f"{index}/{len(rows)} {candidate_id} rate_limited; retrying in {delay:g}s",
                        flush=True,
                    )
                    time.sleep(delay)
                except Exception as exc:  # preserve non-rate-limit failures explicitly
                    status = "failed"
                    error = f"{type(exc).__name__}: {exc}"
                    break
            record = {
                "candidate_id": candidate_id,
                "status": status,
                "model": backend.model_name,
                "prompt_sha256": prompt_hash,
                "annotation": parsed,
                "rationale": parsed.get("rationale") if isinstance(parsed, dict) else None,
                "confidence": parsed.get("confidence") if isinstance(parsed, dict) else None,
                "error": error,
                "input_tokens": response.input_tokens if response else None,
                "output_tokens": response.output_tokens if response else None,
                "latency_seconds": response.latency_seconds if response else time.perf_counter() - started,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"{index}/{len(rows)} {candidate_id} {status}", flush=True)
            if inter_request_delay_seconds:
                time.sleep(inter_request_delay_seconds)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run one advisory LLM annotation pass over Human PR candidates.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--max-output-tokens", type=int, default=500)
    parser.add_argument("--max-attempts-per-candidate", type=int, default=4)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    parser.add_argument("--inter-request-delay-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    backend = OpenAIResponsesBackend(
        model_name=args.model,
        temperature=None,
        max_output_tokens=args.max_output_tokens,
        reasoning_effort="none",
    )
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    annotate(
        rows,
        backend=backend,
        output=args.output,
        max_attempts_per_candidate=args.max_attempts_per_candidate,
        retry_delay_seconds=args.retry_delay_seconds,
        inter_request_delay_seconds=args.inter_request_delay_seconds,
    )


if __name__ == "__main__":
    main()
