# Human PR expansion cost and execution plan

Projection scales observed per-attempt token cost from frozen Human PR 20 runs. EVAR-BlindGate is assumed to cost approximately one ordinary two-call protocol arm.

| Model | Historical cost/attempt | Full attempts | Stability attempts | Projected | With contingency |
| --- | ---: | ---: | ---: | ---: | ---: |
| anthropic/claude-sonnet-5 | $0.0137 | 2400 | 960 | $45.98 | $57.48 |
| deepseek/deepseek-v4-pro-0813 | $0.0037 | 2400 | 960 | $12.36 | $15.44 |
| google/gemini-3.1-pro-preview | $0.0151 | 2400 | 960 | $50.80 | $63.50 |
| gpt-4.1 | $0.0071 | 2400 | 960 | $23.71 | $29.64 |
| moonshotai/kimi-k3 | $0.0127 | 2400 | 960 | $42.58 | $53.23 |
| qwen/qwen3.8-max | $0.0107 | 2400 | 960 | $35.85 | $44.82 |

The complete plan contains **20,160 protocol attempts**. The empirical projection is **$211.28**, or **$264.10** with the frozen 25% contingency.

This is a planning estimate, not authorization to spend. Before execution, refresh exact model prices, run dry-run and benchmark preflight, verify available credit against the upper bound, and freeze the new price table. If the budget is smaller, revise the protocol prospectively before inspecting any powered model outcome; do not silently drop models or repetitions after results are visible.
