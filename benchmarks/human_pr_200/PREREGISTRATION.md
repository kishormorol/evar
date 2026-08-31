# Human PR expansion preregistration

Status: protocol frozen before Human PR expansion model calls. The directory name
`human_pr_200` is retained for artifact compatibility; the powered target below is 300
independent source comments and therefore 600 temporal cases.

## Research question and confirmatory comparison

The confirmatory question is whether EVAR-Hard changes actionable-decision quality
relative to AR-Text when both evaluate the same human-authored claim and repository
snapshot. GPT-4.1 is the continuity model because it was fixed before the Human PR 20
holdout. AR remains a descriptive baseline. Claude Sonnet 5, Gemini 3.1 Pro Preview,
DeepSeek V4 Pro, Kimi K3, and Qwen3.8 Max are external-validity extensions and are not
pooled into the confirmatory test.

The two label-specific endpoints are:

- false-consensus rate among unsupported merge-snapshot cases; and
- supported-claim retention among supported review-snapshot cases.

AR-Text and EVAR-Hard are compared with exact two-sided McNemar tests. Each endpoint
uses alpha 0.025, giving family-wise alpha at most 0.05 by Bonferroni correction. The
smallest effect of practical interest is an absolute paired difference of 0.15. Effect
sizes and cluster-bootstrap intervals are reported even when a test is not significant.
No cross-model pooled p-value is planned.

## Sampling and annotation

All 682 mechanically acquired candidates enter two independent expert annotation
passes. Reviewers receive the same randomly ordered, label-free queue and may not see
the advisory LLM annotations or each other's decisions. Any difference in eligibility,
normalized claim, family, temporal judgment, or exclusion reason is resolved by a
third expert from an identity-blinded adjudication queue.

Selection is deterministic after adjudication. It targets 300 eligible source comments
from at least 40 repositories, balances language and claim family, and retains no more
than six comments per repository. Each source comment produces one supported review
snapshot and one unsupported merge snapshot. If fewer than 300 candidates satisfy the
frozen criteria, no smaller confirmatory benchmark is substituted: acquisition resumes,
or the study is explicitly redesignated as estimation-only before any model call.

The target follows the prospective power calculation in `POWER_PLAN.md`. With a 0.15
paired difference, per-endpoint alpha 0.025, and the conservative supported-case
discordance estimate, 300 independent source comments provide estimated power 0.856.
The unsupported-case estimate is 0.967. Repeated calls do not increase this independent
sample size.

## Model execution

The prompt, parser, verifier, cases, model slugs, prices, and input manifest are hashed
before execution. The confirmatory GPT-4.1 matrix evaluates AR, AR-Text, and EVAR-Hard
once on every case. The five-provider extension uses the same three protocols and is
reported model by model.

Every model request receives a configured 120-second transport deadline, at most two
attempts, and a 250-second total call budget. These values are identical across the
OpenRouter models and are recorded with each result. A failure remains a typed failed
row; it is not converted to a negative decision or imputed. A cell must be complete to
receive a protocol-quality estimate.

Repeatability is measured on a deterministic 60-source-comment subset stratified by
label, language, repository, and claim family. Every model-protocol-case cell in that
subset receives three total repetitions. Repetition indices are recorded and transcripts
are stored separately. Repeatability is summarized as within-cell agreement and the
distribution of label-specific rate estimates, not as 180 additional independent cases.

Before paid calls, a dry run, benchmark preflight, price-table freeze, and projected-cost
report must pass. Execution does not begin if available credit is below the projected
upper bound. Prices or model availability may force a new timestamped protocol version,
but model outcomes may not be inspected before that revision is frozen.

## Analysis and exclusions

The unit of independent resampling is the source review comment; its two temporal cases
remain together. Results include per-model FCR, SCR, paired differences, exact tests,
cluster-bootstrap intervals, receipt validity, abstention, latency, tokens, cost, and
typed failure counts. Repository, language, and claim-family strata are descriptive
unless a later multiplicity-controlled analysis is frozen before model calls.

No candidate, model call, or protocol is removed because of its outcome. Post-freeze
exclusions are limited to proven provenance corruption or benchmark-construction defects,
must be listed individually, and require a sensitivity analysis with and without the
affected source comments.
