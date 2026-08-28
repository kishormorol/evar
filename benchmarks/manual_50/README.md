# Manual 50 Held-Out Benchmark

This benchmark contains 50 deterministic toy code-review claim cases:

- 25 supported claims
- 25 unsupported claims
- 10 cases per claim family

Claim families:

- `behavior_inversion`
- `missing_guard`
- `incorrect_call_relationship`
- `causal_mislocalization`
- `stale_evidence`

Regenerate the cases:

```bash
python benchmarks/manual_50/generate.py
```

Run a protocol:

```bash
python -m evar.run --cases benchmarks/manual_50/cases.jsonl --protocol evar_hard --config configs/openai_pilot.yaml
```

Use `benchmarks/manual_10` for prompt and harness development. Use this benchmark as the larger held-out check after changes are frozen.
