# Human PR 20 Model Extension Results

Exploratory post-release model extension over the unchanged 20 temporal human-review cases. Three GPT-5.6 tiers use explicit `reasoning.effort: none`, one run per protocol, and identical budgets. This is not a new untouched benchmark.

> Seed 41 is a provenance label. OpenAI Responses API sampling is not asserted to be deterministic.

## Model-grouped results

| Model | Protocol | n | Failed | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-5.6-luna | ar | 20 | 0 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 0 / 0 | 55,423 / 3,321 | 3.21 | $0.015 |
| gpt-5.6-luna | ar_text | 20 | 0 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 0 / 0 | 57,972 / 3,238 | 3.18 | $0.015 |
| gpt-5.6-luna | evar_hard | 20 | 0 | 0.000 (0.000-0.000) | 0.600 (0.300-0.900) | 17 / 3 | 60,114 / 3,320 | 3.10 | $0.016 |
| gpt-5.6-sol | ar | 20 | 0 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 0 / 0 | 55,590 / 3,493 | 3.93 | $0.292 |
| gpt-5.6-sol | ar_text | 20 | 0 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 0 / 0 | 58,318 / 3,423 | 4.08 | $0.302 |
| gpt-5.6-sol | evar_hard | 20 | 0 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 19 / 1 | 59,917 / 3,441 | 3.61 | $0.308 |
| gpt-5.6-terra | ar | 20 | 0 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 0 / 0 | 55,314 / 3,210 | 2.98 | $0.149 |
| gpt-5.6-terra | ar_text | 20 | 0 | 0.100 (0.000-0.300) | 0.600 (0.300-0.900) | 0 / 0 | 58,033 / 3,258 | 3.10 | $0.155 |
| gpt-5.6-terra | evar_hard | 20 | 0 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 18 / 2 | 59,631 / 3,236 | 3.17 | $0.158 |

## Paired changes from AR

Negative delta FCR and non-negative delta SCR favor the candidate. Each metric has only ten paired cases per model.

| Model | Comparison | Metric | Pairs | Delta (95% CI) |
| --- | --- | --- | ---: | ---: |
| gpt-5.6-luna | ar_text-ar | FCR | 10 | 0.000 (0.000-0.000) |
| gpt-5.6-luna | ar_text-ar | SCR | 10 | 0.000 (0.000-0.000) |
| gpt-5.6-luna | evar_hard-ar | FCR | 10 | -0.100 (-0.300-0.000) |
| gpt-5.6-luna | evar_hard-ar | SCR | 10 | -0.100 (-0.300-0.000) |
| gpt-5.6-sol | ar_text-ar | FCR | 10 | 0.000 (0.000-0.000) |
| gpt-5.6-sol | ar_text-ar | SCR | 10 | -0.100 (-0.300-0.000) |
| gpt-5.6-sol | evar_hard-ar | FCR | 10 | 0.000 (0.000-0.000) |
| gpt-5.6-sol | evar_hard-ar | SCR | 10 | -0.100 (-0.300-0.000) |
| gpt-5.6-terra | ar_text-ar | FCR | 10 | 0.000 (0.000-0.000) |
| gpt-5.6-terra | ar_text-ar | SCR | 10 | -0.200 (-0.500-0.000) |
| gpt-5.6-terra | evar_hard-ar | FCR | 10 | 0.000 (0.000-0.000) |
| gpt-5.6-terra | evar_hard-ar | SCR | 10 | 0.000 (0.000-0.000) |

## Descriptive pooled view

This view pools the same 20 cases across three models and is not an independent-sample estimate.

| Protocol | Model-case records | FCR | SCR |
| --- | ---: | ---: | ---: |
| ar | 60 | 0.100 | 0.767 |
| ar_text | 60 | 0.100 | 0.667 |
| evar_hard | 60 | 0.067 | 0.700 |

## Interpretation

The extension remains heterogeneous. Luna EVAR-Hard lowers observed FCR by one case relative to both textual conditions but also retains one fewer supported claim. Terra EVAR-Hard matches AR and retains two more supported claims than AR-Text at the same FCR. Sol EVAR-Hard exactly matches AR-Text and retains one fewer supported claim than AR. Across the three models descriptively pooled, EVAR-Hard has FCR 0.067 and SCR 0.700, compared with 0.100/0.667 for AR-Text and 0.100/0.767 for AR. No protocol universally dominates.

## Audit

The judge-free audit checked all 180 extension records and transcripts and reported no issues or run failures.
