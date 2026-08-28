# Real 10 Pilot Results

Date: 2026-08-28

This pilot benchmark uses isolated copies of real EVAR source files. It is less templated than `manual_50`, but still drawn from this repository rather than independent external projects.

## GPT-4.1 Mini

Result files:

- `results/20260828T210900Z-6c2ef540_ar.jsonl`
- `results/20260828T210939Z-6efa3ef2_ar_text.jsonl`
- `results/20260828T212156Z-0b4d5875_evar_hard.jsonl`

Bootstrap summary:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ar | 10 | 10 | 0 | 0.400 | 0.000 | 0.800 | 1.000 | 1.000 | 1.000 |
| ar_text | 10 | 10 | 0 | 0.400 | 0.000 | 0.800 | 1.000 | 1.000 | 1.000 |
| evar_hard | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

The synthetic `manual_50` benchmark did not fully predict performance on this real-code pilot. After adding evidence roles, path recovery, import-complete fixtures, and targeted structural checks, EVAR-Hard rejected every unsupported claim while retaining every supported claim in this 10-case pilot.

The failures are useful:

- Real source files are longer and noisier than the synthetic fixtures.
- AR and AR-Text admitted two unsupported claims, showing that textual review remains vulnerable on more realistic code.
- EVAR-Hard correctly rejected the two unsupported claims accepted by AR and AR-Text.
- Receipt quality still matters: earlier pilot runs missed supported cases when generated receipts used imprecise paths, stale snippets, or behavioral witnesses that could not import isolated dependencies.
- The latest run completed all cases after fixture and verifier improvements.

This should be treated as a pilot diagnostic, not a paper-grade result. The next step is to improve receipt generation on a development split, then expand this into an independent external-repository benchmark without tuning on the evaluation cases.
