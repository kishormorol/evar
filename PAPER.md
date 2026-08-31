# Evidence-Verified Adversarial Review for Code-Review Claims

Project preview: [evar-research.elitelab-ai.chatgpt.site](https://evar-research.elitelab-ai.chatgpt.site) · Development repository: [github.com/kishormorol/evar](https://github.com/kishormorol/evar)

## Abstract

When a code-review agent cites the wrong lines, asking a second language model whether the finding sounds reasonable can reproduce the same mistake. We test a stricter alternative. Evidence-Verified Adversarial Review (EVAR) requires the reviewer to submit a structured receipt—a file, line range, expected observation, falsification condition, and optionally a bounded command—and makes deterministic verification a precondition for actionability. We compare ordinary adversarial review (AR), textual evidence (AR-Text), and EVAR-Hard with matched prompts, cases, and call budgets. Our final holdout contains 120 decisions over temporal pairs derived from ten public pull-request comments. On this holdout, `gpt-4.1-mini` gives the same FCR/SCR operating point for AR-Text and EVAR-Hard (0.200/0.700), while `gpt-4.1` favors AR-Text (0.200/0.700 versus 0.300/0.600). Results from three newer OpenAI models are similarly mixed. A separate cross-provider run completes only seven of fifteen protocol cells and reveals a practical obstacle: schema and serving failures can prevent the comparison from being run at all. Across 900 completed matched decisions, the hard gate changes which findings survive but does not consistently improve decision quality. What it does provide is a reproducible acceptance boundary: an actionable EVAR finding has a machine-checked receipt, and failed evidence remains visible in the record.

## 1. Research Question

Can external deterministic verification reduce false consensus between LLM reviewer and critic agents during code review?

We define false consensus as an unsupported candidate claim becoming actionable after reviewer/critic interaction. We also track supported-claim retention to ensure that stricter verification does not simply reject everything.

One Human PR 20 pair makes the task concrete. In Black pull request 5272, a reviewer asked that an internal explanation involving `hug_power_op` and cloned leaves be replaced with a concise user-facing changelog entry. The claim is supported at the reviewed commit and unsupported after the merge edit. A textual critic can find the wording plausible in either snapshot; an evidence receipt must identify the exact changelog lines present in that snapshot. EVAR evaluates that narrow actionability question rather than open-ended defect discovery.

This work makes four concrete contributions:

1. **Protocol:** a structured evidence receipt and deterministic gate that make acceptance conditions externally inspectable.
2. **Benchmark:** a temporally paired holdout built from public human review comments at reviewed and merged commits.
3. **Evidence:** matched AR, AR-Text, and EVAR-Hard experiments that expose a model-sensitive safety-retention tradeoff.
4. **Artifact:** frozen inputs, transcripts, result manifests, and judge-free audits for 900 completed matched decisions, plus canonical accounting for 180 cross-provider attempts with failures retained explicitly.

### 1.1 Related Work

EVAR builds on iterative critique and multi-agent deliberation but changes the acceptance condition. Self-Refine demonstrates that model-generated feedback can improve a model's own outputs across tasks [1], Reflexion carries linguistic feedback through agent memory [15], and multi-agent debate uses multiple model instances to improve reasoning and factuality through textual exchange [2]. Neither result implies that agreement is independently grounded. CRITIC shows the complementary value of tool-interactive feedback [6]. EVAR narrows that premise to a pre-specified review claim and makes a verified external observation a necessary condition for actionability rather than optional context for another revision.

Modern code review is not only defect detection. Studies at Microsoft and Google describe knowledge transfer, alternative solutions, team awareness, and workflow integration as important parts of the practice [7, 8]. Industrial studies of deployed automated review systems further show why adoption, latency, and developer utility require direct measurement [9, 10]. EVAR's FCR and SCR therefore measure the fate of a supplied technical claim, not whether a generated comment is timely, understandable, or useful to a team.

CodeReviewer evaluates learned quality estimation, comment generation, and refinement [11], while hybrid work combines LLM generation with static analyzers to trade broader coverage against rule-based precision [12]. EVAR begins later: a candidate claim already exists, and deterministic machinery validates its submitted observation and controls actionability. SWE-agent similarly demonstrates that the model--computer interface matters [14], but EVAR deliberately limits itself to structural checks or a shell-free timed process. The current prototype is not an operating-system sandbox.

For software-engineering evaluation, SWE-bench grounds tasks in real GitHub issues and pull requests and highlights the need for repository context and executable environments [3]. More recent code-review work evaluates models against human pull-request feedback and reports low detection of human-flagged issues [4]. EVAR studies a narrower question: given a pre-specified candidate review claim, does an evidence gate prevent unsupported reviewer-critic consensus without discarding supported claims?

SWR-Bench makes a complementary choice: it evaluates 1,000 complete pull requests with full-project context and structured ground truth, then asks whether generated reviews cover the reported issues [5]. EVAR is smaller and deliberately different. It does not score open-ended issue discovery; it fixes one candidate claim and asks whether that claim can cross an auditable evidence boundary. That trades breadth for a clean test of false consensus and lets us report why a finding was accepted, rejected, or mechanically unverifiable. A future larger benchmark should combine EVAR's receipt-level audit with the PR-scale context and manual verification used by SWR-Bench.

ContextCRBench scales context-rich review evaluation to quality assessment, localization, and comment generation [13]. Its emphasis on issue context and fine-grained localization reinforces an external-validity limit here: EVAR's focused excerpts isolate the verification question, but cannot substitute for evaluating complete pull requests with developer intent.

## 2. Protocols

We compare three protocols under the same two-call budget: one schema-constrained reviewer call followed by one critic call. The reviewer always returns exactly one receipt; the protocols differ in what happens to it before criticism.

| Protocol | Evidence Handling | Actionability Gate |
| --- | --- | --- |
| AR | Reviewer proposes a finding; critic evaluates textually. | Critic returns `ACCEPT`. |
| AR-Text | Reviewer provides textual evidence; critic evaluates without execution. | Critic returns `ACCEPT`. |
| EVAR-Hard | Reviewer submits a structured `EvidenceReceipt`; verifier checks structural or behavioral evidence; critic evaluates the verified observation. | Verifier returns `VERIFIED` and critic returns `ACCEPT`. |

The EVAR-Hard receipt contains the claim, evidence type, evidence role, referenced file and line range, optional verification command, expected observation, and falsification condition. The evidence role distinguishes evidence intended to support a claim from evidence intended to contradict it. Behavioral witnesses must print `EVAR_WITNESS_PASS` only when the claim is supported.

In every run, the reviewer sees the candidate claim and repository snapshot but not the label. AR passes the receipt fields to a critic with verification marked unused. AR-Text projects the receipt into textual evidence without executing it. EVAR-Hard verifies the receipt before the critic call; the critic sees failed verification, but cannot override the hard gate. Two frozen deterministic repairs may re-check an explicit opposite-role AST observation or fall back from invalid inline-Python syntax to structural verification. Both events are logged. There is no model revision turn in the reported configured runs.

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

| Study phase | Cases | Decisions | Evidential role |
|---|---:|---:|---|
| External PR 50 | 50 | 600 | Frozen first evaluation; later inspected to diagnose receipt failures |
| Development PR 20 | 20 | diagnostic | Prompt and verifier development only |
| Human PR 20 | 20 | 120 | Untouched final holdout and primary RQ1 evidence |
| GPT-5.6 extension | 20 reused | 180 | Pre-specified exploratory model-sensitivity analysis |
| Cross-provider pilots | 20 reused | partial | Operational validity accounting, not a balanced leaderboard |

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

#### Case-level decision transitions

Aggregate rates hide whether EVAR-Hard merely filters AR-Text decisions or changes the critic's reasoning. On `gpt-4.1-mini`, the two protocols differ on two supported cases in opposite directions—one accepted claim becomes rejected and one rejected claim becomes accepted—so their aggregate scores tie. On `gpt-4.1`, four decisions change: two supported claims are lost, one supported claim is recovered, and one unsupported claim becomes actionable.

| Model | Supported keep | Supported accept→reject | Supported reject→accept | Unsupported keep | Unsupported accept→reject | Unsupported reject→accept |
|---|---:|---:|---:|---:|---:|---:|
| `gpt-4.1` | 7 | 2 | 1 | 9 | 0 | 1 |
| `gpt-4.1-mini` | 8 | 1 | 1 | 10 | 0 | 0 |

The unsupported reject→accept transition matters: EVAR-Hard is not a monotone post-filter because the critic sees a different evidence representation. Verified but irrelevant evidence can persuade the critic to accept a claim that textual evidence did not.

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

### 5.3 Cross-Model Pareto Synthesis

Comparing EVAR-Hard against each matched baseline without pooling gives the clearest summary. Negative FCR deltas and positive SCR deltas favor EVAR-Hard.

| Model | Baseline | ΔFCR | ΔSCR | Relation |
|---|---|---:|---:|---|
| GPT-4.1 | AR | -0.100 | -0.100 | Tradeoff |
| GPT-4.1 | AR-Text | +0.100 | -0.100 | Dominated |
| GPT-4.1-mini | AR | -0.200 | -0.200 | Tradeoff |
| GPT-4.1-mini | AR-Text | 0.000 | 0.000 | Tie |
| GPT-5.6-luna | AR | -0.100 | -0.100 | Tradeoff |
| GPT-5.6-luna | AR-Text | -0.100 | -0.100 | Tradeoff |
| GPT-5.6-terra | AR | 0.000 | 0.000 | Tie |
| GPT-5.6-terra | AR-Text | 0.000 | +0.200 | Dominates |
| GPT-5.6-sol | AR | 0.000 | -0.100 | Dominated |
| GPT-5.6-sol | AR-Text | 0.000 | 0.000 | Tie |

Across ten comparisons, EVAR-Hard dominates once, is dominated twice, ties three times, and trades lower false consensus for lower supported-claim retention four times. Its single dominance result—Terra against AR-Text—is not reproduced against AR or by the adjacent Luna and Sol tiers. The effect is therefore an interaction among reviewer, evidence representation, verifier, and critic, not a stable wrapper benefit.

### 5.4 Exploratory Cross-Provider Extension

We additionally ran a pre-specified cross-provider extension through OpenRouter with cases, prompts, budgets, verifier semantics, and scoring fixed. Claude Sonnet 5 and Gemini 3.1 Pro Preview each completed all 60 decisions. DeepSeek produced 22 valid and 15 invalid-output rows across 37 attempts. Kimi completed AR only; Qwen has a three-case connectivity pilot. Duplicate retries and aborted files are excluded from canonical accounting. Incomplete model blocks are treated as operational reliability evidence, not imputed performance results.

| Model | Attempted rows | Valid rows | Failed/incomplete |
|---|---:|---:|---:|
| Claude Sonnet 5 | 60 | 60 | 0 |
| Gemini 3.1 Pro | 60 | 60 | 0 |
| DeepSeek V4 Pro | 37 | 22 | 15 |
| Kimi K3 | 20 | 20 | 0 |
| Qwen3.8 Max | 3 | 3 | 0 |

These are attempted rows rather than independent cases; repeated pilot rows are not pooled into performance estimates.

| Model | Protocol | FCR | SCR | Verified receipts |
|---|---|---:|---:|---:|
| Claude | AR | 0.000 | 0.600 | — |
| Claude | AR-Text | 0.000 | 0.700 | — |
| Claude | EVAR-Hard | 0.000 | 0.700 | 20/20 |
| Gemini | AR | 0.000 | 0.800 | — |
| Gemini | AR-Text | 0.000 | 0.800 | — |
| Gemini | EVAR-Hard | 0.000 | 0.800 | 19/20 |
| Kimi | AR | 0.100 | 0.900 | — |

These complete cells add no evidence of EVAR dominance. Claude and Gemini already have zero false consensus under every protocol, leaving only supported-claim retention to differ. DeepSeek's valid-response rate is 59.5% (22/37), so a protocol comparison would be misleading.

### 5.5 Frozen External PR 50 Evaluation

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

### 5.6 GPT-4.1 Mini, Three Synthetic 50-Case Repetitions

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

### 5.7 GPT-4.1, Synthetic 50 Cases

| Protocol | n | Completed | Failed | FCR | FCR Low | FCR High | SCR | SCR Low | SCR High |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AR | 50 | 50 | 0 | 0.040 | 0.000 | 0.120 | 0.960 | 0.880 | 1.000 |
| AR-Text | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 0.920 | 0.800 | 1.000 |
| EVAR-Hard | 50 | 50 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |

Result files:

- `results/20260828T203024Z-16682391_ar.jsonl`
- `results/20260828T203246Z-fb1d8e13_ar_text.jsonl`
- `results/20260828T203836Z-f25cfab0_evar_hard.jsonl`

### 5.8 GPT-4.1 Mini, Real-Code 10-Case Pilot

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

### 5.9 GPT-4.1 Mini, External-Source 10-Case Pilot

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

### 5.10 GPT-4.1 Mini, External PR-Style 10-Case Pilot

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

### 5.11 GPT-4.1 Mini, External PR-Style 20-Case Benchmark

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

The empirical story is less tidy than the protocol. External PR 50 initially suggested a familiar bargain: the hard gate admitted fewer unsupported claims, but it also discarded supported ones. Receipt generation was then improved on a separate development split. On Human PR 20, 90% of receipts verified for both models, so the obvious mechanical bottleneck had largely receded. The expected gain over textual evidence did not appear. `gpt-4.1-mini` tied AR-Text, and `gpt-4.1` was one case worse on each metric.

Individual transitions explain why. EVAR-Hard is not AR-Text followed by a filter; the critic receives a different representation of the evidence, and its judgment can move in either direction. In one `gpt-4.1` case, an unsupported claim rejected by AR-Text became actionable under EVAR-Hard. The receipt passed the verifier, but that did not make its observation relevant. In the other direction, a failed receipt can suppress a sound claim before the critic can recover it. Mechanical validity, relevance, critic judgment, and final actionability are separate stages.

The newer models do not simplify the picture. Luna exchanges a lower FCR for lower retention, Terra matches AR while outperforming AR-Text on retention, and Sol matches AR-Text. Receipt verification improves from 85% to 95% without a corresponding ordering of the decisions. Of ten matched Pareto comparisons across the five OpenAI configurations, EVAR-Hard dominates once, is dominated twice, ties three times, and produces a safety-retention tradeoff four times. Its effect depends on who writes the receipt, what the verifier can check, and how the critic reads the result.

The sample is too small to rank protocols in a broader population: one changed decision moves a holdout metric by 0.100. It is sufficient to reject the stronger claim that a hard evidence gate is automatically better than textual evidence. The benefit that survives every run is narrower and procedural. EVAR makes the acceptance path inspectable, retains failed evidence instead of burying it in dialogue, and prevents critic agreement from overriding a failed check.

The development sequence matters when interpreting the earlier benchmarks. Synthetic cases and the small source pilots helped expose path, role, command, and AST-checking failures. A post-hoc repair pass reached perfect results on External PR 20, but those cases had already shaped the repair. That score is evidence that the diagnosed failures were fixed, not that the repair generalizes.

## 7. Threats to Validity

**Construct validity.** FCR is the rate at which supplied unsupported claims become actionable; it is not the false-positive rate of an agent searching freely for defects. SCR records retention of claims grounded in public review-and-fix sequences, not whether every comment is useful. A verified receipt proves that an observation passed a mechanical check, not that the observation entails the claim.

**Internal validity.** Human PR 20 treats the reviewed commit and later merge edit as temporal evidence. This is auditable, but a merge may address only part of a comment, and the cases were necessarily inspected during construction. The evaluator was frozen before holdout calls, labels were removed from prompts, temporal pairs were clustered in the bootstrap, and failed calls were retained. Independent expert adjudication would still be stronger.

**External validity.** The holdout contains ten comments from five Python repositories. Requiring a clean temporal contrast favors localized claims and excludes much of architectural review, other languages, and claims that need unavailable runtime systems. Focused excerpts are also much smaller than full pull requests. The benchmark evaluates supplied claims, not open-ended issue discovery or developer utility.

**Reliability.** Most holdout cells contain one stochastic call per case, and the configured seeds are provenance labels rather than guaranteed inference controls. One changed decision moves a metric by 0.100. Bootstrap intervals show sensitivity to the observed pairs, not uncertainty over a sampled population. Gateway routing, throttling, and schema failures add variability to the cross-provider extension, so incomplete cells are not used for performance comparisons.

**Extension validity.** Both extensions reuse Human PR 20 after the first outcomes were known. They are repeated measurements, not new benchmark examples. Reasoning settings are not necessarily comparable across vendors, and aliases, routing, behavior, and prices can change after the freeze. The OpenAI extension is therefore exploratory; the incomplete provider run is primarily operational accounting.

**Implementation scope and safety.** The verifier is Python-specific and recognizes a limited set of observations. Behavioral witnesses use `shell=False` and a timeout but are not isolated by the operating system. The released fixtures are trusted. Untrusted receipts or repositories would require process isolation, network denial, and disposable filesystems.

**Data ethics.** The repositories and comments are public, and URLs and usernames are retained for provenance. Public availability is not the same as research consent: the comments were written to maintain software. The analysis is restricted to technical claims, and reviewer behavior is not profiled.

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

EVAR began with a simple premise: agreement between two language models should not be enough to make a code-review claim actionable. Requiring a checked receipt does enforce a clearer boundary, and it turns several hidden failures into inspectable records. The experiments also show the limit of that idea. A receipt can verify and still be irrelevant, while a sound claim can be lost because its receipt fails. On the final human-comment holdout, the hard gate offers no decision-quality advantage over textual evidence; across later models, its effect varies.

That leaves a narrower but useful result. Deterministic evidence improves the provenance of an accepted finding, not necessarily the finding itself. Establishing a performance benefit will require more independent review comments, expert adjudication, repeated calls, full pull-request context, and complete cross-provider cells. The artifact is intended to make that larger test possible without hiding the awkward outcomes that motivated it.

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

## Appendix: Experimental Details

### Case construction

Each Human PR 20 case stores the public pull-request URL, comment author, reviewed commit, merge commit, path, line location, claim text, label, and the source excerpts shown to the model. The reviewed snapshot is the positive member of the pair; the merge snapshot is the negative member. Both commits remain available for audit. The set is balanced between ten supported and ten unsupported cases across five repositories. The model-visible task excludes the label and construction notes. Context is clipped to the target file and, where needed, a companion changed file. This makes the test reproducible and focuses it on evidence selection rather than repository navigation.

### Audit and reproduction

The audit checks transcript completeness, model/protocol metadata, frozen prompt hashes, token consistency, nonnegative latency, and the EVAR implication that actionability requires both `VERIFIED` and critic `ACCEPT`.

```bash
python -m unittest discover -s tests
python scripts/summarize_cross_provider.py \
  --manifest benchmarks/human_pr_20/cross_provider_canonical_manifest.json \
  --output benchmarks/human_pr_20/cross_provider_summary.json
python -m evar.audit_results --results RESULTS/*.jsonl
```

The cross-provider transport uses a process-level curl deadline because some chunked responses left a Python socket read open beyond its nominal timeout. The replacement bounds the subprocess, preserves HTTP status codes for retry accounting, and records a timeout instead of hanging the experiment.

### Case and output schemas

Each benchmark case is a JSON object with stable identifiers. The principal fields are `case_id`, `claim`, `claim_family`, `ground_truth`, `paired_case_id`, `repo_path`, `snapshot_kind`, `source_commit`, `source_pull_request`, `target_context_file`, and optional `companion_context_file`. The model sees only the task description, candidate claim, claim family, valid repository paths, and file contents. Labels, pairing, snapshot kind, source-comment metadata, and construction evidence remain evaluator-only. The runner records the SHA-256 hash of every prompt template.

All reviewer prompts use the same strict schema: an object containing exactly one receipt with `claim_id`, `claim`, evidence type and role, repository-relative file, nullable line bounds, nullable command, nullable expected exit code, nullable expected-output substring, and falsification condition. Additional properties are rejected. A response that remains invalid after the configured retry becomes `ModelOutputError`; the evaluator does not synthesize a replacement.

### Interaction schedule

The configured protocols use two model calls per case. The reviewer emits one receipt. AR calls the critic with verification marked unused. AR-Text derives a textual-evidence view from the receipt. EVAR-Hard verifies the receipt, optionally performs one frozen deterministic repair and re-verification, and then calls the critic. There is no model revision turn. Every request role, prompt hash, timestamp, token count, response, parser outcome, and retry number is recorded.

### Receipt validation rules

Structural validation removes display artifacts such as Markdown fences, leading line numbers, and surrounding whitespace. It normally checks the repository-relative path, line interval, and normalized source observation. For structural receipts only, the frozen verifier may recover an unambiguous stale path by suffix, claimed function, or sole Python file, and may search that file when display-derived line numbers extend beyond end-of-file. Behavioral receipts receive neither recovery. Behavioral validation parses the command into an argument vector, launches it with `shell=False` from the fixture directory, applies a five-second default timeout, and checks exit status plus the `EVAR_WITNESS_PASS` marker. This prevents shell-pipeline interpretation and bounds elapsed execution, but it is not an operating-system sandbox: the child process retains the evaluator's network and filesystem permissions. Two deterministic repairs were frozen before Human PR 20: align the role with an explicit opposite-role AST observation, or fall back from invalid inline-Python syntax to structural checking. Each repair is logged and re-verified; no claim, file, or line range is generated during repair.

### Statistical and cost details

FCR and SCR are calculated only from completed rows of the relevant ground-truth class, with numerators and denominators retained in the report. Bootstrap intervals resample source case identifiers so both temporal members of a human comment remain together. Paired deltas join protocols on `(model, replicate, case_id)` before resampling. Token cost uses recorded input/output tokens and the frozen price table; retries count toward cost and latency. Cross-provider rows are reported as validity accounting rather than a pooled quality estimate because gateway routing and duplicate pilots make the cells non-independent.

### Representative failure cases

Common EVAR failures were receipts that quoted a nearby true line without establishing the claim, commands that passed without printing the required marker, line ranges copied from display excerpts rather than repository files, and contradiction receipts submitted with the support role. DeepSeek also produced empty or non-JSON reviewer responses after consuming its output budget. These are recorded as `ModelOutputError`, not as negative review decisions. Receipt validity, critic decisions, and final actionability are therefore reported separately.

### Larger replication

A stronger replication should sample review comments before observing their outcomes, include complete pull-request snapshots, obtain two independent expert labels with adjudication, preregister the sampling frame, repeat every model-protocol cell, report calibration and abstention, and include multilingual repositories. The present artifact supplies the receipt and audit machinery for that study; 20 temporal cases are not a representative sample of code review.

## References

1. Aman Madaan et al. "Self-Refine: Iterative Refinement with Self-Feedback." arXiv:2303.17651, 2023. https://arxiv.org/abs/2303.17651
2. Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, and Igor Mordatch. "Improving Factuality and Reasoning in Language Models through Multiagent Debate." arXiv:2305.14325, 2023. https://arxiv.org/abs/2305.14325
3. Carlos E. Jimenez et al. "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" arXiv:2310.06770, 2023. https://arxiv.org/abs/2310.06770
4. Deepak Kumar. "SWE-PRBench: Benchmarking AI Code Review Quality Against Pull Request Feedback." arXiv:2603.26130, 2026. https://arxiv.org/abs/2603.26130
5. Zhengran Zeng et al. "Benchmarking and Studying the LLM-based Code Review." arXiv:2509.01494, 2025. https://arxiv.org/abs/2509.01494
6. Zhibin Gou et al. "CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing." arXiv:2305.11738, 2023. https://arxiv.org/abs/2305.11738
7. Alberto Bacchelli and Christian Bird. "Expectations, Outcomes, and Challenges of Modern Code Review." ICSE, 2013. https://doi.org/10.1109/ICSE.2013.6606617
8. Caitlin Sadowski, Emma Söderberg, Luke Church, Michal Sipko, and Alberto Bacchelli. "Modern Code Review: A Case Study at Google." ICSE-SEIP, 2018. https://research.google/pubs/modern-code-review-a-case-study-at-google/
9. Umut Cihan et al. "Automated Code Review in Practice." ICSE-SEIP, 2025. https://doi.org/10.1109/ICSE-SEIP66354.2025.00043
10. Kla Tantithamthavorn et al. "RovoDev Code Reviewer: A Large-Scale Online Evaluation of LLM-based Code Review Automation at Atlassian." ICSE-SEIP, 2026. https://doi.org/10.1145/3786583.3786851
11. Zhiyu Li et al. "Automating Code Review Activities by Large-Scale Pre-training." ESEC/FSE, 2022. https://arxiv.org/abs/2203.09095
12. Imen Jaoua, Oussama Ben Sghaier, and Houari A. Sahraoui. "Combining Large Language Models with Static Analyzers for Code Review Generation." MSR, 2025. https://arxiv.org/abs/2502.06633
13. Ruida Hu et al. "Benchmarking LLMs for Fine-Grained Code Review with Enriched Context in Practice." FSE Industry Papers, 2026. https://arxiv.org/abs/2511.07017
14. John Yang et al. "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering." arXiv:2405.15793, 2024. https://arxiv.org/abs/2405.15793
15. Noah Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366, 2023. https://arxiv.org/abs/2303.11366
