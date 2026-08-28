# Real 10 Pilot Benchmark

This benchmark is a first pilot for real-code evaluation. It uses isolated copies of actual EVAR source files rather than toy generated functions.

Composition:

- 10 cases total
- 5 supported claims
- 5 unsupported claims
- Claims cover backend behavior, parser validation, metric aggregation, verifier execution, and configured-run transcript handling

Regenerate:

```bash
python benchmarks/real_10/generate.py
```

Run:

```bash
python -m evar.run --cases benchmarks/real_10/cases.jsonl --protocol ar --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/real_10/cases.jsonl --protocol ar_text --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/real_10/cases.jsonl --protocol evar_hard --config configs/openai_pilot.yaml
```

This is still a pilot. The next stronger benchmark should use independent external repositories and real PR-style changes.
