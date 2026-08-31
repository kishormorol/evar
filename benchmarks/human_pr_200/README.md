# Human PR 200

Human PR 200 is the planned larger, multilingual successor to Human PR 20. The target
is 100 independent human review comments, each rendered as a supported reviewed-commit
case and an unsupported merged-commit case.

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

For the first annotation pass, use the balanced 276-comment tranche
`annotation_queue_280.jsonl`: 50 comments per language where available, a six-comment
repository cap, and all records still blinded and unlabeled.

Open the local annotation tool by serving the repository root and visiting
`http://localhost:4173/review/human_pr_200.html`:

```bash
PYTHONPATH=. python3 -m http.server 4173
```

Each annotator exports their own JSONL file. Keep those files private from the other
annotator until both passes are complete. Merge exact agreements and create a blinded
queue for a third adjudicator with:

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
  --output benchmarks/human_pr_200/final_100.jsonl \
  --manifest benchmarks/human_pr_200/selection_manifest.json

PYTHONPATH=. python3 scripts/render_human_pr_200.py \
  --input benchmarks/human_pr_200/final_100.jsonl \
  --output-dir benchmarks/human_pr_200/frozen \
  --audit benchmarks/human_pr_200/render_audit.json
```

Selection uses a fixed seed, first enforces repository breadth, and then balances
language and claim-family counts subject to the six-comments-per-repository cap. It
fails closed unless 100 eligible, provenance-complete comments from at least 20
repositories are available.
