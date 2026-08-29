# Evidence-Verified Adversarial Review for Code-Review Claims

## Abstract

LLM reviewer and critic agents can converge on plausible but unsupported code-review findings when their interaction remains purely textual. We study Evidence-Verified Adversarial Review (EVAR), a protocol that requires reviewer agents to attach structured evidence receipts and routes those receipts through deterministic verification before a finding can become actionable. On a held-out 50-case synthetic code-review benchmark, EVAR-Hard with `gpt-4.1` achieved zero false consensus rate (FCR = 0.000) and perfect supported-claim retention (SCR = 1.000). In three `gpt-4.1-mini` repetitions, EVAR-Hard matched AR-Text on mean SCR (0.987) while preserving zero mean FCR. Two 10-case real-code pilots reached FCR = 0.000 and SCR = 1.000 for EVAR-Hard after verifier improvements. A harder commit-grounded external pilot exposed the current limitation: EVAR-Hard reduced false consensus relative to textual protocols but rejected many supported claims due to weak receipts. These results suggest that executable or mechanically checked evidence can make reviewer/critic agreement more reliable, but receipt generation and verifier coverage are now the main bottlenecks.

## 1. Research Question

Can external deterministic verification reduce false consensus between LLM reviewer and critic agents during code review?

We define false consensus as an unsupported candidate claim becoming actionable after reviewer/critic interaction. We also track supported-claim retention to ensure that stricter verification does not simply reject everything.

## 2. Protocols

We compare three protocols:

| Protocol | Evidence Handling | Actionability Gate |
| --- | --- | --- |
| AR | Reviewer proposes a finding; critic evaluates textually. | Critic returns `ACCEPT`. |
| AR-Text | Reviewer provides textual evidence; critic evaluates without execution. | Critic returns `ACCEPT`. |
| EVAR-Hard | Reviewer submits a structured `EvidenceReceipt`; verifier checks structural or behavioral evidence; critic evaluates the verified observation. | Verifier returns `VERIFIED` and critic returns `ACCEPT`. |

The EVAR-Hard receipt contains the claim, evidence type, evidence role, referenced file and line range, optional verification command, expected observation, and falsification condition. The evidence role distinguishes evidence intended to support a claim from evidence intended to contradict it. Behavioral witnesses must print `EVAR_WITNESS_PASS` only when the claim is supported.

## 3. Benchmark

The held-out benchmark is `benchmarks/manual_50`.

It contains 50 synthetic code-review claim cases:

| Property | Count |
| --- | ---: |
| Total cases | 50 |
| Supported claims | 25 |
| Unsupported claims | 25 |
| Claim families | 5 |
| Cases per family | 10 |

Claim families:

- `behavior_inversion`
- `missing_guard`
- `incorrect_call_relationship`
- `causal_mislocalization`
- `stale_evidence`

The benchmark is generated deterministically by `benchmarks/manual_50/generate.py`. It is held out from the earlier 10-case development loop, but it is still synthetic and templated.

## 4. Metrics

False Consensus Rate (FCR):

```text
unsupported actionable claims / unsupported completed cases
```

Supported Claim Retention (SCR):

```text
supported actionable claims / supported completed cases
```

Lower FCR is better. Higher SCR is better.

## 5. Results

### 5.1 GPT-4.1 Mini, Three 50-Case Repetitions

| Protocol | Run | FCR | SCR | Failed |
| --- | --- | ---: | ---: | ---: |
| AR | `20260828T195616Z-1d981ab2_ar.jsonl` | 0.000 | 0.760 | 0 |
| AR | `20260828T201243Z-08dbded7_ar.jsonl` | 0.000 | 0.880 | 0 |
| AR | `20260828T202102Z-02d07946_ar.jsonl` | 0.000 | 0.800 | 0 |
| AR-Text | `20260828T195904Z-722800e2_ar_text.jsonl` | 0.000 | 1.000 | 0 |
| AR-Text | `20260828T201526Z-9047089d_ar_text.jsonl` | 0.000 | 0.960 | 0 |
| AR-Text | `20260828T204106Z-eb60f7d6_ar_text.jsonl` | 0.000 | 1.000 | 0 |
| EVAR-Hard | `20260828T200932Z-6ce44436_evar_hard.jsonl` | 0.000 | 1.000 | 0 |
| EVAR-Hard | `20260828T201808Z-9d0bce07_evar_hard.jsonl` | 0.000 | 1.000 | 0 |
| EVAR-Hard | `20260828T202702Z-995e84e0_evar_hard.jsonl` | 0.000 | 0.960 | 0 |

Mean results:

| Protocol | Mean FCR | Mean SCR |
| --- | ---: | ---: |
| AR | 0.000 | 0.813 |
| AR-Text | 0.000 | 0.987 |
| EVAR-Hard | 0.000 | 0.987 |

