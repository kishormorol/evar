# External PR 10 Pilot Benchmark

This benchmark is a first PR-style external-code pilot. Each case is grounded in a real public repository commit and asks whether a candidate review claim is supported by the post-commit source snapshot.

Source provenance:

| Source | Repository | Commits |
| --- | --- | --- |
| MarkupSafe | `https://github.com/pallets/markupsafe` | `0b6bee071fbd8d3171fb1ac4fb669baace808438` |
| zipp | `https://github.com/jaraco/zipp` | `84be2a5570778549503492d094f40a7203197bb2`, `d860de467a5887a6f09e5b66e4ef51f2e9c516fa`, `3503c8b2e47f28eb49aad9ddb4f5c002146404ad`, `f89b93f0370dd85d23d243e25dfc1f99f4d8de48` |

Composition:

- 10 cases total
- 5 supported claims
- 5 unsupported claims
- Cases are paired around real commits so each supported claim has a nearby unsupported alternative.

Regenerate:

```bash
gh repo clone pallets/markupsafe benchmarks/external_10/sources/markupsafe
gh repo clone jaraco/zipp benchmarks/external_10/sources/zipp
python benchmarks/external_pr_10/generate.py
```

Run:

```bash
python -m evar.run --cases benchmarks/external_pr_10/cases.jsonl --protocol ar --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/external_pr_10/cases.jsonl --protocol ar_text --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/external_pr_10/cases.jsonl --protocol evar_hard --config configs/openai_pilot.yaml
```

This is still a pilot. A stronger version should include the actual before/after diff, linked tests, and larger multi-file changes.
