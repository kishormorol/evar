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

Each model runs AR, AR-Text, and EVAR-Hard once over all 20 cases, for 300 attempted decisions. Seed 53 is a provenance label; it is not a claim of deterministic inference. Temperature is omitted, output is capped at 1,200 tokens per model call, and OpenRouter routing is restricted to endpoints that accept the requested JSON-schema parameter.

## Interpretation Boundary

This is an exploratory extension on a previously reported benchmark, not a new untouched holdout. The five model measurements reuse the same cases and must not be treated as 100 independent examples. Gateway routing also adds an infrastructure layer: the exact model slug is frozen, but OpenRouter can select among eligible serving providers for that model.

Before model calls, freeze the evaluator commit and hashes for cases, snapshots, prompts, configs, backend code, verifier code, and scoring code. After all calls, preserve every result row and transcript, run the judge-free audit, and generate a separate output manifest.
