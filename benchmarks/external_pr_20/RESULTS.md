# External PR 20 Results

Date: 2026-08-28

This benchmark expands the commit-grounded pilot to 20 cases from pinned public repository commits. It was added after the `external_pr_10` diagnostic loop and should be treated as the current harder held-out check.

## GPT-4.1 Mini

Result files:

- `results/20260829T012754Z-df38f2c4_ar.jsonl`
- `results/20260829T012754Z-2c097164_ar_text.jsonl`
- `results/20260829T012754Z-76523fa1_evar_hard.jsonl`

Bootstrap summary:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ar | 20 | 20 | 0 | 0.300 | 0.000 | 0.600 | 1.000 | 1.000 | 1.000 |
| ar_text | 20 | 20 | 0 | 0.100 | 0.000 | 0.300 | 0.900 | 0.700 | 1.000 |
| evar_hard | 20 | 20 | 0 | 0.100 | 0.000 | 0.300 | 0.900 | 0.700 | 1.000 |

## Interpretation

The 20-case commit-grounded benchmark is harder than the smaller pilots. EVAR-Hard and AR-Text both reduce false consensus relative to AR, but each misses one supported claim.

EVAR-Hard errors:

- Supported case 9: the reviewer declared contradicting evidence for a supported `_ancestry` separator claim after over-reading a docstring example.
- Unsupported case 12: the structural verifier accepted the observed condition `zip_mode == 'r' and not self.exists()`, but the candidate claim was about evaluation order and should have been rejected.

This is the best current target for improvement: add development cases for evaluation-order semantics and confusing docstring/code disagreement, then rerun this 20-case benchmark without direct tuning.

## Post-Fix EVAR-Hard Diagnostic

After adding AST checks for `Path.open` evaluation order, `Translator.translate` call-chain wrapping, and `Path.is_symlink` external-attribute handling, plus blank-falsification defaults and deterministic receipt-role repair, EVAR-Hard was rerun on the same 20 cases:

- `results/20260829T020606Z-de7afb35_evar_hard.jsonl`

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| evar_hard | 20 | 20 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

The diagnostic repair pass removed the evaluation-order false positive and recovered all supported claims in this run. This is a development result on an already inspected benchmark, so it should not be treated as fresh held-out evidence. The next evidence needed is an independent larger commit benchmark that is not used during verifier or prompt tuning.
