---
status: done
stage: 11
slug: langgraph_runtime
created: 2026-05-18
closed: 2026-06-15
progress: "CLOSED 2026-06-15 (5 increments). Runtime core + durable Postgres checkpointer (verified vs real Docker PG@5544) + tracing + coordinate() + decision_engine/rl_policy de-mock (G-052) + G-044 test harness + process-gap sweep (G-015/G-038/G-039/G-048) + risk-register refresh. Independent review PASS (audits/STAGE_11_independent_review.md). Full-infra live verification (PG+Neo4j+Redis): 186 passed/1 skipped, audit 364; surfaced+fixed G-053 (ws_broker shutdown deadlock) + G-054 (api task leak); discharged G-049/G-050 R-IND. ADRs: 2026-06-14_stage11_langgraph_runtime_core.md, 2026-06-14_stage11_runtime_complete.md, 2026-06-15_stage11_full_infra_verification.md."
---

# Stage 11 — LangGraph + Pydantic AI Agent Runtime (PULLED FORWARD)

> Migrate the bespoke coordinator (`backend/agents/embodied_agent.py`) to a LangGraph + Pydantic AI runtime under `backend/agents/runtime/`. Deterministic graph execution, Postgres checkpointer, HITL `interrupt()` primitives, LangSmith / Langfuse tracing. Public contract `coordinate(incident) -> list[Decision]` preserved. Models from Stages 4–10 are wired in as direct Python imports here; they become MCP tools in Stage 11.5.

## Pre-requisites

- Stages 4–10 closed (real models exist for the runtime to call).
- CTO Checkpoint #2 (Stage 10.5) completed; its remediations routed.
- `knowledge-base/KB_06_Agent_Coordination_Protocol.md` reframe locked.

## Acceptance criteria

- [x] `backend/agents/runtime/graph.py` defines a LangGraph `StateGraph` — nodes: observe, orient (predict + TTF world-model), diagnose (learned-causal), explain (SHAP), decide, verify (neuro-symbolic), hitl-confirm (conditional), execute, log. (The KB_25 self-healing loop; per-domain decide-robotics/manufacturing/supply is the legacy `run_all_agents` concern, retained.)
- [x] `backend/agents/runtime/state.py` defines `AgentState` (Pydantic) + `Decision`. (Minimal state per research §17; effectively immutable per super-step.)
- [x] `backend/agents/runtime/checkpointer.py` wires `langgraph.checkpoint.postgres.PostgresSaver` (pool-backed) against the project's Postgres — VERIFIED durable (setup + per-super-step persist + fresh-saver reload). Alembic `0002_langgraph_checkpoints`.
- [x] `backend/agents/runtime/hitl.py` implements `interrupt()` for SIL 1+ decisions (fail-safe; full safety wrapper Stage 17).
- [x] `backend/agents/embodied_agent.py` gains `coordinate(incident) -> list[Decision]` delegating to the runtime (thin wrapper; legacy `run_all_agents` retained alongside).
- [x] Tracing wired (`agents/runtime/tracing.py`): always-on per-node `AgentState.trace` + env-gated Langfuse/LangSmith callbacks; `main.py` builds the runtime + logs tracer status at startup. (Live Langfuse dashboard render needs the observability compose stack — env-gated, graceful.)
- [x] `pytest tests/agents/runtime/ -q` green (7 pass incl. PG durability); 80-test client+core+runtime regression green; no agent-coordination regression.
- [~] `scripts/audit.sh`: HOLDS at 364 (`--no-baseline-drop`). The de-mocked decision-engine theatre is dict-literal/synthetic (audit-invisible, Rule 1a), so the grep count does not move; no grep-counted theatre exists in these files to remove. Justified in KB_TASK_LOG.

### CTO Checkpoint #2 remediations (routed 2026-06-14 from `audits/CTO_2_remediation_map.json`; re-homed here from STAGE_11_5 after the router's G-015 string-sort mis-route)

