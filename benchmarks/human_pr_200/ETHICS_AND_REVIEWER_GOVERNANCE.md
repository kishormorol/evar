# Ethics and reviewer governance

This file records the governance conditions for the powered Human PR expansion. It
does not itself constitute institutional approval. Before either final expert begins,
the study lead must obtain and record the determination required by the lead
institution (for example, not-human-subjects research, exempt review, or approval).

## Institutional determination

- Status: **pending**
- Institution: to be recorded by the study lead
- Determination category: to be recorded by the study lead
- Protocol or determination identifier: to be recorded by the study lead
- Determination date: to be recorded by the study lead
- Responsible investigator: to be recorded in the private study log

Final expert annotation may not begin while the status above is `pending`. The public
artifact may report the category and identifier, but reviewer names, signatures,
contact details, and compensation records remain outside the repository.

The submission summary is in `INSTITUTIONAL_DETERMINATION_REQUEST.md`. The reviewer
materials are `REVIEWER_INFORMATION_SHEET.md` and
`REVIEWER_ACKNOWLEDGMENT_TEMPLATE.md`. Bracketed fields must be completed before use.

## Data and participant boundary

The benchmark source material consists of public GitHub pull-request comments and
public repository snapshots. The study analyzes technical claims and does not infer
sensitive attributes, evaluate individual developers, or publish reviewer-level
performance. Public availability does not remove the need for a local institutional
determination.

The expert annotators and adjudicator are study personnel or recruited reviewers. They
must receive a short information sheet covering the task, expected time, compensation
if any, data handling, withdrawal procedure, and whom to contact with concerns. The
study lead retains acknowledgment records privately.

## Role separation and blinding

- Pilot reviewers may assess interface clarity, but their decisions are never labels.
- Expert A and Expert B independently review the complete 682-item queue.
- Neither expert may access the advisory LLM annotations or the other expert's export.
- A third person adjudicates disagreements using the identity-blinded queue.
- Pilot discussion participants do not become final experts if individual pilot
  answers were discussed during interface revision.
- Model runs remain blocked until both exports, adjudication, deterministic selection,
  case rendering, contamination checks, and the model-input freeze have completed.

## Privacy and reporting

Stable pseudonymous reviewer identifiers are used in exports. The mapping from those
identifiers to people is stored outside the repository with access limited to the study
lead. Publications report aggregate agreement, yield, and timing. They do not compare
or rank individual annotators.

Source URLs and public usernames are retained only for provenance. The released
benchmark should minimize unnecessary personal data and document source licensing,
redistribution constraints, intended use, and the process for handling a reasonable
removal request.

## Required study log

Before the benchmark is frozen, the private study log must contain:

1. the institutional determination record;
2. the information sheet and acknowledgment used for each reviewer role;
3. role assignments and stable pseudonymous identifiers;
4. pilot dates, completion times, and interface-only feedback;
5. start and completion timestamps for both independent passes;
6. validation reports and hashes for both exports;
7. the adjudicator export and its validation report; and
8. any protocol deviation, exclusion, withdrawal, or provenance correction.

Any deviation that could depend on observed labels must be disclosed and followed by
the sensitivity analysis specified in `PREREGISTRATION.md`.
