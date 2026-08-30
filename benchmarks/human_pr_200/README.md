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
artifact is `candidates_all.jsonl` and currently contains 487 candidates from 44
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
  --input benchmarks/human_pr_200/candidates_all.jsonl \
  --output benchmarks/human_pr_200/annotation_queue_all.jsonl
```

Open the local annotation tool by serving the repository root and visiting
`http://localhost:4173/review/human_pr_200.html`:

```bash
PYTHONPATH=. python3 -m http.server 4173
```

Each annotator exports their own JSONL file. Merge the completed annotations and
render accepted temporal pairs with `scripts/render_human_pr_200.py`.
