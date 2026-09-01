# Human PR reviewer handoff

The annotation portal is ready for a short workflow pilot and then two independent
expert passes. Human decisions are required: model annotations cannot be substituted
for either expert.

## Roles

- Pilot reviewers test whether the interface and instructions are understandable.
  Their labels are training data, not benchmark ground truth.
- Expert A and Expert B independently label the complete 682-candidate queue. They
  must not see each other's answers or advisory model output.
- A third person adjudicates only disagreements and must use a different identifier.

Pilot reviewers should not become final experts if pilot answers were discussed or
used to revise the interface. This keeps the final passes independent of the pilot.

## Run the 18-item pilot

1. Serve the repository and open `http://localhost:4180/review/human_pr_200.html`.
2. Enter a stable private reviewer ID.
3. Under **More options**, load `benchmarks/human_pr_200/pilot_queue_18.jsonl`.
4. Complete all 18 items independently and export the finished review.
5. Record completion time and list any question, category, or code view that was
   unclear. Do not change claim families, eligibility rules, or selection criteria
   based on desired labels.
6. Validate the export:

```bash
PYTHONPATH=. python3 scripts/validate_human_pr_annotation_export.py \
  --input private/pilot_reviewer_a.jsonl \
  --queue benchmarks/human_pr_200/pilot_queue_18.jsonl \
  --report private/pilot_reviewer_a_validation.json
```

The pilot is balanced across the six languages: three candidates per language from
18 different repositories. Its frozen provenance is in
`pilot_queue_18_manifest.json`.

## Run the two final expert passes

Each expert opens a fresh browser profile or uses a separate machine, loads the
default `annotation_queue_682.jsonl`, and works alone. Each keeps one reviewer ID for
the whole export. Do not exchange drafts or discuss individual candidates until both
exports have passed validation.

Validate both exports separately:

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

Validation fails if an answer is incomplete, a reviewer ID changes, a claim family is
not allowed, a candidate is missing or added, or source evidence differs from the
frozen queue. The report records hashes for the queue and export.

## Adjudicate and freeze

After both expert exports validate, run the adjudication command in `README.md`. Give
the resulting identity-blinded disagreement queue to the third adjudicator, validate
that export against the disagreement queue, and rerun adjudication with
`--adjudications`. Then select 300 resolved eligible comments and render the 600 paired
benchmark cases. Paid model runs and paper results remain blocked until those steps
finish successfully.
