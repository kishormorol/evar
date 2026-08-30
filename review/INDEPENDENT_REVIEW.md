# Independent Methodology Review Packet

EVAR invites a reviewer with no role in benchmark construction, prompt tuning, implementation, or model execution to audit the `v0.2.0` artifact.

## Scope

Please evaluate whether the public evidence supports the paper's claims. A review may be signed or anonymous, but it must disclose any conflict of interest and identify the exact release or commit reviewed.

## Primary questions

1. Do benchmark labels follow from the cited human pull-request comment and the reviewed/merge commit pair?
2. Are source provenance, temporal pairing, repository diversity, label balance, and multi-file context represented accurately?
3. Could ground truth leak into an agent-visible prompt, repository snapshot, task description, or claim?
4. Do result records and transcripts agree on final actionability, verifier status, token usage, and failures?
5. Are FCR, SCR, paired deltas, uncertainty intervals, and denominators calculated correctly?
6. Does the paper clearly distinguish frozen evaluation, development diagnostics, and post-hoc analysis?
7. Are conclusions appropriately bounded by the small holdout and the mixed Human PR 20 result?

## Minimum review procedure

- Verify `benchmarks/human_pr_20/freeze_manifest.json` with `python -m evar.freeze verify`.
- Verify result hashes in `benchmarks/human_pr_20/results_manifest.json`.
- Run `python -m pytest -q`.
- Rebuild `benchmarks/human_pr_20/report.json` with `python scripts/report_human_pr_20.py`.
- Inspect all ten source-comment URLs and at least four temporal case pairs.
- Inspect at least one AR, AR-Text, and EVAR-Hard transcript for each model.
- Compare findings against `benchmarks/human_pr_20/audit_report.json`.

## Response format

Please file a GitHub issue containing:

- reviewer name or `anonymous`;
- conflicts of interest;
- reviewed release/commit;
- checks completed;
- blocking issues, non-blocking issues, and suggested revisions;
- one verdict: `claims supported as written`, `supported with revisions`, or `not supported`.

An issue requesting this review is part of the release record. Until a qualified person posts a completed review, the project describes the review as **requested**, never completed.
