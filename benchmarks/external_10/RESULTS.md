# External 10 Pilot Results

Date: 2026-08-28

This pilot benchmark uses isolated copies of source files from public Python repositories outside EVAR. It is more independent than `real_10`, but still uses hand-authored static claims rather than full pull-request changes.

## GPT-4.1 Mini

Result files:

- `results/20260828T225009Z-c44d58a8_ar.jsonl`
- `results/20260828T225009Z-05a32dc4_ar_text.jsonl`
- `results/20260828T225243Z-be058cc5_evar_hard.jsonl`

Bootstrap summary:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ar | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| ar_text | 10 | 10 | 0 | 0.200 | 0.000 | 0.600 | 1.000 | 1.000 | 1.000 |
| evar_hard | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

EVAR-Hard retained all supported claims and rejected all unsupported claims on this small external-source pilot. AR also scored perfectly in this run, while AR-Text admitted one unsupported claim.

The diagnostic failures during development were useful:

- Models may quote equivalent Python snippets with different string delimiters.
- A verified comment or docstring can be insufficient support when the code contradicts a stronger claim.
- Some source slices need dependency files included so behavioral witnesses can import the target module.

This benchmark is a bridge, not the final evidence. The next step is an external pull-request benchmark where each case is grounded in a real change, review claim, and executable validation command.
