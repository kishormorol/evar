# Expert recruitment and qualification

Use this material only after the institutional determination permits recruitment.
Replace every bracketed field before contacting anyone. Do not commit names, email
addresses, screening answers, payment records, or identity mappings.

## Required roles

- Expert A and Expert B each independently review all 682 candidates.
- A separate adjudicator reviews only disagreements.
- Pilot reviewers assess the interface and instructions; their answers never become
  benchmark labels.

Experts should have substantial practical or research experience reviewing software,
be able to read all six benchmark languages (Go, Java, JavaScript, Python, Rust, and
TypeScript), and be comfortable distinguishing a concrete defect claim from style or
preference. Record the evidence used to establish suitability in the private study log.
Do not publish or rank individual qualifications.

The adjudicator should meet at least the same standard as the two experts. Anyone who
helped construct candidates, saw advisory LLM labels, or discussed pilot answers is not
eligible for a final expert role.

If two suitably polyglot experts cannot be recruited, stop and prospectively amend the
design to use language-qualified reviewer pairs. Do not assign languages opportunistically
after viewing labels or model results.

## Private screening questions

1. How many years have you performed professional or research software development?
2. How frequently have you reviewed pull requests during the last two years?
3. Which of the six benchmark languages can you read confidently?
4. Have you contributed to or reviewed any source repository in the candidate pool?
5. Have you seen EVAR advisory model annotations or helped construct benchmark labels?
6. Can you complete the assigned work independently during [completion window]?

The study lead records a role decision and short rationale privately. Repository
involvement is not an automatic exclusion, but affected candidates must be identified
before annotation and handled according to the institutional determination and
preregistered deviation policy.

## Recruitment message

> Subject: Invitation to review public code examples for a research benchmark
>
> We are recruiting experienced software reviewers for a study of code-review claims.
> You would independently compare a public review comment with two frozen versions of
> the affected code. The final expert role contains 682 items and is expected to take
> [time based on the interface pilot]. Work may be divided across sessions during
> [dates]. Compensation is [terms]. Your decisions will be stored under a pseudonymous
> identifier and reported only in aggregate. Participation and withdrawal are governed
> by the attached information sheet and institutional determination [identifier]. If
> interested, please reply to [study contact] to receive the qualification questions.

## Workload safeguards

- Derive the time estimate from the 18-item interface pilot; do not guess it in the
  information sheet.
- Schedule the 682-item pass across multiple sessions and recommend a break at least
  every 50 items.
- Ask reviewers to download a private backup after every session.
- Record session dates, approximate active time, and interruptions in the private log.
- Do not introduce deadlines or incentives that reward rushing or agreement.
