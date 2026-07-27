# ADR — Stage 11 (increment 2): durable checkpointer + tracing + decision-engine de-mock + test-harness fix

**Date**: 2026-06-14
**Status**: Accepted (Stage 11 increment 2 — completes the runtime; see increment 1
`2026-06-14_stage11_langgraph_runtime_core.md`)
**Author personas**: `backend-engineer` (primary) + `ml-engineer` + `devops-sre` + `agentic-governance-engineer`
**Relates**: pays CTO #2 remediations G-044 (test harness), G-052 (decision-engine fabrication), and the runtime's
Postgres checkpointer + tracing ACs. Research §17. Follows Hard Rule 1a (audit-invisible theatre) + 11/11b.

---

## Context

Increment 1 delivered the self-healing LangGraph runtime core (MemorySaver, HITL, binding verifier). This increment
completes Stage 11's durable-execution + observability ACs and pays the CTO #2 remediations that were folded in.

## Decisions

**D1 — Durable Postgres checkpointer (verified).** `agents/runtime/checkpointer.py` now returns a **pool-backed
`PostgresSaver`** (`psycopg_pool.ConnectionPool` — the documented durable-app pattern, not the scoped
`from_conn_string` context manager) when `DATABASE_URL` is reachable, else MemorySaver (named honestly). **Verified
against a clean Postgres:** `setup()` creates the checkpoint tables, a graph run persists one checkpoint per
super-step, and a **fresh saver instance durably reloads** the run. Alembic `0002_langgraph_checkpoints` invokes the
idempotent `setup()` so the tables join the migration chain (chained from `0001_init` — stages 2–5 added none, so the
task's "0006" name was hypothetical). Pin: `langgraph-checkpoint<3` (4.x breaks langgraph 0.2.60 via the
`Reviver(allowed_objects=...)` mismatch — a dependency conflict caught + resolved this session); `psycopg[binary]`
supplies libpq on Windows.

**D2 — Observability tracing, honest + env-gated.** `agents/runtime/tracing.py`: the always-on per-node
`AgentState.trace` is the dependency-free Art-12 record; Langfuse (`LANGFUSE_*`) / LangSmith (`LANGCHAIN_TRACING_V2`)
callbacks attach ONLY when configured (never a fake trace). `run_incident` passes them; `main.py` builds the runtime
at startup and logs the checkpointer backend + tracer status.

**D3 — decision_engine de-mock (G-052; Rule 1a audit-invisible theatre).** Removed the live fabrications the
independent CTO #2 caught: `explain_decision` (hardcoded SHAP/attention/counterfactuals → delegates to the real
`Explainer` / honest-empty; key_factors derived from real reasoning — done at CTO #2), `_get_predictions`
(`×1.02/1.01` fabricated growth → honest **naive-persistence** baseline, labelled `source`), and `predict`
(synthetic `0.9-h*0.01` confidence + fake `±10%` bounds + false `"lstm-v1"` → honest model-or-naive labelling:
`is_naive_baseline`, `confidence_basis`, bounds only when a real model provides them, a labelled LOW 0.25 confidence
for the naive path). Removed the vestigial `import random` in `rl_policy._generate_heuristic_actions` (a
deterministic threshold heuristic — documented as such, not theatre). These are dict-literals the audit grep can't
see (Rule 1a), so the baseline **holds at 364** (`--no-baseline-drop`); the theatre removed is real but grep-invisible.

**D4 — Test-harness fix (G-044; RESOLVED).** The conftest `client` fixture (and the WS smoke `sync_client`) now run
the app **lifespan** (`app.router.lifespan_context` / `TestClient` context-manager) so `state_manager` /
`decision_engine` / `SimWorld` initialise — the lifespan degrades gracefully without Neo4j/Firebase/MQTT (verified:
`/health` + `/ready` → 200). Result: `test_api` **21 failed → 24 passed**; `test_websocket_smoke` **hang → 2 passed**;
no regression (80 passed / 1 skip across the client + core + runtime suites). The full local suite no longer hangs.

## Why
- A runtime that "checkpoints" only in memory isn't durable; the pool-backed PostgresSaver makes pause/resume real
  and is the Art-12 evidence path — verified, not asserted.
- The decision-engine fabrications were exactly the audit-invisible theatre Rule 1a now forbids; honest naive
  baselines + labelling remove them without breaking the API contract.
- The G-044 lifespan fix converts 21 misleading 503 failures + a hang into a genuinely-exercised live app path.

## Consequences
- New: `0002_langgraph_checkpoints.py`, `agents/runtime/tracing.py`, this ADR. Modified: `checkpointer.py`
  (pool-backed), `graph.py` (tracing callbacks), `main.py` (runtime + tracer startup), `decision_engine.py` (de-mock),
  `rl_policy.py` (vestigial import), `conftest.py` + `test_websocket_smoke.py` (lifespan), `requirements.txt`,
  runtime tests (+checkpointer/tracing/PG-durability). KB_06 (node graph), KB_01 (topology), risk register.
- Audit holds 364 (`--no-baseline-drop`, Rule 1a). Tests: runtime 7 (+PG durable), test_api 24, ws 2, 80-test
  targeted regression green.
- G-044 RESOLVED; G-052 RESOLVED (decision-engine fabrications removed; rl_policy heuristic is honest-deterministic).

## Honest residual (Stage 11 close scope)
- The legacy `embodied_agent.run_all_agents` multi-agent cycle is RETAINED alongside the runtime (a different
  concern from incident-coordination); `coordinate()` is the runtime-backed public contract. Full retirement of the
  legacy cycle is optional future cleanup, not a Stage-11 blocker.
- **Ollama-local LLM failover proof** (CTO #2 R5): the self-healing loop is LLM-FREE by design (it runs ML models),
  so the runtime doesn't exercise the LLM; `agents/llm_client.py` retains the Groq→Ollama fallback. A live failover
  test needs a local Ollama daemon (infra) → remains PARTIAL, ledgered.
- Per-stage INDEPENDENT review required before final close (Rule 11b).

## References
- `agents/runtime/{checkpointer,tracing,graph}.py` · `alembic/versions/0002_langgraph_checkpoints.py` ·
  `services/decision_engine.py` · `tests/conftest.py` · `tests/agents/runtime/test_canned_decision.py`.
- Increment-1 ADR `2026-06-14_stage11_langgraph_runtime_core.md`. Research §17. KB_01/06/25.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:30+00:00 -->
<!-- signature: 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 -->
