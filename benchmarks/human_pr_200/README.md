# Human PR 200

Human PR 200 is the historical working name for the planned larger, multilingual
successor to Human PR 20. The prospective paired-power analysis raises the confirmatory
target to 300 independent human review comments, each rendered as a supported
reviewed-commit case and an unsupported merged-commit case. The directory name remains
stable for artifact compatibility; a successful freeze will contain 600 temporal cases.

The benchmark has two deliberately separate stages:

1. `candidates_all.jsonl` is acquired mechanically from public GitHub review comments.
   Every candidate has a human author, merged pull request, exact reviewed and merge
   commits, changed anchored context, source links, and hashes of both complete files.
2. Two annotators independently decide whether the comment expresses a self-contained,
   technically checkable claim and whether the merge snapshot removes that condition.
   Disagreements go to a third adjudicator. Only adjudicated candidates become cases.

A second acquisition wave is preserved in `candidates_expansion.jsonl`; the combined
artifact is `candidates_682.jsonl` and currently contains 682 candidates from 63
repositories. Acquisition does not assign labels or generate normalized claims. This prevents an LLM
or a change heuristic from becoming an unreported source of benchmark ground truth.
Only one candidate is retained per pull request during acquisition, and repositories
used by the prior Human PR 20 holdout are not in the source registry.

Acquire the candidate pool with an authenticated GitHub token:

```bash
GITHUB_TOKEN="$(gh auth token)" PYTHONPATH=. python3 scripts/acquire_human_pr_candidates.py \
  --repositories benchmarks/human_pr_200/repositories.json \
  --output benchmarks/human_pr_200/candidates.jsonl \
  --audit benchmarks/human_pr_200/acquisition_audit.json \
  --cutoff 2026-08-30T23:59:59Z \
  --pages 3 \
  --per-repo 12
```

The candidate pool is not an evaluation benchmark. Do not run model experiments on it
until annotation, adjudication, case rendering, contamination checks, and input freezing
are complete.

The canonical combined queue is generated with:

```bash
PYTHONPATH=. python3 scripts/prepare_human_pr_annotation_queue.py \
  --input benchmarks/human_pr_200/candidates_682.jsonl \
  --output benchmarks/human_pr_200/annotation_queue_682.jsonl
```

The earlier 276-comment tranche remains available for workflow testing. The powered
study requires both experts to annotate the full blinded `annotation_queue_682.jsonl`;
the target cannot be reached from the smaller tranche.

Open the local annotation tool by serving the repository root and visiting
`http://localhost:4173/review/human_pr_200.html`:

```bash
PYTHONPATH=. python3 -m http.server 4173
```

Before the final passes, use the frozen 18-item interface pilot. It contains three
candidates per language from 18 repositories. Pilot labels are workflow-training data,
not benchmark ground truth; see `REVIEWER_HANDOFF.md` for role separation and the exact
handoff procedure.

The portal initially shows a highlighted 15-line window around the reviewed location.
Reviewers can reveal the complete stored excerpt with **Show full context**. This
changes presentation only: exports retain the exact original evidence.

Each annotator exports their own JSONL file. Keep those files private from the other
annotator until both passes are complete. Merge exact agreements and create a blinded
queue for a third adjudicator with:

```bash
PYTHONPATH=. python3 scripts/validate_human_pr_annotation_export.py \
  --input private/annotator_a.jsonl \
  --queue benchmarks/human_pr_200/annotation_queue_682.jsonl \
  --report private/annotator_a_validation.json
```

The validator checks completeness, the stable reviewer ID, frozen claim families,
the exact candidate set and evidence payload, and queue/export hashes. Validate each
expert export before adjudication.

```bash
PYTHONPATH=. python3 scripts/adjudicate_human_pr_annotations.py \
  --annotator-a private/annotator_a.jsonl \
  --annotator-b private/annotator_b.jsonl \
  --resolved benchmarks/human_pr_200/resolved_annotations.jsonl \
  --disagreements private/adjudication_queue.jsonl \
  --audit benchmarks/human_pr_200/adjudication_audit.json
```

After the adjudicator exports the disagreement queue, repeat the command with
`--adjudications private/adjudicator.jsonl`. The renderer rejects rows without two
independent reviewer IDs and, for disagreements, a distinct adjudicator ID:

```bash
PYTHONPATH=. python3 scripts/select_human_pr_200.py \
  --input benchmarks/human_pr_200/resolved_annotations.jsonl \
  --output benchmarks/human_pr_200/final_300.jsonl \
  --manifest benchmarks/human_pr_200/selection_manifest.json \
  --target 300 \
  --min-repositories 40

PYTHONPATH=. python3 scripts/render_human_pr_200.py \
  --input benchmarks/human_pr_200/final_300.jsonl \
  --output-dir benchmarks/human_pr_200/frozen \
  --audit benchmarks/human_pr_200/render_audit.json
```

Selection uses a fixed seed, first enforces repository breadth, and then balances
language and claim-family counts subject to the six-comments-per-repository cap. It
fails closed unless 300 eligible, provenance-complete comments from at least 40
repositories are available.

The generated paired-power report uses the frozen Human PR 20 discordances, a 0.15
smallest effect of practical interest, and alpha 0.025 for each of the two label-specific
tests. Its conservative planning estimate reaches power 0.856 for supported cases and
0.967 for unsupported cases at 300 source comments. See `POWER_PLAN.md` and
`PREREGISTRATION.md`; neither repeated calls nor additional models are counted as new
independent examples.

The paid-run configurations are frozen under `configs/human_pr_expansion_full/` for
the one-pass complete matrix and `configs/human_pr_expansion_stability/` for the
three-pass 60-comment stability subset. They are inputs, not authorization to run:
annotation, selection, rendering, contamination checks, input hashing, and a fresh
price/credit preflight must all finish first.
