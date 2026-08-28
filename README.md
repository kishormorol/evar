# EVAR: Evidence-Verified Adversarial Review

EVAR is a minimal research harness for comparing reviewer/critic code review protocols.

Research question:

> Can external executable verification reduce false consensus between LLM reviewer/critic agents during code review?

This is not a production application. It supports deterministic dummy-agent smoke tests and OpenAI-backed reviewer/critic experiments.

Current writeup:

- [Paper draft](PAPER.md)
- [Manual 50 benchmark results](benchmarks/manual_50/RESULTS.md)
- [Real 10 pilot results](benchmarks/real_10/RESULTS.md)
- [External 10 pilot results](benchmarks/external_10/RESULTS.md)

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

Each command writes JSONL results to stdout for later statistical analysis.
Configured model runs write timestamped JSONL files to `results/` and per-case transcripts to `results/transcripts/<run_id>/`.

Summarize result JSONL with FCR/SCR:

```bash
python -m evar.eval_table --results ar_results.jsonl evar_results.jsonl
python -m evar.eval_table --results ar_results.jsonl evar_results.jsonl --bootstrap 10000 --seed 7
```

`FCR` is the unsupported-case actionable rate. `SCR` is the supported-case actionable rate.

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

## Scientific Guardrails

- Benchmark ground-truth labels are loaded as fixture data and are not changed by protocols.
- Protocols receive a `TaskCase` view that excludes `ground_truth` and `ground_truth_evidence`.
- Reviewer and critic prompts must not include expected answers.
- The verifier uses only submitted evidence receipts plus repository files/commands.
- Model configuration and budgets are recorded in each result row.
- Per-case run failures are emitted as JSONL rows with `run_status: "failed"` instead of being dropped.
- Seeds are set in the default runner config.
- Experiments are reproducible from the `python -m evar.run ...` commands above.
