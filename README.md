# EVAR: Evidence-Verified Adversarial Review

EVAR is a minimal research harness for comparing reviewer/critic code review protocols.

Research question:

> Can external executable verification reduce false consensus between LLM reviewer/critic agents during code review?

This is not a production application. The current implementation uses deterministic dummy agents so the end-to-end path can run without calling an LLM.

## Protocols

- `AR`: reviewer proposes findings, critic challenges, consensus is textual.
- `AR-Text`: same architecture, but reviewer adds textual evidence when challenged.
- `EVAR-Hard`: reviewer must attach a structured evidence receipt; deterministic verification gates actionability.

All protocol classes accept the same `ProtocolBudget` and `AgentConfig` objects so experiments can keep model configuration and review/revision budgets equivalent.

## Run

```bash
python -m evar
pytest
```

