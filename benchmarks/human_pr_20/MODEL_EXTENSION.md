# Human PR 20 Model Extension Protocol

This post-release extension evaluates the unchanged Human PR 20 cases with three
additional OpenAI models: `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`.
It is a model generalization study, not a new untouched benchmark.

Methodological boundaries:

- `cases.jsonl`, repository snapshots, prompts, verifier semantics, and scoring are unchanged.
- The only backend change permits omission of unsupported `temperature` and records an
  explicit `reasoning.effort: none` request for these models.
- Each model runs AR, AR-Text, and EVAR-Hard once with identical case order and budgets.
- Seed 41 is a provenance label, not a deterministic-inference claim.
- No prompt, verifier, label, or case change may be made after the extension manifest is frozen.
- Results are reported separately from the original untouched two-model evaluation.
- Because model selection occurred after the first study, extension results are exploratory.

The selected tiers correspond to the current official roles: Luna for cost-sensitive
workloads, Terra for balanced cost and capability, and Sol for flagship capability.
Standard token prices at freeze time are recorded in the extension report.
