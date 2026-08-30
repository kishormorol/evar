# Human PR 200 annotation protocol

`candidates.jsonl` is an acquisition artifact, not labeled evaluation data. The
annotation queue contains a stable randomized order and two exact file excerpts for
each candidate: the snapshot at which a human left the comment and the later merged
snapshot. Annotators must not run model experiments against this queue.

For each record, two annotators independently complete the following fields:

- `eligible`: `true` only if the comment expresses a self-contained, technically
  checkable claim about the target, with enough evidence in the two excerpts.
- `normalized_claim`: a short declarative claim that does not mention the label,
  reviewed/merged status, or the annotation process.
- `claim_family`: one of `behavior_inversion`, `missing_guard`,
  `incorrect_call_relationship`, `causal_mislocalization`, or `stale_evidence`.
  Exclude claims that do not fit these families rather than inventing a new class
  after seeing model results.
- `supported_at_review`: whether the normalized claim is true at `review_commit`.
- `unsupported_at_merge`: whether the same claim is false at `merge_commit`.
- `exclusion_reason`: required when `eligible` is false.

Eligibility exclusions include bots, praise-only or purely stylistic comments,
requests whose truth depends on unavailable external systems, comments whose target
cannot be reconstructed, and claims that remain true at both snapshots. Suggestions
may be retained only when the underlying technical condition can be stated and checked
without reproducing the suggestion text verbatim.

The adjudicator accepts a candidate only when both annotators agree that it is eligible,
the normalized claim is stable, and the temporal labels are `true`/`true`. The accepted
candidate becomes two benchmark cases with the same claim: `SUPPORTED` at the reviewed
commit and `UNSUPPORTED` at the merged commit. Disagreements, exclusions, and changes
to the claim are retained in an adjudication log. Sampling should be stratified by
language and repository, with no more than six source comments from one repository and
at least 20 repositories in the final 100-comment set.