- [x] (CTO #2) Wire the deepened models into the live runtime — DONE 2026-06-14: the runtime nodes call the real RUL/world-model, learned-causal diagnosis, exact-SHAP, intervention policy + binding plan verifier; decisions persist via the Postgres checkpointer; HITL via `interrupt()`. [~] Ollama-local LLM failover: the self-healing loop is LLM-FREE by design (runs ML models); `agents/llm_client.py` retains the Groq→Ollama fallback; a LIVE failover proof needs a local Ollama daemon (infra) → PARTIAL, ledgered.
- [x] (CTO #2) Fix the test harness G-044 — DONE 2026-06-14: conftest `client` + WS `sync_client` now run the app lifespan (degrades gracefully w/o Neo4j; `/health`+`/ready`→200). `test_api` 21-failed→24-passed; `test_websocket_smoke` hang→2-passed; full suite no longer hangs. (Neo4j-in-test-stack not required — the lifespan degrades; G-044 RESOLVED.)
- [x] (CTO #2) Refresh `compliance/risk-register.md` — DONE 2026-06-14: corrected stale stage numbers (defect 5→9, demand 6→5); added a "v3 depth-hardening + Stage-11" section (RUL transformer, ResNet18 defect, MaskablePPO, causal discovery, plan-verifier no-op/binding, LangGraph durability, audit-invisible-theatre, new-OSS supply chain, pandas/tts conflict); added a "Last full refresh" note.
- [x] (CTO #2) Sweep the deferred process gaps — DONE 2026-06-14: G-015 (remediation-router now matches the exact frontmatter `stage:`, not a prefix glob), G-038 (unified slug→role into `context_loader.suggest_role_from_slug` with word-boundary matching), G-039 (`pre_tool_use.sh` §9 blocks net-shrink of `KB_TASK_LOG.md`/`research/initial-research.md`), G-048 (`close-task.sh` base-10 + single-line gap counts). All verified; ledger rows RESOLVED.
- [x] (CTO #2) Run the 5 owed per-increment independent reviews (Stages 8/9/7/10/6 depth-hardening) + an independent CTO #2 pass — DONE 2026-06-14 via fresh `general-purpose` agents adopting the `task-auditor`/`cto-reviewer` personas → `audits/STAGE_0{6,7,8,9,10}_depth_independent_review.md` (all PASS) + `audits/CTO_2_independent_review.md` (CONCUR). Their Bash/pytest was denied → STATIC verification (G-049/G-050 R-IND caveat); the **R-IND belt-and-suspenders dynamic run is now discharged** (2026-06-15): a run-capable session re-ran the full suite + `audit.sh` + PG-durability against the real Docker stack — 186 passed/1 skipped, audit 364. ADR `2026-06-15_stage11_full_infra_verification.md`.
- [x] **Full-infra live verification (2026-06-15)** — Docker PG@5544 (local-shadow re-mapped) + Neo4j@7687 (app connects + schema init) + Redis@6379: full suite **186 passed / 1 skipped**, runtime 7/7 incl. PG durability vs real PG, audit **364**, zero pending-task warnings. Surfaced + FIXED two real production defects: **G-053** (`ws_broker.stop()` deadlock → bounded `get_message` polling + time-boxed stop) and **G-054** (`ExternalAPIClient` task leak → lifespan closes + `close()` awaits).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/agents/runtime/__init__.py` | Package marker |
| `backend/agents/runtime/graph.py` | LangGraph StateGraph definition |
| `backend/agents/runtime/state.py` | Pydantic `AgentState` |
| `backend/agents/runtime/checkpointer.py` | Postgres checkpointer setup |
| `backend/agents/runtime/hitl.py` | HITL interrupt nodes |
| `backend/agents/runtime/nodes/*.py` | Per-node implementations |
| `backend/tests/agents/runtime/test_canned_decision.py` | End-to-end trace test |
| `backend/alembic/versions/0006_langgraph_checkpoints.py` | Schema for langgraph_checkpoints |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/agents/embodied_agent.py` | Wrap new runtime; keep `coordinate()` signature |
| `backend/requirements.txt` | Add `langgraph`, `langgraph-checkpoint-postgres`, `pydantic-ai`, `langfuse`, `langsmith` (Apache 2.0 or MIT; pin versions) |
| `backend/main.py` | Initialize LangGraph runtime + Langfuse tracer on startup |
| `knowledge-base/KB_06_Agent_Coordination_Protocol.md` | Update with concrete node graph + checkpointer schema |
| `knowledge-base/KB_01_System_Architecture.md` | Topology diagram updated |

## KB files this stage updates

- `KB_06_Agent_Coordination_Protocol.md`
- `KB_01_System_Architecture.md`
- `KB_15_Observability_Evidence_Pipeline.md` (trace coverage)
- `KB_TASK_LOG.md`

## Verification commands

```bash
cd backend && alembic upgrade head
cd backend && pytest tests/agents/runtime/ -v
docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d
# Verify Langfuse trace renders at http://localhost:3001 after running the canned test
```

## Audit target

- Pre: capture from `.audit-baseline` at stage open.
- Target: strict decrease — the bespoke coordinator's heuristic-action fallbacks at `backend/ml/rl_policy.py:267-335` and similar should drop as the LangGraph runtime delegates to the real Stage 7 PPO policy.

## Role

- Primary: `backend-engineer`
- Secondary: `devops-sre` (observability wiring), `ml-engineer` (model integration)

## Risks / unknowns

- LangGraph version churn: pin major version; tests cover the API surface we use.
- Postgres checkpointer schema bloat: monitor; add retention policy in Stage 21.
- HITL `interrupt()` UX needs frontend support; Stage 11 frontend follow-up may be needed.

## Hand-off

- What is now true: agent runtime is a deterministic LangGraph; every decision produces a trace; HITL interrupts are wired (full safety wrapper in Stage 17).
- What the next stage (11.5) starts with: a runtime ready to mount MCP tool servers.
- Open items deferred: full audit_chain signing (Stage 13.5); A2A external boundary (Stage 14); functional safety wrapper (Stage 17).
