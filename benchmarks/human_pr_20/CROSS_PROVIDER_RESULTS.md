# Human PR 20 Cross-Provider Results

Matched 300-attempt comparison on the unchanged 20-case temporal holdout. Every attempted row is retained. Quality metrics are shown only for 20/20-valid cells; incomplete cells document this fixed-timeout client/gateway configuration.

> Seed 67 is a provenance label; OpenRouter sampling is not asserted to be deterministic. Each entry contains 20 attempted cases, including failures.

| Model | Protocol | Valid / attempted | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Input / output tokens | Mean seconds | Est. API cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Claude Sonnet 5 | ar | 20 / 20 | 0.000 (0.000-0.000) | 0.600 (0.300-0.900) | 0 / 0 | 102,096 / 5,983 | 7.30 | $0.264 |
| Claude Sonnet 5 | ar_text | 20 / 20 | 0.000 (0.000-0.000) | 0.600 (0.300-0.900) | 0 / 0 | 107,055 / 5,994 | 7.29 | $0.274 |
| Claude Sonnet 5 | evar_hard | 20 / 20 | 0.000 (0.000-0.000) | 0.500 (0.200-0.800) | 18 / 0 | 109,973 / 6,306 | 7.77 | $0.283 |
| DeepSeek V4 Pro | ar | 13 / 20 | -- | -- | 0 / 0 | 43,535 / 20,849 | 25.75 | $0.070 |
| DeepSeek V4 Pro | ar_text | 16 / 20 | -- | -- | 0 / 0 | 52,439 / 21,159 | 27.93 | $0.077 |
| DeepSeek V4 Pro | evar_hard | 14 / 20 | -- | -- | 13 / 0 | 52,086 / 20,066 | 34.03 | $0.074 |
| Gemini 3.1 Pro Preview | ar | 20 / 20 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 0 / 0 | 71,060 / 13,215 | 8.22 | $0.301 |
| Gemini 3.1 Pro Preview | ar_text | 20 / 20 | 0.000 (0.000-0.000) | 0.800 (0.500-1.000) | 0 / 0 | 73,782 / 12,510 | 7.99 | $0.298 |
| Gemini 3.1 Pro Preview | evar_hard | 20 / 20 | 0.000 (0.000-0.000) | 0.800 (0.500-1.000) | 20 / 0 | 75,896 / 13,080 | 7.89 | $0.309 |
| Kimi K3 | ar | 15 / 20 | -- | -- | 0 / 0 | 50,593 / 3,983 | 25.44 | $0.212 |
| Kimi K3 | ar_text | 20 / 20 | 0.000 (0.000-0.000) | 0.700 (0.400-1.000) | 0 / 0 | 66,312 / 4,977 | 14.35 | $0.274 |
| Kimi K3 | evar_hard | 20 / 20 | 0.000 (0.000-0.000) | 0.800 (0.500-1.000) | 19 / 1 | 67,796 / 4,795 | 18.79 | $0.275 |
| Qwen3.8 Max | ar | 16 / 20 | -- | -- | 0 / 0 | 49,638 / 16,573 | 28.00 | $0.199 |
| Qwen3.8 Max | ar_text | 18 / 20 | -- | -- | 0 / 0 | 56,965 / 18,300 | 27.35 | $0.224 |
| Qwen3.8 Max | evar_hard | 15 / 20 | -- | -- | 13 / 0 | 59,717 / 16,396 | 28.27 | $0.218 |

## Paired changes from AR

Each interval resamples the ten temporal source-comment pairs. Negative FCR and non-negative SCR deltas favor the candidate protocol.

| Model | Comparison | Metric | Pairs | Delta (95% CI) |
| --- | --- | --- | ---: | ---: |
| Claude Sonnet 5 | ar_text-ar | FCR | 10 | 0.000 (0.000-0.000) |
| Claude Sonnet 5 | ar_text-ar | SCR | 10 | 0.000 (-0.300-0.300) |
| Claude Sonnet 5 | evar_hard-ar | FCR | 10 | 0.000 (0.000-0.000) |
| Claude Sonnet 5 | evar_hard-ar | SCR | 10 | -0.100 (-0.400-0.200) |
| Gemini 3.1 Pro Preview | ar_text-ar | FCR | 10 | -0.100 (-0.300-0.000) |
| Gemini 3.1 Pro Preview | ar_text-ar | SCR | 10 | 0.000 (0.000-0.000) |
| Gemini 3.1 Pro Preview | evar_hard-ar | FCR | 10 | -0.100 (-0.300-0.000) |
| Gemini 3.1 Pro Preview | evar_hard-ar | SCR | 10 | 0.000 (0.000-0.000) |

## Operational accounting

Across all cells, 267 of 300 attempts produced valid decisions and 33 failed before scoring. Failures remain in denominators for operational accounting but not in FCR/SCR denominators. Because missingness is model-dependent, we do not pool the surviving decisions.

| Model | Valid / attempted | Client timeout | Schema / parse | Other |
| --- | ---: | ---: | ---: | ---: |
| Claude Sonnet 5 | 60 / 60 | 0 | 0 | 0 |
| DeepSeek V4 Pro | 43 / 60 | 16 | 1 | 0 |
| Gemini 3.1 Pro Preview | 60 / 60 | 0 | 0 | 0 |
| Kimi K3 | 55 / 60 | 5 | 0 | 0 |
| Qwen3.8 Max | 49 / 60 | 11 | 0 | 0 |

Thirty-two of the 33 failed rows hit the runner's 20-second HTTP transport deadline; one DeepSeek row failed schema parsing. These observations characterize this client/gateway configuration, not intrinsic model reliability. No failed row is interpreted as a negative review decision.

## Scope

This is a model-diversity extension, not a new-data extension. It probes cross-provider portability but does not increase the number of independent human review comments, and timeout-censored cells cannot support reliability comparisons. The larger Human PR 200 pool remains unlabeled until two independent experts and a third adjudicator complete the frozen protocol.
