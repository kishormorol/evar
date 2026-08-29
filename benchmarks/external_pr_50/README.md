# External PR 50 Benchmark

This frozen candidate benchmark contains 50 review-claim cases grounded in 25 public upstream commits. Every source change produces a supported and an unsupported claim about the same post-commit snapshot.

The design is balanced by label, project, and claim family:

- 25 `SUPPORTED` and 25 `UNSUPPORTED` cases
- 10 cases from each of five repositories
- 10 cases in each of the five EVAR claim families
- one supported/unsupported pair per project and family

| Source | Repository |
| --- | --- |
| Click | <https://github.com/pallets/click> |
| pluggy | <https://github.com/pytest-dev/pluggy> |
| attrs | <https://github.com/python-attrs/attrs> |
| more-itertools | <https://github.com/more-itertools/more-itertools> |
| Requests | <https://github.com/psf/requests> |

The exact source commit for every case is recorded in `cases.jsonl`. Source histories are used only to regenerate snapshots and are excluded from version control. Each generated case contains the exact upstream source patch for its pinned commit, limited to the file or files relevant to that claim pair. This keeps model context focused while retaining both the pre-change and post-change evidence a real PR reviewer would see.

Regenerate:

```bash
gh repo clone pallets/click benchmarks/external_pr_50/sources/click
gh repo clone pytest-dev/pluggy benchmarks/external_pr_50/sources/pluggy
gh repo clone python-attrs/attrs benchmarks/external_pr_50/sources/attrs
gh repo clone more-itertools/more-itertools benchmarks/external_pr_50/sources/more-itertools
gh repo clone psf/requests benchmarks/external_pr_50/sources/requests
python benchmarks/external_pr_50/generate.py
```

Leakage policy:

- the claims and ground-truth evidence are authored from pinned upstream diffs;
- no `external_pr_50` case is used to modify evaluator prompts or verification rules;
- prompts, verifier implementation, cases, configs, and snapshots are hashed before runs;
- ground-truth fields are scoring metadata and are not included in model prompts;
- runs are audited without a judge model.