### 5.2 GPT-4.1, 50 Cases

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 50 | 50 | 0 | 0.040 | 0.000 | 0.120 | 0.960 | 0.880 | 1.000 |
| AR-Text | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 0.920 | 0.800 | 1.000 |
| EVAR-Hard | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260828T203024Z-16682391_ar.jsonl`
- `results/20260828T203246Z-fb1d8e13_ar_text.jsonl`
- `results/20260828T203836Z-f25cfab0_evar_hard.jsonl`

### 5.3 GPT-4.1 Mini, Real-Code 10-Case Pilot

This pilot uses isolated copies of EVAR source files. It is more realistic than `manual_50`, but it is still drawn from the same repository and should be treated as diagnostic rather than paper-grade evidence.

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 10 | 10 | 0 | 0.400 | 0.000 | 0.800 | 1.000 | 1.000 | 1.000 |
| AR-Text | 10 | 10 | 0 | 0.400 | 0.000 | 0.800 | 1.000 | 1.000 | 1.000 |
| EVAR-Hard | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260828T210900Z-6c2ef540_ar.jsonl`
- `results/20260828T210939Z-6efa3ef2_ar_text.jsonl`
- `results/20260828T212156Z-0b4d5875_evar_hard.jsonl`

### 5.4 GPT-4.1 Mini, External-Source 10-Case Pilot

This pilot uses isolated copies of source files from MarkupSafe and zipp at pinned commits. It is independent of EVAR source code, but still uses hand-authored static claims rather than real pull-request review comments.

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| AR-Text | 10 | 10 | 0 | 0.200 | 0.000 | 0.600 | 1.000 | 1.000 | 1.000 |
| EVAR-Hard | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260828T225009Z-c44d58a8_ar.jsonl`
- `results/20260828T225009Z-05a32dc4_ar_text.jsonl`
- `results/20260828T225243Z-be058cc5_evar_hard.jsonl`

### 5.5 GPT-4.1 Mini, External PR-Style 10-Case Pilot

This pilot uses post-commit source snapshots from MarkupSafe and zipp at pinned commits. It is more realistic than `external_10` because claims are grounded in real commits, but it still uses hand-authored candidate claims rather than actual pull-request comments.

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 10 | 10 | 0 | 0.800 | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 |
| AR-Text | 10 | 10 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| EVAR-Hard | 10 | 10 | 0 | 0.200 | 0.000 | 0.600 | 0.200 | 0.000 | 0.600 |

Result files:

- `results/20260829T003248Z-5934bedd_ar.jsonl`
- `results/20260829T003248Z-32311376_ar_text.jsonl`
- `results/20260829T003248Z-19464e26_evar_hard.jsonl`

## 6. Interpretation

EVAR-Hard is strongest in the `gpt-4.1` comparison: it retains all supported claims while rejecting all unsupported claims. AR-Text also avoids false positives, but misses two supported claims. AR retains most supported claims but admits one unsupported claim.

In the `gpt-4.1-mini` repeated runs, both AR-Text and EVAR-Hard avoid false consensus and achieve similar supported-claim retention. This suggests that textual evidence alone may be sufficient for this synthetic benchmark, while deterministic verification becomes more useful as model behavior or case ambiguity changes.

The most important positive signal is not just EVAR-Hard's final score, but the failure mode it enforces: a claim cannot become actionable unless evidence is mechanically checked. During development, this exposed errors in command parsing, structural matching, and critic interpretation of counterevidence.

The EVAR-source real-code pilot gives a stronger diagnostic signal than the synthetic benchmark. AR and AR-Text accepted all five supported claims, but also admitted two unsupported claims. EVAR-Hard retained all five supported claims and rejected all five unsupported claims after adding evidence roles, path recovery, import-complete fixtures, and targeted structural checks.

The external-source pilot is a small independence check. EVAR-Hard again retained all supported claims and rejected all unsupported claims; AR also scored perfectly in this run, while AR-Text admitted one unsupported claim. The sample is too small for a broad claim, but it confirms that the harness can run against source outside EVAR.

The external PR-style pilot is harder and more informative. AR and AR-Text retained supported claims but over-accepted unsupported claims. EVAR-Hard reduced false consensus, but its SCR fell because reviewer-generated receipts often cited wrong files, stale snippets, or true observations that did not support the stronger candidate claim. This suggests that the next research problem is not merely adding verification, but making receipt generation precise enough for real commit-level review.

## 7. Threats to Validity

The primary benchmark is synthetic and templated. Even though `manual_50` was held out from the original 10-case tuning loop, the cases share simple patterns and short files. The `real_10` and `external_10` pilots are closer to real code, but they remain small and use hand-authored static claims. The `external_pr_10` pilot is commit-grounded but was inspected during harness development, so it should be treated as diagnostic rather than held-out evidence. Results should not be presented as evidence of real-world code-review performance without a larger benchmark based on real repository changes.

Prompts were improved after observing failures on the development benchmark and during held-out analysis. This is appropriate for harness development but weakens claims about prompt-independent generalization.

The sample size remains small for statistical claims. Bootstrap intervals are useful as descriptive uncertainty checks, but stronger claims require more diverse cases and independent repetitions.

## 8. Next Work

The next research-quality step is to build a real-repository benchmark from actual commits or pull requests. Cases should include multi-file reasoning, test behavior, misleading comments, stale diffs, hidden call chains, and realistic reviewer claims. Receipt generation should be improved on a development split, then EVAR should be evaluated without further prompt tuning on the held-out external set.

Additional useful extensions:

- Add per-family result tables.
- Track token cost and latency per protocol.
- Compare more models.
- Add a judge-free transcript audit report.
- Add richer structural verifiers for common Python review claims.
