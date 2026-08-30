# Human PR 20 Results

Untouched temporal holdout built from ten real human pull-request review comments across five previously unseen repositories. Each comment yields a supported reviewed-commit case and an unsupported merge-commit case. The evaluator and prompts were frozen before any model call.

> The integer seed is a provenance label. OpenAI Responses API sampling is not asserted to be deterministic.

## Aggregate results

| Model | Protocol | n | Failed | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-4.1 | ar | 20 | 0 | 0.400 (0.100–0.700) | 0.700 (0.400–1.000) | 0 / 0 | 55,588 / 3,045 | 2.31 | $0.136 |
| gpt-4.1 | ar_text | 20 | 0 | 0.200 (0.000–0.500) | 0.700 (0.400–1.000) | 0 / 0 | 58,600 / 3,206 | 2.39 | $0.143 |
| gpt-4.1 | evar_hard | 20 | 0 | 0.300 (0.000–0.600) | 0.600 (0.300–0.900) | 18 / 2 | 60,045 / 3,114 | 2.32 | $0.145 |
| gpt-4.1-mini | ar | 20 | 0 | 0.400 (0.100–0.700) | 0.900 (0.700–1.000) | 0 / 0 | 55,732 / 3,175 | 3.58 | $0.027 |
| gpt-4.1-mini | ar_text | 20 | 0 | 0.200 (0.000–0.500) | 0.700 (0.400–1.000) | 0 / 0 | 58,853 / 3,328 | 3.42 | $0.029 |
| gpt-4.1-mini | evar_hard | 20 | 0 | 0.200 (0.000–0.500) | 0.700 (0.400–1.000) | 18 / 2 | 61,243 / 3,302 | 3.45 | $0.030 |

## Paired deltas from AR

Negative ΔFCR and non-negative ΔSCR favor the candidate. Intervals are case-cluster bootstrap intervals and are wide because each condition has only ten cases per label.

| Model | Comparison | Metric | Pairs | Delta (95% CI) |
| --- | --- | --- | ---: | ---: |
| gpt-4.1 | ar_text-ar | FCR | 10 | -0.200 (-0.500–0.000) |
| gpt-4.1 | ar_text-ar | SCR | 10 | 0.000 (-0.300–0.300) |
| gpt-4.1 | evar_hard-ar | FCR | 10 | -0.100 (-0.300–0.000) |
| gpt-4.1 | evar_hard-ar | SCR | 10 | -0.100 (-0.300–0.000) |
| gpt-4.1-mini | ar_text-ar | FCR | 10 | -0.200 (-0.500–0.000) |
| gpt-4.1-mini | ar_text-ar | SCR | 10 | -0.200 (-0.500–0.000) |
| gpt-4.1-mini | evar_hard-ar | FCR | 10 | -0.200 (-0.500–0.000) |
| gpt-4.1-mini | evar_hard-ar | SCR | 10 | -0.200 (-0.500–0.000) |

## Interpretation

On `gpt-4.1-mini`, EVAR-Hard and AR-Text tie at FCR 0.200 and SCR 0.700. On `gpt-4.1`, EVAR-Hard is worse than AR-Text on this small holdout (FCR 0.300 vs 0.200; SCR 0.600 vs 0.700). These results do not establish that EVAR outperforms the stronger text-evidence baseline. They do show that the v2 receipt format retained substantially more supported findings than the earlier external-pr benchmark, but the datasets differ, so that comparison is diagnostic rather than causal.

## Audit

The judge-free audit checked all 120 records and transcripts. It found no failures, prompt-hash mismatches, transcript-integrity errors, actionability-gate inconsistencies, token inconsistencies, or latency inconsistencies. All source comments are linked in the frozen cases file and attributed to non-bot GitHub accounts.
