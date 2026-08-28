# Real 10 Pilot Results

Date: 2026-08-28

This pilot benchmark uses isolated copies of real EVAR source files. It is less templated than `manual_50`, but still drawn from this repository rather than independent external projects.

## GPT-4.1 Mini

Result files:

- `results/20260828T205529Z-dcf2723d_ar.jsonl`
- `results/20260828T205617Z-5d8acfe7_ar_text.jsonl`
- `results/20260828T205700Z-e9d1d3bd_evar_hard.jsonl`

Bootstrap summary:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ar | 10 | 9 | 1 | 0.000 | 0.000 | 0.000 | 0.600 | 0.200 | 1.000 |
| ar_text | 10 | 10 | 0 | 0.400 | 0.000 | 0.800 | 0.600 | 0.200 | 1.000 |
| evar_hard | 10 | 9 | 1 | 0.000 | 0.000 | 0.000 | 0.200 | 0.000 | 0.600 |

## Interpretation

The synthetic `manual_50` benchmark did not predict performance on this real-code pilot. EVAR-Hard was conservative and avoided false positives, but it retained only one supported claim among completed supported cases.

The failures are useful:

- Real source files are longer and noisier than the synthetic fixtures.
- The model sometimes emits malformed receipts when the relevant file path is nested.
- EVAR-Hard rejects many claims because evidence receipts are unverified or too weak.
- AR-Text admitted two unsupported claims, showing textual evidence remains vulnerable on more realistic code.

This should be treated as a pilot diagnostic, not a paper-grade result. The next step is to expand this into an independent external-repository benchmark and improve receipt generation without tuning on evaluation cases.
