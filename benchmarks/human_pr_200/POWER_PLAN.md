# Human PR 200 paired-power plan

This prospective calculation uses only the frozen Human PR 20 outcomes. It does not inspect Human PR 200 labels or model results. The primary comparison is AR-Text versus EVAR-Hard, tested separately within supported and unsupported temporal cases with an exact two-sided McNemar test.

The smallest effect of practical interest is an absolute paired rate difference of 0.15, with alpha = 0.025. To avoid treating ten-case pilot discordance as precise, the planning rate for each label is the largest model-specific 95% Wilson upper bound.

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
| 100 | 0.339 | 0.500 |
| 150 | 0.517 | 0.721 |
| 200 | 0.664 | 0.854 |
| 250 | 0.774 | 0.929 |
| 300 | 0.856 | 0.967 |
| 350 | 0.909 | 0.986 |
| 400 | 0.945 | 0.994 |
| 500 | 0.980 | 0.999 |

The final acquisition target must be chosen before model calls. If no feasible row reaches the desired power for both labels, the study must either acquire more independently adjudicated comments or explicitly present the corresponding endpoint as estimation rather than a powered superiority test. Repeated model calls reduce Monte Carlo uncertainty but do not increase the number of independent source comments.
