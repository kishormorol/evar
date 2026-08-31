# EVAR: Evidence-Verified Adversarial Review

EVAR is a minimal research harness for comparing reviewer/critic code review protocols.

Research question:

> Can external executable verification reduce false consensus between LLM reviewer/critic agents during code review?

This is not a production application. It supports deterministic dummy-agent smoke tests and OpenAI-backed reviewer/critic experiments.

Current writeup:

- [Anonymous FSE-format paper (PDF)](paper/arxiv/main.pdf)
- [LaTeX source](paper/arxiv/main.tex)
- [Earlier narrative draft](PAPER.md)
- [Manual 50 benchmark results](benchmarks/manual_50/RESULTS.md)
- [Real 10 pilot results](benchmarks/real_10/RESULTS.md)
- [External 10 pilot results](benchmarks/external_10/RESULTS.md)
- [External PR 10 pilot results](benchmarks/external_pr_10/RESULTS.md)
- [External PR 20 results](benchmarks/external_pr_20/RESULTS.md)
- [Frozen External PR 50 results](benchmarks/external_pr_50/RESULTS.md)
- [Untouched Human PR 20 results](benchmarks/human_pr_20/RESULTS.md)
- [GPT-5.6 model extension results](benchmarks/human_pr_20/MODEL_EXTENSION_RESULTS.md)
- [Claude, Gemini, DeepSeek, Kimi, and Qwen extension](benchmarks/human_pr_20/CROSS_PROVIDER_RESULTS.md)
- [Human PR 200 expert-annotation protocol](benchmarks/human_pr_200/README.md)
- [Independent review packet](review/INDEPENDENT_REVIEW.md)

## Protocols

- `AR`: reviewer proposes findings, critic challenges, consensus is textual.
- `AR-Text`: same architecture, but reviewer adds textual evidence when challenged.
- `EVAR-Hard`: reviewer must attach a structured evidence receipt; deterministic verification gates actionability.

All protocol classes accept the same `ProtocolBudget` and `AgentConfig` objects so experiments can keep model configuration and review/revision budgets equivalent.

## Run

```bash
python -m evar
python -m unittest discover -s tests
```

`pytest` is optional for developer environments that install `.[dev]`.

Model-backed runs load credentials from the process environment or the repository's ignored `.env` file:

```text
OPENAI_API_KEY=...       # OpenAI Responses API models
OPENROUTER_API_KEY=...   # Claude, Gemini, Kimi, DeepSeek, Qwen, and other routed models
```

See `.env.example` for the supported variable names. Never commit the populated `.env` file.

## Benchmark JSONL

Each benchmark fixture is one JSON object per line:

```json
{"case_id":"case-1","repo_path":"path/to/repo","task_description":"Review the target change.","claim":"handler is missing an input guard","ground_truth":"UNSUPPORTED","ground_truth_evidence":"The guard exists in handler.py.","validation_command":["python","-m","unittest"],"claim_family":"missing_guard"}
```

Allowed `ground_truth` values:

- `SUPPORTED`
- `UNSUPPORTED`

Allowed `claim_family` values:

- `behavior_inversion`
- `missing_guard`
- `incorrect_call_relationship`
- `causal_mislocalization`
- `stale_evidence`

Run a protocol over a JSONL fixture file:

```bash
python -m evar.run --protocol ar --cases cases.jsonl
python -m evar.run --protocol ar_text --cases cases.jsonl
python -m evar.run --protocol evar --cases cases.jsonl
```

Cross-provider runs use the same command with an `openrouter` config, for example:

```bash
python -m evar.run --protocol evar_hard \
  --cases benchmarks/human_pr_20/cases.jsonl \
  --config configs/cross_provider_human_pr_20_v2/claude_sonnet5_seed67.yaml
```

Each command writes JSONL results to stdout for later statistical analysis.
Configured model runs write timestamped JSONL files to `results/` and per-case transcripts to `results/transcripts/<run_id>/`.

Summarize result JSONL with FCR/SCR:

```bash
python -m evar.eval_table --results ar_results.jsonl evar_results.jsonl
python -m evar.eval_table --results ar_results.jsonl evar_results.jsonl --bootstrap 10000 --seed 7
python -m evar.eval_table --results ar_results.jsonl evar_results.jsonl --by-family
python -m evar.eval_table --results ar_results.jsonl evar_results.jsonl --costs
```

`FCR` is the unsupported-case actionable rate. `SCR` is the supported-case actionable rate.
Use `--by-family` to append per-claim-family FCR/SCR rows; it can be combined with
`--bootstrap` and either output format.
Use `--costs` to append total token usage and per-case runtime for each protocol.

Validate model-adapter structured outputs without calling a model API:

```bash
python -m evar.run_model --cases cases.jsonl --dry-run
```

Compare deterministic AR, AR-Text, and EVAR-Hard evidence-level protocols:

```bash
python -m evar.demo_compare
```

Evidence-level protocol registry names:

- `ar`
- `ar_text`
- `evar_hard`

## Current Results

Untouched `human_pr_20` holdout built from ten real human review comments across five previously unseen repositories:

| Model | Protocol | FCR | SCR |
| --- | --- | ---: | ---: |
| `gpt-4.1` | `ar` | 0.400 | 0.700 |
| `gpt-4.1` | `ar_text` | 0.200 | 0.700 |
| `gpt-4.1` | `evar_hard` | 0.300 | 0.600 |
| `gpt-4.1-mini` | `ar` | 0.400 | 0.900 |
| `gpt-4.1-mini` | `ar_text` | 0.200 | 0.700 |
| `gpt-4.1-mini` | `evar_hard` | 0.200 | 0.700 |

This final holdout does not establish that EVAR outperforms AR-Text. The full 120-record audit passed, and all intervals and costs are reported in the linked result artifact.

Exploratory extension on the same Human PR 20 cases, using explicit reasoning effort `none` and one run per protocol:

| Model | Protocol | FCR | SCR | EVAR receipts verified |
| --- | --- | ---: | ---: | ---: |
| `gpt-5.6-luna` | `ar` | 0.100 | 0.700 | — |
| `gpt-5.6-luna` | `ar_text` | 0.100 | 0.700 | — |
| `gpt-5.6-luna` | `evar_hard` | 0.000 | 0.600 | 17/20 |
| `gpt-5.6-terra` | `ar` | 0.100 | 0.800 | — |
| `gpt-5.6-terra` | `ar_text` | 0.100 | 0.600 | — |
| `gpt-5.6-terra` | `evar_hard` | 0.100 | 0.800 | 18/20 |
| `gpt-5.6-sol` | `ar` | 0.100 | 0.800 | — |
| `gpt-5.6-sol` | `ar_text` | 0.100 | 0.700 | — |
| `gpt-5.6-sol` | `evar_hard` | 0.100 | 0.700 | 19/20 |

All 180 extension decisions completed and passed the judge-free audit. The outcomes are heterogeneous: EVAR-Hard trades FCR for SCR with Luna, matches AR with Terra, and matches AR-Text with Sol. The estimated standard token cost was $1.411; see the linked report for intervals, token counts, prices, and limitations.

The matched cross-provider extension attempted another 300 decisions with Claude Sonnet 5, Gemini 3.1 Pro Preview, DeepSeek V4 Pro, Kimi K3, and Qwen3.8 Max. It retained 267 valid decisions and all 33 structured-output failures. Claude and Gemini completed every cell; DeepSeek, Kimi, and Qwen had model-dependent incomplete cells, so the report does not turn surviving subsets into protocol rankings. The canonical matrix cost an estimated $3.350 in standard token charges; diagnostics and superseded retries brought total gateway usage to $9.241.

Held-out 50-case `gpt-4.1` result:

| Protocol | FCR | SCR |
| --- | ---: | ---: |
| `ar` | 0.040 | 0.960 |
| `ar_text` | 0.000 | 0.920 |
| `evar_hard` | 0.000 | 1.000 |

Three `gpt-4.1-mini` repetitions on the same 50-case benchmark:

| Protocol | Mean FCR | Mean SCR |
| --- | ---: | ---: |
| `ar` | 0.000 | 0.813 |
| `ar_text` | 0.000 | 0.987 |
| `evar_hard` | 0.000 | 0.987 |

Independent-source `external_10` pilot with `gpt-4.1-mini`:

| Protocol | FCR | SCR |
| --- | ---: | ---: |
| `ar` | 0.000 | 1.000 |
| `ar_text` | 0.200 | 1.000 |
| `evar_hard` | 0.000 | 1.000 |

External commit-grounded `external_pr_10` pilot with `gpt-4.1-mini`:

| Protocol | FCR | SCR |
| --- | ---: | ---: |
| `ar` | 0.800 | 1.000 |
| `ar_text` | 1.000 | 1.000 |
| `evar_hard` | 0.000 | 1.000 |

External commit-grounded `external_pr_20` benchmark with `gpt-4.1-mini`:

| Protocol | FCR | SCR |
| --- | ---: | ---: |
| `ar` | 0.300 | 1.000 |
| `ar_text` | 0.100 | 0.900 |
| `evar_hard` | 0.100 | 0.900 |
| `evar_hard` with receipt repair | 0.000 | 1.000 |

## Scientific Guardrails

- Benchmark ground-truth labels are loaded as fixture data and are not changed by protocols.
- Protocols receive a `TaskCase` view that excludes `ground_truth` and `ground_truth_evidence`.
- Reviewer and critic prompts must not include expected answers.
- The verifier uses only submitted evidence receipts plus repository files/commands.
- Model configuration and budgets are recorded in each result row.
- Per-case run failures are emitted as JSONL rows with `run_status: "failed"` instead of being dropped.
- Seeds are set in the default runner config.
- Experiments are reproducible from the `python -m evar.run ...` commands above.

Behavioral verification defaults to local subprocess execution for compatibility. For untrusted repositories, set `verifier_execution_backend: container` and `verifier_container_image` in the run config. The Docker backend disables networking, mounts the repository read-only, drops Linux capabilities, runs as a non-root user, and applies CPU, memory, PID, timeout, and temporary-filesystem limits.
