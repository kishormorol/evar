# External PR 10 Pilot Results

Date: 2026-08-28

This benchmark uses post-commit source snapshots from public repositories and asks PR-style review questions about the changed behavior. It is more realistic than `external_10`, but still uses hand-authored claims rather than live pull-request comments.

## GPT-4.1 Mini

Result files:

- `results/20260829T003248Z-5934bedd_ar.jsonl`
- `results/20260829T003248Z-32311376_ar_text.jsonl`
- `results/20260829T003248Z-19464e26_evar_hard.jsonl`

Bootstrap summary:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ar | 10 | 10 | 0 | 0.800 | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 |
| ar_text | 10 | 10 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| evar_hard | 10 | 10 | 0 | 0.200 | 0.000 | 0.600 | 0.200 | 0.000 | 0.600 |

## Interpretation

This pilot is the first benchmark here that substantially stresses the current receipt/verifier design.

AR and AR-Text retained all supported claims but admitted most or all unsupported claims. EVAR-Hard reduced false consensus substantially, but it also rejected most supported claims because the generated evidence receipts were not mechanically checkable.

Observed EVAR-Hard failure modes:

- Wrong file paths such as `zipp/path.py` when the relevant code is in `zipp/__init__.py`.
- Stale or invented snippets, especially around moved code and renamed expressions.
- Structural receipts that verify a true observation but do not support the stronger candidate claim.
- Behavioral witnesses with invalid one-line Python control flow.

This should not be tuned away on this benchmark. The next work should create a development split of commit-grounded cases, improve receipt generation and structural verifiers there, then rerun this set as a held-out diagnostic.
