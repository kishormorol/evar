# Human PR 200 paired-power plan

This prospective calculation uses only frozen Human PR 20 outcomes and does not inspect Human PR expansion labels or model results. The primary powered comparison is the within-row EVAR-BlindGate role-aware soft decision versus the hard-gated decision, tested separately within supported and unsupported temporal cases with an exact two-sided McNemar test.

The smallest effect of practical interest is an absolute paired rate difference of 0.15, with alpha = 0.025. No verification-blind pilot outcome exists. To avoid choosing a favorable discordance assumption, both endpoints use the largest model-specific 95% Wilson upper bound observed in the earlier AR-Text versus EVAR-Hard pilot as a conservative planning proxy.

## Frozen pilot inputs

| Model | Label | Discordant / pairs | Rate | 95% Wilson upper |
| --- | --- | ---: | ---: | ---: |
| gpt-4.1 | SUPPORTED | 3 / 10 | 0.300 | 0.603 |
| gpt-4.1 | UNSUPPORTED | 1 / 10 | 0.100 | 0.404 |
| gpt-4.1-mini | SUPPORTED | 2 / 10 | 0.200 | 0.510 |
| gpt-4.1-mini | UNSUPPORTED | 0 / 10 | 0.000 | 0.278 |

## Prospective power curve

| Independent source comments (pairs per label) | Supported-case power | Unsupported-case power |
| ---: | ---: | ---: |
| 100 | 0.339 | 0.339 |
| 150 | 0.517 | 0.517 |
| 200 | 0.664 | 0.664 |
| 250 | 0.774 | 0.774 |
| 300 | 0.856 | 0.856 |
| 350 | 0.909 | 0.909 |
| 400 | 0.945 | 0.945 |
| 500 | 0.980 | 0.980 |

The final acquisition target must be chosen before model calls. If no feasible row reaches the desired power for both labels, the study must either acquire more independently adjudicated comments or explicitly present the corresponding endpoint as estimation rather than a powered superiority test. Repeated model calls reduce Monte Carlo uncertainty but do not increase the number of independent source comments.
