# Evidence-Verified Adversarial Review for Code-Review Claims

Project preview: [evar-research.elitelab-ai.chatgpt.site](https://evar-research.elitelab-ai.chatgpt.site) · Development repository: [github.com/kishormorol/evar](https://github.com/kishormorol/evar)

## Abstract

LLM reviewer and critic agents can converge on plausible but unsupported code-review findings when their interaction remains purely textual. We study Evidence-Verified Adversarial Review (EVAR), a protocol that requires structured evidence receipts and deterministic verification before a finding can become actionable. After a 600-record frozen experiment exposed severe supported-claim loss, we improved receipt generation only on a separate development split and evaluated once on Human PR 20: ten real human pull-request review comments paired across their reviewed and merge commits, producing 20 balanced cases from five previously unseen Python repositories. In the original 120-decision study, EVAR-Hard tied AR-Text with `gpt-4.1-mini` and trailed it with `gpt-4.1`. A pre-specified post-release model extension added 180 audited decisions from `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol` at explicit reasoning effort `none`. Descriptively pooling those three models, EVAR-Hard achieved FCR 0.067 and SCR 0.700, compared with 0.100/0.667 for AR-Text and 0.100/0.767 for AR, but model-level results were heterogeneous and all intervals were wide. EVAR therefore does not demonstrate universal performance dominance. Its contribution is an auditable acceptance boundary and reproducible evidence that verification changes, rather than uniformly improves, the safety-retention operating point.

## 1. Research Question

Can external deterministic verification reduce false consensus between LLM reviewer and critic agents during code review?

We define false consensus as an unsupported candidate claim becoming actionable after reviewer/critic interaction. We also track supported-claim retention to ensure that stricter verification does not simply reject everything.

This work makes six concrete contributions:

1. It defines false consensus as a measurable failure mode for reviewer–critic code-review protocols.
2. It introduces structured evidence receipts and a deterministic actionability gate.
3. It provides a reproducible harness for comparing textual and verification-backed protocols under matched budgets.
4. It provides input and output freeze manifests plus judge-free transcript audits for 900 model decisions.
5. It introduces a temporal holdout derived from real human review comments across previously unseen repositories.
6. It reports a mixed, non-dominance result across five evaluated models while separating the untouched study, exploratory model extension, development diagnostics, and post-hoc interpretation.

### 1.1 Related Work

EVAR builds on iterative critique and multi-agent deliberation but changes the acceptance condition. Self-Refine demonstrates that model-generated feedback can improve a model's own outputs across tasks [1], while multi-agent debate uses multiple model instances to improve reasoning and factuality through textual exchange [2]. Neither result implies that agreement is independently grounded. EVAR instead makes a verified external observation a necessary condition for actionability.

For software-engineering evaluation, SWE-bench grounds tasks in real GitHub issues and pull requests and highlights the need for repository context and executable environments [3]. More recent code-review work evaluates models against human pull-request feedback and reports low detection of human-flagged issues [4]. EVAR studies a narrower question: given a pre-specified candidate review claim, does an evidence gate prevent unsupported reviewer-critic consensus without discarding supported claims?

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
| `development_external_pr_20` | 20 | Inspected MarkupSafe and zipp commits | Existing balanced development cases | Receipt-format development only |
| `human_pr_20` | 20 | Ten human review comments from Black, pytest, Rich, Pydantic, and Poetry | Temporal reviewed-commit/merge-commit pairs | Untouched final evaluation |

The first primary frozen benchmark is `benchmarks/external_pr_50`. It contains 50 claim cases grounded in 25 public upstream commits. Every source change produces one supported and one unsupported claim about the same exact file-scoped patch. The benchmark is balanced across labels, repositories, and claim families: each of five repositories contributes one claim pair to every family.

After inspecting that benchmark's receipt failures, no code or prompt change was evaluated against it again. EVAR v2 was developed on the separate `development_external_pr_20` split. The final `human_pr_20` evaluation was then generated from ten review comments written by non-bot GitHub users. For each comment, the code at the reviewed commit supports the comment's claim and the merged commit no longer does, yielding a controlled temporal pair. The 20 cases are balanced by label, span five repositories absent from `external_pr_50`, preserve exact public provenance, include a changed target excerpt plus a companion changed-file excerpt when available, and remain below 30 KB of context per case. Evaluator code, prompts, configs, and cases were frozen before the first model call.

After the original Human PR 20 study was publicly released, we specified an exploratory model-extension protocol before making any benchmark calls. The unchanged cases, prompts, verifier semantics, and scoring were evaluated with three current model tiers: `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`. All used explicit `reasoning.effort: none`, one run per protocol, identical budgets, and seed 41 as a provenance label. The extension required one transport-level backend change: omit the unsupported `temperature` parameter for these models. This change and the three configs were frozen at commit `9a72f36`; it did not change prompts, verification, or scoring.

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

### 5.1 Untouched Human PR 20 Evaluation

The final holdout contains 20 cases constructed from ten real human pull-request review comments. Each comment forms a temporal pair: the claim is supported at the commit the reviewer saw and unsupported at the merged commit where the relevant code was changed. Five repositories are represented, none used by `external_pr_50`. Each of two models ran AR, AR-Text, and EVAR-Hard exactly once, for 120 attempted decisions and no run failures. The integer seed is a provenance label, not a claim of deterministic API sampling.

| Model | Protocol | n | Failed | FCR (95% cluster CI) | SCR (95% cluster CI) | Verified / failed receipts | Estimated API cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-4.1` | AR | 20 | 0 | 0.400 (0.100-0.700) | 0.700 (0.400-1.000) | 0 / 0 | $0.136 |
| `gpt-4.1` | AR-Text | 20 | 0 | 0.200 (0.000-0.500) | 0.700 (0.400-1.000) | 0 / 0 | $0.143 |
| `gpt-4.1` | EVAR-Hard | 20 | 0 | 0.300 (0.000-0.600) | 0.600 (0.300-0.900) | 18 / 2 | $0.145 |
| `gpt-4.1-mini` | AR | 20 | 0 | 0.400 (0.100-0.700) | 0.900 (0.700-1.000) | 0 / 0 | $0.027 |
| `gpt-4.1-mini` | AR-Text | 20 | 0 | 0.200 (0.000-0.500) | 0.700 (0.400-1.000) | 0 / 0 | $0.029 |
| `gpt-4.1-mini` | EVAR-Hard | 20 | 0 | 0.200 (0.000-0.500) | 0.700 (0.400-1.000) | 18 / 2 | $0.030 |

Paired changes from AR are modest and uncertain. For `gpt-4.1-mini`, AR-Text and EVAR-Hard have identical outcomes: delta FCR = -0.200 (95% CI -0.500 to 0.000) and delta SCR = -0.200 (-0.500 to 0.000). For `gpt-4.1`, AR-Text improves FCR by -0.200 with no SCR change, while EVAR-Hard improves FCR by only -0.100 and reduces SCR by -0.100. Thus the holdout provides no evidence that EVAR-Hard dominates the simpler text-evidence baseline.

The v2 receipt format verifies 18 of 20 receipts for each model, a large diagnostic improvement over the earlier mini-model frozen run. This is not a causal comparison: `human_pr_20` differs in repositories, claims, context construction, and sample size. The full 120-record audit found no run failures, prompt-hash mismatch, transcript-integrity error, gate inconsistency, token inconsistency, or latency inconsistency.

### 5.2 Exploratory GPT-5.6 Model Extension

The post-release extension evaluates the unchanged Human PR 20 cases with three additional model tiers under explicit reasoning effort `none`. It contains 180 decisions: 20 cases × 3 protocols × 3 models. All runs completed, and the judge-free audit reported no issue across any record or transcript. Standard token prices at the August 30, 2026 freeze were $0.20/$1.20 per million input/output tokens for Luna, $2/$12 for Terra, and $4/$20 for Sol, following the [official OpenAI model comparison](https://developers.openai.com/api/docs/models/compare).

| Model | Protocol | n | FCR (95% CI) | SCR (95% CI) | Verified / failed receipts | Estimated API cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `gpt-5.6-luna` | AR | 20 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 0 / 0 | $0.015 |
| `gpt-5.6-luna` | AR-Text | 20 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 0 / 0 | $0.015 |
| `gpt-5.6-luna` | EVAR-Hard | 20 | 0.000 (0.000-0.000) | 0.600 (0.300-0.900) | 17 / 3 | $0.016 |
| `gpt-5.6-terra` | AR | 20 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 0 / 0 | $0.149 |
| `gpt-5.6-terra` | AR-Text | 20 | 0.100 (0.000-0.300) | 0.600 (0.300-0.900) | 0 / 0 | $0.155 |
| `gpt-5.6-terra` | EVAR-Hard | 20 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 18 / 2 | $0.158 |
| `gpt-5.6-sol` | AR | 20 | 0.100 (0.000-0.300) | 0.800 (0.500-1.000) | 0 / 0 | $0.292 |
| `gpt-5.6-sol` | AR-Text | 20 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 0 / 0 | $0.302 |
| `gpt-5.6-sol` | EVAR-Hard | 20 | 0.100 (0.000-0.300) | 0.700 (0.400-1.000) | 19 / 1 | $0.308 |

Luna EVAR-Hard changes FCR by -0.100 and SCR by -0.100 relative to AR; both paired intervals span no change. Terra EVAR-Hard exactly matches AR and retains two more supported claims than AR-Text at the same FCR. Sol EVAR-Hard exactly matches AR-Text and retains one fewer supported claim than AR. Descriptively pooling the same 20 cases across the three models, AR scores FCR 0.100/SCR 0.767, AR-Text scores 0.100/0.667, and EVAR-Hard scores 0.067/0.700. This pooled view is not an independent-sample estimate.

The extension cost an estimated $1.411 in standard API token charges. Receipt verification varies from 85% for Luna to 90% for Terra and 95% for Sol, but higher receipt validity does not produce monotonic improvement in final FCR or SCR. These results reinforce that model capability, textual criticism, evidentiary relevance, and the deterministic gate interact rather than forming a simple quality ladder.

### 5.3 Exploratory Cross-Provider Extension

We additionally ran a pre-specified cross-provider extension through OpenRouter with the cases, prompts, budgets, verifier semantics, and scoring held fixed. Claude Sonnet 5 and Gemini 3.1 Pro Preview each completed all 60 protocol decisions (AR, AR-Text, and EVAR-Hard; 120/120 successful rows). DeepSeek V4 completed 20 AR cases (11 valid and 9 invalid-output failures) and 17 AR-Text cases before stopping. Kimi K3 completed 16 full AR cases plus a separate three-case pilot; Qwen3.8 Max completed a three-case AR pilot. These exploratory rows are not pooled as independent evidence. Invalid model outputs and incomplete cells remain visible as failures. A process-level curl deadline was added after some OpenRouter chunked responses stayed open indefinitely.

| Model | Attempted rows | Valid rows | Failed/incomplete |
|---|---:|---:|---:|
| Claude Sonnet 5 | 60 | 60 | 0 |
| Gemini 3.1 Pro | 60 | 60 | 0 |
| DeepSeek V4 Pro | 37 | 22 | 15 |
| Kimi K3 | 19 | 19 | 0 |
| Qwen3.8 Max | 3 | 3 | 0 |

These are attempted rows rather than independent cases; repeated pilot rows are not pooled into performance estimates.

### 5.4 Frozen External PR 50 Evaluation

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

### 5.4 GPT-4.1 Mini, Three Synthetic 50-Case Repetitions

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

### 5.5 GPT-4.1, Synthetic 50 Cases

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 50 | 50 | 0 | 0.040 | 0.000 | 0.120 | 0.960 | 0.880 | 1.000 |
| AR-Text | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 0.920 | 0.800 | 1.000 |
| EVAR-Hard | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260828T203024Z-16682391_ar.jsonl`
- `results/20260828T203246Z-fb1d8e13_ar_text.jsonl`
- `results/20260828T203836Z-f25cfab0_evar_hard.jsonl`

### 5.6 GPT-4.1 Mini, Real-Code 10-Case Pilot

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

### 5.7 GPT-4.1 Mini, External-Source 10-Case Pilot

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

### 5.8 GPT-4.1 Mini, External PR-Style 10-Case Pilot

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

### 5.9 GPT-4.1 Mini, External PR-Style 20-Case Benchmark

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

The untouched human-comment holdout changes the headline. EVAR-Hard does not outperform AR-Text: it ties AR-Text on both metrics with `gpt-4.1-mini` and is one case worse on each metric with `gpt-4.1`. With only ten eligible cases per metric and wide intervals, those one-case differences should not be overinterpreted. The defensible finding is non-dominance, not evidence that EVAR is inferior in a defined population.

The receipt-generation improvements did address the earlier mechanical bottleneck: 90% of v2 receipts verified for both models. Yet stronger receipt validity did not translate into better final decisions than AR-Text. The critic and the evidentiary relevance of a structurally valid quote remain important error sources. This separates two questions that the earlier experiment partially conflated: whether a model can construct a valid receipt, and whether requiring that receipt improves review decisions.

The three-model extension strengthens this non-dominance conclusion. With Luna, EVAR-Hard rejected one additional unsupported claim relative to both textual protocols but also retained one fewer supported claim. With Terra, EVAR-Hard exactly matched AR and retained two more supported claims than AR-Text. With Sol, EVAR-Hard exactly matched AR-Text and retained one fewer supported claim than AR. Receipt verification rose from 85% to 95% across the three tiers without a monotonic improvement in final outcomes. Verification is therefore not a model-independent quality layer: model behavior, receipt relevance, critic decisions, and verifier coverage jointly determine the operating point.

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

Human PR 20 is closer to the target setting than the hand-authored benchmarks, but it is still small: only ten source comments, five repositories, and ten cases per label. Comment selection required a clean temporal contrast and machine-reconstructable context, which favors localized, explicit review claims and is not representative sampling of all code-review comments. Each claim is evaluated twice at related commits, so pairs are not independent; confidence intervals cluster by case identifier but cannot create population representativeness. The ground-truth assumption is temporal: the reviewed commit supports the human comment and the merged code removes the cited condition. That is auditable but is not an independent expert adjudication of review usefulness.

The final holdout was untouched by evaluator tuning, but the benchmark-generation procedure and individual source comments were necessarily inspected before freezing to validate provenance and label direction. This is dataset construction, not blind annotation. A genuinely independent methodology review has been requested but is not complete at the time of this release.

The GPT-5.6 extension is exploratory rather than a new untouched benchmark. Its protocol and evaluator were frozen before its model calls, but it reuses the same 20 Human PR cases after the original results were known. The three models are repeated measurements on those cases, not 60 independent benchmark examples, and each model-protocol cell has only one API call per case. Explicit reasoning effort `none` controls cost and comparability but does not characterize each model's maximum capability. Model aliases, behavior, availability, and token prices may also change after the August 30, 2026 freeze.

The frozen `external_pr_50` benchmark improves repository diversity and prevents post-hoc prompt or verifier tuning on its cases, but it is still hand-authored. Claims are constructed from real commits rather than sampled from human review comments, and each case presents a focused file-scoped patch rather than a full repository checkout. Supported and unsupported claims share the same patch, which controls evidence but may make classification easier than open-ended review.

The two configured seeds are replicate labels only. The backend did not send a seed parameter to the OpenAI Responses API, so the study has independent repeated calls but not controlled seeded inference. One mini EVAR output failed JSON parsing. Four additional attempts were excluded under an infrastructure rule because DNS, concurrent throttling, or exhausted credits caused widespread request failures; the raw excluded records and reasons remain in the artifact.

The earlier `manual_50` benchmark is synthetic and templated. Even though it was held out from the original 10-case tuning loop, the cases share simple patterns and short files. The `real_10` and `external_10` pilots are closer to real code, but they remain small and use hand-authored static claims. The `external_pr_10` pilot is commit-grounded but was inspected during harness development, so it should be treated as diagnostic rather than held-out evidence. The `external_pr_20` benchmark is a stronger held-out check, but it is still small and limited to two source projects. Results should not be presented as evidence of real-world code-review performance without a larger benchmark based on human review claims.

Prompts were improved after observing failures on the earlier development benchmarks. Those changes were frozen before `external_pr_50`; they nevertheless weaken claims about prompt-independent generalization beyond the frozen evaluation.

The sample size remains small for statistical claims. Bootstrap intervals are useful as descriptive uncertainty checks, but stronger claims require more diverse cases and independent repetitions.

The verifier is specialized to Python and to a limited set of structural and behavioral claim patterns. Some successful checks use targeted AST logic added after observing development failures. This improves the harness but means performance can reflect verifier coverage as much as protocol quality.

The 20-case receipt-repair result is explicitly post-hoc. The same benchmark informed the repair logic, so the repaired score measures whether the diagnosed failures were corrected, not whether the correction generalizes.

The study now includes human-authored production pull-request comments as candidate claims, but it does not test human reviewers using EVAR, repository-scale dependency graphs, or a calibrated estimate of review utility. It measures acceptance of pre-specified candidate claims, not end-to-end bug discovery.

## 8. Next Work

The separate development split and first untouched human-comment evaluation are complete. The next research-quality step is a preregistered, independently labeled benchmark with substantially more human comments, repositories, languages, reviewers, and claim types. It should reserve distinct development and test repositories, use two independent expert labels plus adjudication, and define the sampling frame before collection.

Additional useful extensions:

- Increase per-family sample sizes and repository diversity.
- Repeat the model extension on newly preregistered cases with multiple calls per cell and a reasoning-effort ablation.
- Compare verifier-independent receipt generators.
- Separate receipt validity, evidentiary relevance, critic correctness, and final actionability in the error analysis.
- Compare against stronger tool-using and test-generating baselines, not only text evidence.
- Add richer structural verifiers for common review claims without tuning on the final holdout.

## 9. Conclusion

EVAR changes the acceptance rule for adversarial code review: reviewer-critic agreement is necessary but insufficient; a finding must also survive an external evidence check. In the earlier frozen evaluation, this gate reduced unsupported actionable claims but rejected many supported claims. After receipt-generation improvements on a separate development split, the final human-comment holdout showed high receipt verification but no advantage over AR-Text. The three-model extension was likewise heterogeneous: EVAR-Hard traded safety for retention with Luna, matched AR with Terra, and matched AR-Text with Sol. Its pooled scores are descriptive and do not establish dominance.

The strongest conclusion remains procedural rather than a claim of universal performance advantage. Mechanically checked evidence creates an auditable boundary and exposes why a finding was accepted or rejected, but a valid receipt is not synonymous with a correct decision. The mixed result narrows the research claim and motivates a larger independent evaluation rather than further tuning on this holdout.

## 10. Artifact Availability

The project site summarizes the protocol, evidence, limitations, and reproduction path: [EVAR research site](https://evar-research.elitelab-ai.chatgpt.site).

Version `v0.2.0` is the current public paper release. It archives the evaluator, frozen inputs, 720 model decisions, transcripts, audits, reports, paper source, and independent-review packet. The 180-decision GPT-5.6 extension is prepared locally for a later revision and is not part of that public release. Its run index, report, audit, transcripts, and 193-file results manifest preserve the complete extension artifact without implying publication. The GitHub release remains the canonical public source snapshot; a Zenodo DOI is added here when the external deposit is successfully published.

The repository contains protocol implementations, prompts, benchmark fixtures, canonical results, transcripts, audit reports, and analysis tools. `benchmarks/external_pr_50/freeze_manifest.json` hashes the original 105 frozen inputs, while `benchmarks/human_pr_20/freeze_manifest.json` hashes the final holdout and frozen evaluator inputs. The model extension adds its own input freeze, run index, audit report, and output manifest. Each result manifest hashes the corresponding output artifacts, each `run_index.json` identifies scored runs, and each `audit_report.json` records the judge-free audit findings.

The core deterministic checks run with:

```bash
python -m unittest discover -s tests
python -m evar.demo_compare
```

Model-backed experiments require an explicit configuration and API credentials. The artifact records replicate labels, prompt hashes, model settings, per-case failures, token usage, duration, and transcripts to support auditing and later replication.

## References

1. Aman Madaan et al. "Self-Refine: Iterative Refinement with Self-Feedback." arXiv:2303.17651, 2023. https://arxiv.org/abs/2303.17651
2. Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, and Igor Mordatch. "Improving Factuality and Reasoning in Language Models through Multiagent Debate." arXiv:2305.14325, 2023. https://arxiv.org/abs/2305.14325
3. Carlos E. Jimenez et al. "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" arXiv:2310.06770, 2023. https://arxiv.org/abs/2310.06770
4. Deepak Kumar. "SWE-PRBench: Benchmarking AI Code Review Quality Against Pull Request Feedback." arXiv:2603.26130, 2026. https://arxiv.org/abs/2603.26130
