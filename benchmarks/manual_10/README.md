# EVAR Manual 10 Fixture

This is a hand-written fixture for the first dry EVAR experiment.

- 10 cases total
- 5 `SUPPORTED`
- 5 `UNSUPPORTED`
- paired across the five claim families
- no generated benchmark claims
- no prompt tuning

The cases are intentionally tiny local repositories. The current fake-agent runs use the fixture schema and labels for evaluation only; protocol-visible `TaskCase` objects strip ground-truth labels and ground-truth evidence.

Run:

```bash
python -m evar.run --protocol ar --cases benchmarks/manual_10/cases.jsonl > benchmarks/manual_10/results/ar.jsonl
python -m evar.run --protocol ar_text --cases benchmarks/manual_10/cases.jsonl > benchmarks/manual_10/results/ar_text.jsonl
python -m evar.run --protocol evar --cases benchmarks/manual_10/cases.jsonl > benchmarks/manual_10/results/evar.jsonl
python -m evar.eval_table --results benchmarks/manual_10/results/ar.jsonl benchmarks/manual_10/results/ar_text.jsonl benchmarks/manual_10/results/evar.jsonl --bootstrap 10000 --seed 7
```
