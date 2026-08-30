# EVAR v2 development result

`external_pr_20` is an inspected development benchmark. It was used to validate the
versioned `reviewer_evar_v2.txt` receipt prompt, conservative structural-quote cleanup,
and one bounded retry for malformed structured output. It is not a new held-out result.

Configuration: `configs/development_external_pr_20/gpt41_mini_v2.yaml`

| Model | Protocol | Cases | Failed | FCR | SCR | Input tokens | Output tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-4.1-mini` | EVAR-Hard v2 | 20 | 0 | 0.000 | 1.000 | 111,976 | 2,745 |

The result file and transcripts are stored under
`results/development_external_pr_20/`. Because this benchmark had already informed
earlier verifier development, the score only confirms that the new receipt workflow
preserves the desired development behavior. Evaluation claims must come from a separate
benchmark frozen after this implementation.
