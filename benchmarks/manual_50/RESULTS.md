# Manual 50 Results

Date: 2026-08-28

## Harness Changes

- Added `benchmarks/manual_50`, a deterministic held-out benchmark with 50 cases.
- Added transcript persistence under `results/transcripts/<run_id>/<case_id>.json`.
- Added OpenAI configs:
  - `configs/openai_pilot.yaml` for `gpt-4.1-mini`
  - `configs/openai_gpt41.yaml` for `gpt-4.1`
- Improved AR/AR-Text prompt fairness so non-executed evidence is not framed as failed verification.
- Improved EVAR-Hard critic guidance for verified counterevidence.
- Fixed Windows-safe execution for quoted `python -c` verifier commands.
- Fixed structural verifier matching for common indentation differences.
- Fixed metric aggregation for configured result rows using `final_actionable`.
- Normalized empty optional model-output strings to `None`.

## Unit Tests

```text
Ran 82 tests in 1.370s

OK
```

## GPT-4.1 Mini, 50 Cases, Three Repetitions

| Protocol | Run | FCR | SCR | Failed |
| --- | --- | ---: | ---: | ---: |
| ar | `20260828T195616Z-1d981ab2_ar.jsonl` | 0.000 | 0.760 | 0 |
| ar | `20260828T201243Z-08dbded7_ar.jsonl` | 0.000 | 0.880 | 0 |
| ar | `20260828T202102Z-02d07946_ar.jsonl` | 0.000 | 0.800 | 0 |
| ar_text | `20260828T195904Z-722800e2_ar_text.jsonl` | 0.000 | 1.000 | 0 |
| ar_text | `20260828T201526Z-9047089d_ar_text.jsonl` | 0.000 | 0.960 | 0 |
| ar_text | `20260828T204106Z-eb60f7d6_ar_text.jsonl` | 0.000 | 1.000 | 0 |
| evar_hard | `20260828T200932Z-6ce44436_evar_hard.jsonl` | 0.000 | 1.000 | 0 |
| evar_hard | `20260828T201808Z-9d0bce07_evar_hard.jsonl` | 0.000 | 1.000 | 0 |
| evar_hard | `20260828T202702Z-995e84e0_evar_hard.jsonl` | 0.000 | 0.960 | 0 |

Mean results:

| Protocol | Mean FCR | Mean SCR |
| --- | ---: | ---: |
| ar | 0.000 | 0.813 |
| ar_text | 0.000 | 0.987 |
| evar_hard | 0.000 | 0.987 |

## GPT-4.1, 50 Cases

Result files:

- `results/20260828T203024Z-16682391_ar.jsonl`
- `results/20260828T203246Z-fb1d8e13_ar_text.jsonl`
- `results/20260828T203836Z-f25cfab0_evar_hard.jsonl`

Bootstrap summary:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ar | 50 | 50 | 0 | 0.040 | 0.000 | 0.120 | 0.960 | 0.880 | 1.000 |
| ar_text | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 0.920 | 0.800 | 1.000 |
| evar_hard | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

On the held-out 50-case benchmark, EVAR-Hard and AR-Text both removed false consensus in the mini-model repeated runs. EVAR-Hard matched AR-Text on mean supported-claim retention.

On the larger `gpt-4.1` run, EVAR-Hard was strongest overall: zero false consensus and perfect supported-claim retention. AR had one false positive. AR-Text had zero false positives but missed two supported claims.

The main remaining risk is benchmark simplicity: `manual_50` is balanced and held out from the first 10-case tuning loop, but cases are still synthetic and pattern-based. The next research-quality step is to add less templated cases from real repositories.
