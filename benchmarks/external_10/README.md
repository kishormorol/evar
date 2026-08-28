# External 10 Pilot Benchmark

This benchmark is a first independent-code pilot. It uses small copied source files from public Python repositories, with fixed supported and unsupported candidate review claims.

Source provenance:

| Source | Repository | Commit |
| --- | --- | --- |
| MarkupSafe | `https://github.com/pallets/markupsafe` | `b2e4d9c7687be25695fffbe93a37622302b24fb1` |
| zipp | `https://github.com/jaraco/zipp` | `29a7a55c6bac1a6f705b54135dbea82d03e997c3` |

Composition:

- 10 cases total
- 5 supported claims
- 5 unsupported claims
- Claims cover escaping, argument normalization, method-wrapper state, and glob translation behavior

Regenerate:

```bash
gh repo clone pallets/markupsafe benchmarks/external_10/sources/markupsafe
gh repo clone jaraco/zipp benchmarks/external_10/sources/zipp
python benchmarks/external_10/generate.py
```

Run:

```bash
python -m evar.run --cases benchmarks/external_10/cases.jsonl --protocol ar --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/external_10/cases.jsonl --protocol ar_text --config configs/openai_pilot.yaml
python -m evar.run --cases benchmarks/external_10/cases.jsonl --protocol evar_hard --config configs/openai_pilot.yaml
```

This remains a pilot. The next step is to build external cases from actual commits or pull requests, not only static source-file claims.
