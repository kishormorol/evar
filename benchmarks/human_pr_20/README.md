# Human PR 20

This benchmark contains ten paired findings derived from public human pull-request
review comments across Black, pytest, Rich, Pydantic, and Poetry. Each review thread
produces two cases with the same normalized claim:

- a `SUPPORTED` case at the exact commit reviewed by the commenter;
- an `UNSUPPORTED` case at the exact merge commit after the thread was resolved.

The paired temporal design controls the claim wording and repository while changing the
snapshot. Each case contains a focused target-file excerpt plus a second changed-file
excerpt when available. Comment URL, author, original body, path, line, PR, and commit
provenance remain in `cases.jsonl`; none of the scoring fields enter model prompts.

The ten source comments are from accounts not marked as bots by GitHub. Normalized
claims preserve the technical substance of each comment while making pronouns and
line-local references self-contained.

Regenerate the corpus from GitHub's public API and raw commit content:

```bash
python benchmarks/human_pr_20/generate.py
```

This evaluation must be run only with the evaluator and prompts frozen at commit
`0ce6be8` or an explicitly recorded descendant that changes only benchmark-generation
and release metadata.
