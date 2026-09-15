# Post-clearance execution checklist

This is the operational handoff for the powered Human PR expansion. Do not begin Stage
1 until `ETHICS_AND_REVIEWER_GOVERNANCE.md` records the institutional determination and
all bracketed reviewer-information fields are complete.

## Stage 1: recruit and pilot

1. Recruit roles using `RECRUITMENT_AND_QUALIFICATION.md`.
2. Assign unrelated pseudonymous IDs to Expert A, Expert B, and the adjudicator.
3. Give every reviewer the completed information sheet and retain acknowledgments only
   in `private/`, which is ignored by Git.
4. Run the frozen 18-item interface pilot with people who will not become final experts
   if their answers are discussed.
5. Record completion time and interface-only feedback. Clarify presentation if needed,
   but do not change labels, families, selection rules, or hypotheses in response to
   pilot answers.
6. Re-freeze study inputs if any interface text or code changes.

## Stage 2: independent annotation

Expert A and Expert B each load the full `annotation_queue_682.jsonl`, work alone, keep
one reviewer ID, and export a completed JSONL file. Validate immediately:

```bash
PYTHONPATH=. python3 scripts/validate_human_pr_annotation_export.py \
  --input private/annotator_a.jsonl \
  --queue benchmarks/human_pr_200/annotation_queue_682.jsonl \
  --report private/annotator_a_validation.json

PYTHONPATH=. python3 scripts/validate_human_pr_annotation_export.py \
  --input private/annotator_b.jsonl \
  --queue benchmarks/human_pr_200/annotation_queue_682.jsonl \
  --report private/annotator_b_validation.json
```

Do not disclose either export until both validations succeed.

## Stage 3: adjudicate

Create the identity-blinded disagreement queue:

```bash
PYTHONPATH=. python3 scripts/adjudicate_human_pr_annotations.py \
  --annotator-a private/annotator_a.jsonl \
  --annotator-b private/annotator_b.jsonl \
  --resolved benchmarks/human_pr_200/resolved_annotations.jsonl \
  --disagreements private/adjudication_queue.jsonl \
  --audit benchmarks/human_pr_200/adjudication_audit.json
```

The adjudicator loads only `private/adjudication_queue.jsonl`. Validate the completed
export against that queue, then repeat the command above with
`--adjudications private/adjudicator.jsonl`. Require `unresolved: 0` in the audit.

## Stage 4: select, render, and audit

```bash
PYTHONPATH=. python3 scripts/select_human_pr_200.py \
  --input benchmarks/human_pr_200/resolved_annotations.jsonl \
  --output benchmarks/human_pr_200/final_300.jsonl \
  --manifest benchmarks/human_pr_200/selection_manifest.json \
  --target 300 --min-repositories 40

PYTHONPATH=. python3 scripts/render_human_pr_200.py \
  --input benchmarks/human_pr_200/final_300.jsonl \
  --output-dir benchmarks/human_pr_200/frozen \
  --audit benchmarks/human_pr_200/render_audit.json

PYTHONPATH=. python3 scripts/audit_human_pr_200_contamination.py
PYTHONPATH=. python3 scripts/freeze_human_pr_200_model_inputs.py
```

Selection or either audit must fail closed rather than reducing the target silently.

## Stage 5: price and execution gate

Record fresh prices and their official source URLs in a private working JSON file using
the schema documented by `scripts/freeze_human_pr_expansion_prices.py`, then freeze it:

```json
{
  "observed_at": "YYYY-MM-DD",
  "sources": ["https://official-pricing-page.example"],
  "prices": [
    {
      "model": "exact-model-slug-from-config",
      "input_usd_per_million_tokens": 0.0,
      "output_usd_per_million_tokens": 0.0
    }
  ]
}
```

Include exactly one row for every configured model. Replace the example values with the
prices actually displayed by the provider on the observation date.

```bash
PYTHONPATH=. python3 scripts/freeze_human_pr_expansion_prices.py \
  --input private/current_model_prices.json
PYTHONPATH=. python3 scripts/preflight_human_pr_expansion.py
```

Do not make a paid model call unless preflight prints `ready_for_paid_runs: true`, the
available budget covers the frozen upper bound, and the study lead explicitly approves
the spend.

## Stage 6: analysis and paper

Run the frozen four-protocol matrix, preserve every failed attempt, run the stability
subset repetitions, and regenerate all tables from indexed results. Report expert
agreement, annotation yield, adjudication rate, per-language and per-family results,
paired uncertainty, reliability, and cost. Replace every prospective statement in the
paper with the observed powered-study result before the final independent review.
