# Evidence-Verified Adversarial Review for Code-Review Claims

Project preview: [evar-research.elitelab-ai.chatgpt.site](https://evar-research.elitelab-ai.chatgpt.site) · Development repository: [github.com/kishormorol/evar](https://github.com/kishormorol/evar)

## Abstract

LLM reviewer and critic agents can converge on plausible but unsupported code-review findings when their interaction remains purely textual. We study Evidence-Verified Adversarial Review (EVAR), a protocol that requires structured evidence receipts and deterministic verification before a finding can become actionable. We freeze prompts, evaluator code, verification rules, configs, and 50 commit-grounded claim cases from five Python repositories before running two independent replicates with `gpt-4.1` and `gpt-4.1-mini`. For `gpt-4.1`, EVAR-Hard reduces false consensus rate (FCR) from 0.120 under AR and AR-Text to 0.060, while supported-claim retention (SCR) falls from 1.000 to 0.860. For `gpt-4.1-mini`, EVAR-Hard reduces FCR from 0.160 under AR and 0.120 under AR-Text to 0.041, but SCR falls from 0.980 to 0.420, with one failed model output. Case-clustered paired intervals show the FCR reductions are directionally favorable, while the SCR losses—especially for the smaller model—are substantial. EVAR therefore creates a useful mechanical safety boundary, but current receipt generation and verifier coverage trade false-consensus reduction for missed valid claims.

## 1. Research Question

Can external deterministic verification reduce false consensus between LLM reviewer and critic agents during code review?

We define false consensus as an unsupported candidate claim becoming actionable after reviewer/critic interaction. We also track supported-claim retention to ensure that stricter verification does not simply reject everything.

This work makes five concrete contributions:

1. It defines false consensus as a measurable failure mode for reviewer–critic code-review protocols.
2. It introduces structured evidence receipts and a deterministic actionability gate.
3. It provides a reproducible harness for comparing textual and verification-backed protocols under matched budgets.
4. It provides input and output freeze manifests plus a judge-free transcript audit for a 600-record experiment.
5. It reports synthetic, real-source, and commit-grounded evaluations while separating frozen results from post-hoc development results.

## 2. Protocols

We compare three protocols:

| Protocol | Evidence Handling | Actionability Gate |
| --- | --- | --- |
| AR | Reviewer proposes a finding; critic evaluates textually. | Critic returns `ACCEPT`. |
| AR-Text | Reviewer provides textual evidence; critic evaluates without execution. | Critic returns `ACCEPT`. |
| EVAR-Hard | Reviewer submits a structured `EvidenceReceipt`; verifier checks structural or behavioral evidence; critic evaluates the verified observation. | Verifier returns `VERIFIED` and critic returns `ACCEPT`. |

The EVAR-Hard receipt contains the claim, evidence type, evidence role, referenced file and line range, optional verification command, expected observation, and falsification condition. The evidence role distinguishes evidence intended to support a claim from evidence intended to contradict it. Behavioral witnesses must print `EVAR_WITNESS_PASS` only when the claim is supported.

## 3. Benchmark

The evaluation suite spans synthetic cases, isolated real source, and commit-grounded cases:

| Benchmark | Cases | Source | Claim Construction | Role in Development |
| --- | ---: | --- | --- | --- |
| `manual_50` | 50 | Deterministic synthetic fixtures | Generated from five claim templates | Held out from the original 10-case development loop |
| `real_10` | 10 | Isolated EVAR source files | Hand-authored static claims | Diagnostic |
| `external_10` | 10 | Pinned MarkupSafe and zipp source | Hand-authored static claims | External-source diagnostic |
| `external_pr_10` | 10 | Post-commit MarkupSafe and zipp snapshots | Hand-authored, commit-grounded claims | Development pilot |
| `external_pr_20` | 20 | Pinned MarkupSafe and zipp commits | Hand-authored, commit-grounded claims | Harder held-out check, later inspected for diagnosis |
| `external_pr_50` | 50 | Pinned commits from Click, pluggy, attrs, more-itertools, and Requests | Balanced supported/unsupported claims over exact upstream patches | Frozen primary evaluation |

The primary frozen benchmark is `benchmarks/external_pr_50`. It contains 50 claim cases grounded in 25 public upstream commits. Every source change produces one supported and one unsupported claim about the same exact file-scoped patch. The benchmark is balanced across labels, repositories, and claim families: each of five repositories contributes one claim pair to every family.

The earlier `manual_50` benchmark remains a synthetic diagnostic baseline. The frozen external benchmark has the following structure:

| Property | Count |
| --- | ---: |
| Total cases | 50 |
| Supported claims | 25 |
| Unsupported claims | 25 |
| Claim families | 5 |
| Source repositories | 5 |
| Pinned upstream commits | 25 |
| Cases per family and repository | 10 |

Claim families:

- `behavior_inversion`
- `missing_guard`
- `incorrect_call_relationship`
- `causal_mislocalization`
- `stale_evidence`

The benchmark is regenerated by `benchmarks/external_pr_50/generate.py`. Cloned source histories are excluded from the artifact; each case contains the exact relevant upstream patch. No `external_pr_50` case was used to modify prompts or verifier rules. Before model calls, the artifact hashed all cases, patches, prompts, configs, and evaluator/scoring code at commit `69697c1e04a87094e3d51ba787ecac025fe6382e`.

## 4. Metrics

False Consensus Rate (FCR):

```text
unsupported actionable claims / unsupported completed cases
```

Supported Claim Retention (SCR):

```text
supported actionable claims / supported completed cases
```

Lower FCR is better. Higher SCR is better. Failed runs are reported separately and excluded from both denominators rather than silently counted as decisions or dropped from the result file.

Bootstrap intervals use seeded resampling of eligible completed cases. Paired protocol deltas match records by `case_id` before resampling, preventing unrelated examples from being compared as pairs. These intervals are descriptive because the benchmarks are small and are not random samples from a defined population of code-review tasks.

### 4.1 Analysis and Reproducibility

Each configured run writes one JSONL record per attempted case and a separate transcript. Result records capture protocol, claim family, ground truth, final actionability, verifier status, critic decision, run status, model and prompt configuration, token usage, and end-to-end duration when available. Failures are emitted as explicit records with a failure type and reason.

The analysis CLI reports aggregate FCR/SCR, bootstrap intervals, paired deltas, per-claim-family metrics, and protocol-level token and runtime summaries. The relevant commands are:

```bash
python -m evar.eval_table --results ar.jsonl ar_text.jsonl evar_hard.jsonl \
  --bootstrap 10000 --seed 7 --by-family --costs
```

For the frozen experiment, uncertainty uses 10,000 bootstrap samples with `case_id` as a cluster across the two replicates. Paired deltas match model, replicate label, and case before resampling case clusters. Token counts, end-to-end latency, verifier outcomes, and estimated API cost are reported alongside accuracy metrics.

## 5. Results

### 5.1 Frozen External PR 50 Evaluation

The primary evaluation contains 600 attempted case decisions: 50 cases × 3 protocols × 2 models × 2 replicates. One `gpt-4.1-mini` EVAR-Hard case failed because the reviewer returned truncated invalid JSON; it remains an explicit failed record and is excluded from FCR/SCR denominators. Seeds 7 and 17 are frozen replicate labels, but the Responses API backend did not transmit an explicit inference seed, so they are independent repetitions rather than controlled seeded inference.

| Model | Protocol | n | Failed | FCR (95% cluster CI) | SCR (95% cluster CI) | Verified / failed receipts | Input / output tokens | Mean seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-4.1` | AR | 100 | 0 | 0.120 (0.000–0.280) | 1.000 (1.000–1.000) | 0 / 0 | 156,495 / 17,016 | 2.29 |
| `gpt-4.1` | AR-Text | 100 | 0 | 0.120 (0.020–0.240) | 1.000 (1.000–1.000) | 0 / 0 | 170,374 / 16,272 | 2.30 |
| `gpt-4.1` | EVAR-Hard | 100 | 0 | 0.060 (0.000–0.160) | 0.860 (0.720–0.980) | 76 / 24 | 195,933 / 15,456 | 2.17 |
| `gpt-4.1-mini` | AR | 100 | 0 | 0.160 (0.040–0.320) | 0.980 (0.940–1.000) | 0 / 0 | 154,267 / 14,748 | 3.08 |
| `gpt-4.1-mini` | AR-Text | 100 | 0 | 0.120 (0.000–0.280) | 0.980 (0.940–1.000) | 0 / 0 | 169,699 / 16,401 | 3.25 |
| `gpt-4.1-mini` | EVAR-Hard | 100 | 1 | 0.041 (0.000–0.125) | 0.420 (0.240–0.600) | 47 / 52 | 202,298 / 16,610 | 3.23 |

Paired case-level changes from AR:

| Model | Comparison | ΔFCR (95% cluster CI) | ΔSCR (95% cluster CI) |
| --- | --- | ---: | ---: |
| `gpt-4.1` | AR-Text − AR | 0.000 (−0.060–0.060) | 0.000 (0.000–0.000) |
| `gpt-4.1` | EVAR-Hard − AR | −0.060 (−0.160–0.000) | −0.140 (−0.280–−0.020) |
| `gpt-4.1-mini` | AR-Text − AR | −0.040 (−0.120–0.000) | 0.000 (0.000–0.000) |
| `gpt-4.1-mini` | EVAR-Hard − AR | −0.122 (−0.255–0.000) | −0.560 (−0.740–−0.380) |

The family analysis localizes the tradeoff. EVAR-Hard reaches zero FCR in four of five families for both models; `stale_evidence` remains at FCR = 0.200. With `gpt-4.1`, EVAR-Hard SCR ranges from 0.700 to 1.000 by family. With `gpt-4.1-mini`, SCR is 0.200 for `behavior_inversion` and `missing_guard`, 0.400 for `causal_mislocalization` and `stale_evidence`, and 0.900 for `incorrect_call_relationship`.

### 5.2 GPT-4.1 Mini, Three Synthetic 50-Case Repetitions

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

### 5.3 GPT-4.1, Synthetic 50 Cases

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 50 | 50 | 0 | 0.040 | 0.000 | 0.120 | 0.960 | 0.880 | 1.000 |
| AR-Text | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 0.920 | 0.800 | 1.000 |
| EVAR-Hard | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260828T203024Z-16682391_ar.jsonl`
- `results/20260828T203246Z-fb1d8e13_ar_text.jsonl`
- `results/20260828T203836Z-f25cfab0_evar_hard.jsonl`

### 5.4 GPT-4.1 Mini, Real-Code 10-Case Pilot

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

### 5.5 GPT-4.1 Mini, External-Source 10-Case Pilot

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

### 5.6 GPT-4.1 Mini, External PR-Style 10-Case Pilot

This pilot uses post-commit source snapshots from MarkupSafe and zipp at pinned commits. It is more realistic than `external_10` because claims are grounded in real commits, but it still uses hand-authored candidate claims rather than actual pull-request comments.

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 10 | 10 | 0 | 0.800 | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 |
| AR-Text | 10 | 10 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| EVAR-Hard | 10 | 10 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260829T003248Z-5934bedd_ar.jsonl`
- `results/20260829T003248Z-32311376_ar_text.jsonl`
- `results/20260829T010200Z-0439f1c0_evar_hard.jsonl`

### 5.7 GPT-4.1 Mini, External PR-Style 20-Case Benchmark

This benchmark expands the commit-grounded setup to 20 cases from pinned MarkupSafe and zipp commits. It was added after the `external_pr_10` diagnostic loop and served as an earlier held-out development check before the frozen primary evaluation.

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 20 | 20 | 0 | 0.300 | 0.000 | 0.600 | 1.000 | 1.000 | 1.000 |
| AR-Text | 20 | 20 | 0 | 0.100 | 0.000 | 0.300 | 0.900 | 0.700 | 1.000 |
| EVAR-Hard | 20 | 20 | 0 | 0.100 | 0.000 | 0.300 | 0.900 | 0.700 | 1.000 |

Result files:

- `results/20260829T012754Z-df38f2c4_ar.jsonl`
- `results/20260829T012754Z-2c097164_ar_text.jsonl`
- `results/20260829T012754Z-76523fa1_evar_hard.jsonl`

Post-fix diagnostic EVAR-Hard result after receipt repair and additional structural checks:

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EVAR-Hard + receipt repair | 20 | 20 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result file:

- `results/20260829T020606Z-de7afb35_evar_hard.jsonl`

## 6. Interpretation

The frozen external evaluation gives a less flattering and more useful result than the earlier synthetic benchmarks. EVAR-Hard reduces unsupported acceptance for both models, but it does not dominate the textual baselines. With `gpt-4.1`, the FCR improvement is accompanied by a moderate 0.140 absolute SCR loss. With `gpt-4.1-mini`, the FCR improvement is accompanied by a 0.560 paired SCR loss. The actionability gate is working as designed; the weak link is whether the reviewer can construct a receipt that the deterministic verifier can validate.

Model capability changes that balance. `gpt-4.1` produces 76 verified receipts across 100 cases, compared with 47 verified receipts across 99 completed mini cases. Consequently, EVAR-Hard retains 86% of supported claims with `gpt-4.1` but only 42% with the mini model. The result argues against treating verification as a model-independent wrapper: receipt generation quality and verifier coverage jointly determine the operating point.

Per-family results further reject a universal benefit claim. EVAR eliminates observed false consensus in four families but not `stale_evidence`. Retention losses concentrate in behavior, guard, and causal-localization claims, while explicit call relationships are comparatively easy to verify. These patterns are descriptive—the family denominators remain only 20 attempted records each—but they provide concrete targets for development on a separate future split.

In the earlier synthetic `gpt-4.1` comparison, EVAR-Hard retained all supported claims while rejecting all unsupported claims. AR-Text also avoided false positives but missed two supported claims, while AR retained most supported claims but admitted one unsupported claim. The frozen external result demonstrates that this synthetic operating point did not generalize unchanged.

In the `gpt-4.1-mini` repeated runs, both AR-Text and EVAR-Hard avoid false consensus and achieve similar supported-claim retention. This suggests that textual evidence alone may be sufficient for this synthetic benchmark, while deterministic verification becomes more useful as model behavior or case ambiguity changes.

The most important positive signal is not just EVAR-Hard's final score, but the failure mode it enforces: a claim cannot become actionable unless evidence is mechanically checked. During development, this exposed errors in command parsing, structural matching, and critic interpretation of counterevidence.

The EVAR-source real-code pilot gives a stronger diagnostic signal than the synthetic benchmark. AR and AR-Text accepted all five supported claims, but also admitted two unsupported claims. EVAR-Hard retained all five supported claims and rejected all five unsupported claims after adding evidence roles, path recovery, import-complete fixtures, and targeted structural checks.

The external-source pilot is a small independence check. EVAR-Hard again retained all supported claims and rejected all unsupported claims; AR also scored perfectly in this run, while AR-Text admitted one unsupported claim. The sample is too small for a broad claim, but it confirms that the harness can run against source outside EVAR.

The external PR-style pilot is harder and more informative. AR and AR-Text retained supported claims but over-accepted unsupported claims. EVAR-Hard retained supported claims and rejected unsupported claims after increasing repository context coverage, adding valid file-path lists to reviewer prompts, copying import dependencies into isolated fixtures, and expanding AST structural checks.

The 20-case commit-grounded benchmark is the current best stress test. Initially, EVAR-Hard and AR-Text both reduced FCR compared with AR, but neither dominated: both had FCR = 0.100 and SCR = 0.900. The EVAR-Hard misses exposed four development targets: distinguishing docstring examples from semantic support, checking evaluation order rather than only verifying that a condition string exists, preferring structural checks over fragile one-line witnesses for visible code facts, and repairing receipt roles when deterministic AST checks observe the opposite of the submitted role. A diagnostic repair pass on the inspected benchmark reached FCR = 0.000 and SCR = 1.000, but this should be treated as harness-development evidence rather than a fresh held-out result.

## 7. Threats to Validity

The frozen `external_pr_50` benchmark improves repository diversity and prevents post-hoc prompt or verifier tuning on its cases, but it is still hand-authored. Claims are constructed from real commits rather than sampled from human review comments, and each case presents a focused file-scoped patch rather than a full repository checkout. Supported and unsupported claims share the same patch, which controls evidence but may make classification easier than open-ended review.

The two configured seeds are replicate labels only. The backend did not send a seed parameter to the OpenAI Responses API, so the study has independent repeated calls but not controlled seeded inference. One mini EVAR output failed JSON parsing. Four additional attempts were excluded under an infrastructure rule because DNS, concurrent throttling, or exhausted credits caused widespread request failures; the raw excluded records and reasons remain in the artifact.

The earlier `manual_50` benchmark is synthetic and templated. Even though it was held out from the original 10-case tuning loop, the cases share simple patterns and short files. The `real_10` and `external_10` pilots are closer to real code, but they remain small and use hand-authored static claims. The `external_pr_10` pilot is commit-grounded but was inspected during harness development, so it should be treated as diagnostic rather than held-out evidence. The `external_pr_20` benchmark is a stronger held-out check, but it is still small and limited to two source projects. Results should not be presented as evidence of real-world code-review performance without a larger benchmark based on human review claims.

Prompts were improved after observing failures on the earlier development benchmarks. Those changes were frozen before `external_pr_50`; they nevertheless weaken claims about prompt-independent generalization beyond the frozen evaluation.

The sample size remains small for statistical claims. Bootstrap intervals are useful as descriptive uncertainty checks, but stronger claims require more diverse cases and independent repetitions.

The verifier is specialized to Python and to a limited set of structural and behavioral claim patterns. Some successful checks use targeted AST logic added after observing development failures. This improves the harness but means performance can reflect verifier coverage as much as protocol quality.

The 20-case receipt-repair result is explicitly post-hoc. The same benchmark informed the repair logic, so the repaired score measures whether the diagnosed failures were corrected, not whether the correction generalizes.

The study does not include human reviewers, production pull-request comments, repository-scale dependency graphs, or a calibrated estimate of review utility. It measures acceptance of pre-specified candidate claims, not end-to-end bug discovery.

## 8. Next Work

The next research-quality step is to create a separate development split for receipt-generation and verifier improvements, leaving `external_pr_50` permanently frozen. Development should target the observed retention failures—especially behavior, guard, causal-localization, and stale-evidence receipts—without adding claim-specific checks from the frozen set. A subsequent evaluation should sample actual pull-request comments, include multi-file context and tests, and use a newly untouched repository set.

Additional useful extensions:

- Increase per-family sample sizes and repository diversity.
- Compare additional models and verifier-independent receipt generators.
- Add explicit retry and failed-row metadata policies before the next freeze.
- Add richer structural verifiers for common Python review claims.

## 9. Conclusion

EVAR changes the acceptance rule for adversarial code review: reviewer–critic agreement is necessary but insufficient; a finding must also survive an external evidence check. In the frozen external evaluation, this gate reduces unsupported actionable claims for both models, but it also rejects supported claims. The cost is moderate with `gpt-4.1` and severe with `gpt-4.1-mini`, demonstrating that EVAR is only as reliable as its receipt generation and verification coverage.

The strongest conclusion remains procedural rather than a claim of universal performance advantage. Mechanically checked evidence creates an auditable safety boundary and can lower false consensus, but verification is not free: weak or unverifiable receipts suppress valid findings. Establishing a better operating point requires verifier and receipt work on a separate development split, followed by evaluation on new human-authored review claims.

## 10. Artifact Availability

The project site summarizes the protocol, evidence, limitations, and reproduction path: [EVAR research site](https://evar-research.elitelab-ai.chatgpt.site).

The site and repository are access-controlled during development. A public paper release should archive the exact evaluated artifact and result files at a stable public identifier.

The repository contains protocol implementations, prompts, benchmark fixtures, canonical results, transcripts, audit reports, and analysis tools. `benchmarks/external_pr_50/freeze_manifest.json` hashes the 105 frozen inputs. `benchmarks/external_pr_50/results_manifest.json` hashes 820 result artifacts, including 12 canonical JSONL runs and 600 canonical transcripts. `run_index.json` identifies scored and excluded attempts, and `audit_report.json` records the judge-free audit findings.

The core deterministic checks run with:

```bash
python -m unittest discover -s tests
python -m evar.demo_compare
```

Model-backed experiments require an explicit configuration and API credentials. The artifact records replicate labels, prompt hashes, model settings, per-case failures, token usage, duration, and transcripts to support auditing and later replication.
