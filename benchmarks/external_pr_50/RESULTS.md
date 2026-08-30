# External PR 50 Results

Frozen evaluation over 50 commit-grounded claim cases, two models, three protocols, and two independent replicate labels. Confidence intervals use 10,000 case-cluster bootstrap samples.

> Seeds 7 and 17 are frozen replicate labels. The OpenAI Responses backend used by this artifact does not transmit an explicit inference seed, so they must not be interpreted as controlled RNG seeds.

## Aggregate results

| Model | Protocol | n | Failed | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-4.1 | ar | 100 | 0 | 0.120 (0.000–0.280) | 1.000 (1.000–1.000) | 0 / 0 | 156,495 / 17,016 | 2.29 | $0.449 |
| gpt-4.1 | ar_text | 100 | 0 | 0.120 (0.020–0.240) | 1.000 (1.000–1.000) | 0 / 0 | 170,374 / 16,272 | 2.30 | $0.471 |
| gpt-4.1 | evar_hard | 100 | 0 | 0.060 (0.000–0.160) | 0.860 (0.720–0.980) | 76 / 24 | 195,933 / 15,456 | 2.17 | $0.516 |
| gpt-4.1-mini | ar | 100 | 0 | 0.160 (0.040–0.320) | 0.980 (0.940–1.000) | 0 / 0 | 154,267 / 14,748 | 3.08 | $0.085 |
| gpt-4.1-mini | ar_text | 100 | 0 | 0.120 (0.000–0.280) | 0.980 (0.940–1.000) | 0 / 0 | 169,699 / 16,401 | 3.25 | $0.094 |
| gpt-4.1-mini | evar_hard | 100 | 1 | 0.041 (0.000–0.125) | 0.420 (0.240–0.600) | 47 / 52 | 202,298 / 16,610 | 3.23 | $0.107 |

## Paired deltas from AR

Negative ΔFCR and non-negative ΔSCR favor the candidate protocol.

| Model | Comparison | Metric | Pairs | Delta (95% CI) |
| --- | --- | --- | ---: | ---: |
| gpt-4.1 | ar_text-ar | FCR | 50 | 0.000 (-0.060–0.060) |
| gpt-4.1 | ar_text-ar | SCR | 50 | 0.000 (0.000–0.000) |
| gpt-4.1 | evar_hard-ar | FCR | 50 | -0.060 (-0.160–0.000) |
| gpt-4.1 | evar_hard-ar | SCR | 50 | -0.140 (-0.280–-0.020) |
| gpt-4.1-mini | ar_text-ar | FCR | 50 | -0.040 (-0.120–0.000) |
| gpt-4.1-mini | ar_text-ar | SCR | 50 | 0.000 (0.000–0.000) |
| gpt-4.1-mini | evar_hard-ar | FCR | 49 | -0.122 (-0.255–0.000) |
| gpt-4.1-mini | evar_hard-ar | SCR | 50 | -0.560 (-0.740–-0.380) |

## Per-family results

| Model | Protocol | Family | n | FCR | SCR |
| --- | --- | --- | ---: | ---: | ---: |
| gpt-4.1 | ar | behavior_inversion | 20 | 0.200 | 1.000 |
| gpt-4.1 | ar | causal_mislocalization | 20 | 0.200 | 1.000 |
| gpt-4.1 | ar | incorrect_call_relationship | 20 | 0.000 | 1.000 |
| gpt-4.1 | ar | missing_guard | 20 | 0.000 | 1.000 |
| gpt-4.1 | ar | stale_evidence | 20 | 0.200 | 1.000 |
| gpt-4.1 | ar_text | behavior_inversion | 20 | 0.200 | 1.000 |
| gpt-4.1 | ar_text | causal_mislocalization | 20 | 0.100 | 1.000 |
| gpt-4.1 | ar_text | incorrect_call_relationship | 20 | 0.000 | 1.000 |
| gpt-4.1 | ar_text | missing_guard | 20 | 0.100 | 1.000 |
| gpt-4.1 | ar_text | stale_evidence | 20 | 0.200 | 1.000 |
| gpt-4.1 | evar_hard | behavior_inversion | 20 | 0.100 | 0.800 |
| gpt-4.1 | evar_hard | causal_mislocalization | 20 | 0.000 | 0.700 |
| gpt-4.1 | evar_hard | incorrect_call_relationship | 20 | 0.000 | 1.000 |
| gpt-4.1 | evar_hard | missing_guard | 20 | 0.000 | 0.800 |
| gpt-4.1 | evar_hard | stale_evidence | 20 | 0.200 | 1.000 |
| gpt-4.1-mini | ar | behavior_inversion | 20 | 0.200 | 1.000 |
| gpt-4.1-mini | ar | causal_mislocalization | 20 | 0.400 | 1.000 |
| gpt-4.1-mini | ar | incorrect_call_relationship | 20 | 0.000 | 1.000 |
| gpt-4.1-mini | ar | missing_guard | 20 | 0.000 | 0.900 |
| gpt-4.1-mini | ar | stale_evidence | 20 | 0.200 | 1.000 |
| gpt-4.1-mini | ar_text | behavior_inversion | 20 | 0.200 | 1.000 |
| gpt-4.1-mini | ar_text | causal_mislocalization | 20 | 0.200 | 1.000 |
| gpt-4.1-mini | ar_text | incorrect_call_relationship | 20 | 0.000 | 1.000 |
| gpt-4.1-mini | ar_text | missing_guard | 20 | 0.000 | 0.900 |
| gpt-4.1-mini | ar_text | stale_evidence | 20 | 0.200 | 1.000 |
| gpt-4.1-mini | evar_hard | behavior_inversion | 20 | 0.000 | 0.200 |
| gpt-4.1-mini | evar_hard | causal_mislocalization | 20 | 0.000 | 0.400 |
| gpt-4.1-mini | evar_hard | incorrect_call_relationship | 20 | 0.000 | 0.900 |
| gpt-4.1-mini | evar_hard | missing_guard | 20 | 0.000 | 0.200 |
| gpt-4.1-mini | evar_hard | stale_evidence | 20 | 0.200 | 0.400 |

## Audit and exclusions

The judge-free audit checked all 600 canonical records and their transcripts. It reported one `ModelOutputError` in the mini EVAR-Hard seed-7 run and the associated missing failed-row experiment metadata. No prompt-hash, transcript-integrity, actionability-gate, token, or latency inconsistency was detected.

Four infrastructure-invalid attempts are preserved under `results/external_pr_50/excluded/` and excluded for the reasons recorded in `benchmarks/external_pr_50/run_index.json`.
