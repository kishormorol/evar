# Cross-Provider Model Extension

This extension evaluates whether EVAR's operating point generalizes beyond OpenAI models. It reuses the unchanged Human PR 20 cases, prompts, deterministic verifier, protocol budgets, and FCR/SCR scoring.

## Frozen Models

| Family | Exact OpenRouter model slug | Reasoning effort |
| --- | --- | --- |
| Claude | `anthropic/claude-sonnet-5` | `low` |
| Gemini | `google/gemini-3.1-pro-preview` | `low` |
| Kimi | `moonshotai/kimi-k3` | `low` |
| DeepSeek | `deepseek/deepseek-v4-pro-0813` | `low` |
| Qwen | `qwen/qwen3.8-max` | `low` |

Each model runs AR, AR-Text, and EVAR-Hard once over all 20 cases, for 300 attempted decisions. Seed 67 is a provenance label; it is not a claim of deterministic inference. Temperature is omitted, output is capped at 2,400 tokens per model call, and OpenRouter routing is restricted to endpoints that accept the requested JSON-schema parameter.

The canonical matrix produced 267 valid decisions and retained 33 failed rows: Claude and Gemini completed 60/60, DeepSeek 43/60, Kimi 55/60, and Qwen 49/60. Only 20/20-valid cells receive FCR/SCR estimates. The canonical token estimate is $3.350; diagnostics and superseded retries are excluded from that estimate but included in the reported $9.241 gateway usage.

## Interpretation Boundary

This is an exploratory extension on a previously reported benchmark, not a new untouched holdout. The five model measurements reuse the same cases and must not be treated as 100 independent examples. Gateway routing also adds an infrastructure layer: the exact model slug is frozen, but OpenRouter can select among eligible serving providers for that model.

The run index records the execution commit and exact canonical files. The artifact manifest hashes cases, snapshots, prompts, configs, backend code, verifier code, and scoring code. Every result row and transcript is preserved, including failures; a judge-free audit checks the 300-row matrix without converting failures into negative predictions.
