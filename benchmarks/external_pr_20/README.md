# External PR 20 Benchmark

This benchmark expands the commit-grounded pilot to 20 cases from pinned public repository commits. Each pair asks one supported and one unsupported review-style claim about a post-commit source snapshot.

Source provenance:

| Source | Repository | Commits |
| --- | --- | --- |
| MarkupSafe | `https://github.com/pallets/markupsafe` | `0b6bee071fbd8d3171fb1ac4fb669baace808438`, `e49d257126d09937b1bf5e2b2173238df729fb13`, `3d809aed7b7b6af5c371bab68666857087335af9` |
| zipp | `https://github.com/jaraco/zipp` | `84be2a5570778549503492d094f40a7203197bb2`, `d860de467a5887a6f09e5b66e4ef51f2e9c516fa`, `3503c8b2e47f28eb49aad9ddb4f5c002146404ad`, `f89b93f0370dd85d23d243e25dfc1f99f4d8de48`, `71ddd8d4f4ab200af870f0060d9ee8c6b7056681`, `5d89a1cf540894ef28c0b6485daf01c860bd59d0`, `dc5fe8f4dd31e551f9bf76b5403e64f06f72a0c7` |

Regenerate:

```bash
gh repo clone pallets/markupsafe benchmarks/external_10/sources/markupsafe
gh repo clone jaraco/zipp benchmarks/external_10/sources/zipp
python benchmarks/external_pr_20/generate.py
```

Run:

```bash
python -m evar.run --cases benchmarks/external_pr_20/cases.jsonl --protocol ar --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/external_pr_20/cases.jsonl --protocol ar_text --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/external_pr_20/cases.jsonl --protocol evar_hard --config configs/openai_pilot.yaml
```
