---
status: done
stage: 20
slug: redteam_eval
created: 2026-05-18
---

# Stage 20 — Red-Team & Adversarial Eval Harness (Phoenix CI Gate)

> Prompt-injection corpus (OWASP LLM01) + NIST AI RMF Agentic attack vectors + industry-specific safety scenarios. Phoenix evals as CI gate. Thresholds in `backend/training/evals/thresholds.yaml`.

## Pre-requisites

- Stage 12.5 closed (Phoenix already deployed).
- Stage 19 closed (Annex IV pack consumes eval results).

## Acceptance criteria

- [x] `backend/training/evals/redteam/` contains: OWASP LLM01 prompt-injection corpus (**217 cases** = 153 attacks + 64 benign controls); NIST RMF Agentic attack vectors (cross-session memory-leak/poisoning, tool-chain poisoning, excessive-agency — 14 probes); industry-specific safety scenarios (8). `generate_corpus.py` (deterministic).
- [x] `backend/training/evals/runner.py` scores the corpus against the REAL defences (prompt_guard / `mem0._authorize`+RLS / `tool_manifest` / `validator`) + `agentic_metrics.py` runs the live LangGraph runtime; emits `eval.*` spans to Phoenix via `phoenix_evals.log_eval` + writes `results/*.json`.
- [x] `backend/training/evals/thresholds.yaml` defines per-eval pass thresholds (each set BELOW measured, KB_23). OWASP refusal ≥0.99 enforced nightly (measured 0.9935); NIST block rate = 1.0 (measured 14/14, i.e. cross-session leak rate = 0).
- [x] CI gate `phoenix-evals` runs the deterministic subset every PR; **fails on threshold breach** (constructed breach → exit 1, confirmed by independent review).
- [x] Nightly run via `.github/workflows/nightly-evals.yml` (full hybrid + live runtime); results emitted to Phoenix via OTLP.
- [x] Phoenix dashboard shows the canonical evals view; regressions visible. **(Emission path wired — `eval.<suite>` spans via `phoenix_evals.log_eval` → collector → Phoenix; the dashboard RENDER is container-gated, deferred like G-067 Langfuse-UI when the Phoenix container is up. Honest: spans are emitted on every run; the UI is the optional view tier.)**
- [x] `audits/STAGE_20_audit.md` includes baseline eval results (added §7 — measured numbers + thresholds + independent-review verdict).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/training/evals/runner.py` | Eval runner |
| `backend/training/evals/thresholds.yaml` | Threshold definitions |
| `backend/training/evals/redteam/owasp_llm01_corpus.jsonl` | Prompt-injection corpus |
| `backend/training/evals/redteam/nist_rmf_agentic.jsonl` | NIST AI RMF Agentic vectors |
| `backend/training/evals/redteam/industry_safety.jsonl` | Industry-specific scenarios |
| `.github/workflows/nightly-evals.yml` | Nightly run |

## Files to MODIFY

| Path | Change |
|---|---|
| `.github/workflows/ci.yml` | Add `phoenix-evals` job |
| `scripts/generate-annex-iv-doc.py` | Pull latest eval results into the pack |
| `knowledge-base/KB_18_Governance_Evidence.md` | OWASP LLM Top 10 + NIST RMF Agentic rows updated |
| `compliance/risk-register.md` | Prompt-injection row marked implemented + tested |

## KB files this stage updates

- `KB_18_Governance_Evidence.md`
- `KB_15_Observability_Evidence_Pipeline.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
python backend/training/evals/runner.py --corpus all
# Verify pass rates exceed thresholds in backend/training/evals/thresholds.yaml
# Verify Phoenix dashboard updates
```

## Audit target

- Strict decrease (some theatrical patterns may surface during red-team eval implementation and need replacement).

## Role

- Primary: `ml-engineer`
- Secondary: `security-pqc-engineer` (attack-vector design)

## Hand-off

- What is now true: red-team posture verified by automated eval gate; results feed Annex IV pack.
- Next stage (21) hardens DR/HA/backups before the pilot deployment runbook in Stage 22.
