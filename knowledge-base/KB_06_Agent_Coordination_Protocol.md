---
name: Agent Coordination Protocol
description: How the embodied agent and sub-agents communicate, resolve conflicts, and handle operator overrides — LangGraph + MCP (internal) + A2A (external) reframe per PRD v2.0
type: spec
last-updated: 2026-05-18
---

> **2026-05-18 PRD v2.0 reframe.** The bespoke coordinator is migrating to a **LangGraph + Pydantic AI runtime in Stage 11** (pulled forward from the original Stage 11+ slot). Internal agent → tool calls go through **MCP** (Stage 11.5) — five FastMCP servers: `sim_world`, `kpi_query`, `decision_log`, `model_inference`, `policy_query`. External agent ↔ agent communication goes through **A2A** (Stage 14) with ML-DSA-65 signed agent cards and ML-KEM-768 + X25519 hybrid mTLS. See [KB_16_A2A_MCP_Protocols.md](KB_16_A2A_MCP_Protocols.md). Existing bespoke coordinator stays in service through Stages 2–10; Stage 11 swaps the substrate without breaking the public `coordinate(incident) → list[Decision]` contract. Every decision written to the `audit_chain` table (Stage 13.5+) is signed with ML-DSA-65. HITL interrupts use LangGraph's `interrupt()` primitives — see `compliance/human-oversight.md`.

# KB_06 — Agent Coordination Protocol

## Purpose
The embodied agent orchestrates three sub-agents (Robotics, Manufacturing, Supply Chain). This file defines the message format between them, the decision sequence, conflict-resolution rules, and human-override semantics. From Stage 11 onward, the runtime is LangGraph + Pydantic AI; internal tool calls use MCP; external agent-to-agent coordination uses A2A.

## Source of truth
- `backend/agents/embodied_agent.py` — coordinator
- `backend/agents/base_agent.py` — sub-agent base class
- `backend/agents/{robotics,manufacturing,supply_chain}_agent.py` — sub-agents
- `backend/agents/llm_client.py` — LLM provider abstraction (Groq, Gemini, Ollama)

## Architectural decision (Stage 0 refresh)

**Bespoke coordinator for Stages 1–10. Optional LangGraph migration in Stage 11.**

Rationale: LangGraph won the 2026 framework war (production-grade observability via LangSmith, native state checkpointing, streaming). However, our current coordinator is functional and the value of migration is highest where audit-trail logging matters most (voice/RAG in Stage 11) — not in foundation stages where it's pure migration tax. Decision logged in `compliance/decision-logs/` on Stage-1 close.

The migration is a substrate swap, not a contract change. The public interface (`EmbodiedAgent.coordinate(incident) -> list[Decision]`) stays stable regardless of substrate.

## Message format (between embodied agent and sub-agents)

```python
class CoordinationRequest:
    incident_id: UUID
    incident_type: str           # one of the six in KB_05
    incident_payload: dict
    world_state_snapshot: dict   # current Redis hot state
    horizon_minutes: int         # 5 by default, up to 60
    constraints: dict            # safety constraints (Stage 7 reward-shaping)

class SubAgentProposal:
    incident_id: UUID
    proposing_agent: Literal["robotics", "manufacturing", "supply_chain"]
    actions: list[Action]
    predicted_outcome: dict      # expected KPI deltas
    confidence: float
    reasoning: str               # human-readable

class Decision:
    decision_id: UUID
    incident_id: UUID
    chosen_actions: list[Action]
    rationale: str               # LLM-generated summary of why these actions
    shap_attribution: dict       # filled by Stage 10
    dice_counterfactual: dict    # filled by Stage 10
    operator_override: Optional[OperatorOverride]
```

## Decision sequence (OODA-style)

1. **Observe** — Embodied agent receives `incident` from simulator (or DB / chat / button).
2. **Orient** — Embodied agent calls world model (`predict(state, horizon=15min)`) for projected state with and without intervention.
3. **Decide (parallel)** — Embodied agent fans out a `CoordinationRequest` to all three sub-agents simultaneously. Each returns a `SubAgentProposal`.
4. **Resolve** — Embodied agent picks the action set that maximizes the global reward (PPO policy in Stage 7) subject to safety constraints; resolves conflicts via the rules below.
5. **Act** — Embodied agent dispatches the chosen actions to the simulator (and, in v2, to real plant systems).
6. **Explain** — SHAP + IG + DiCE backfilled (Stage 10), cached, attached to the `Decision`.
7. **Log** — Decision row written to `decision_logs` table (EU AI Act Art. 12 evidence).
8. **Broadcast** — `decision` envelope sent on the WS so the frontend renders the decision card.

## Conflict-resolution rules

If two sub-agents propose contradictory actions (e.g. Robotics wants to redirect Robot 5 to Stage 7 while Manufacturing wants to pause Stage 7):

1. **Safety wins.** Any action violating a hard constraint (zero throughput, robot velocity > limit, charging-station overflow) is dropped regardless of who proposed it.
2. **Higher predicted reward wins.** PPO policy scores each proposal; max wins.
3. **Tie → embodied agent LLM prompt** asks for a tiebreak rationale with the world-state snapshot as context (prompt-injection sanitized per Stage 11).
4. **All conflicts logged** with both proposals + the tiebreak reasoning in `decision_logs.payload`.

## Operator override semantics (Stage 12)

When an operator clicks "Override" on a decision card:

1. Frontend sends `override` envelope on WS with `{decision_id, override_action, reason}`.
2. Embodied agent receives it; writes a row to `decision_logs` with `operator_override=true`.
3. The override action becomes the executed action; the AI's action is recorded as "not taken" in the log.
4. Override events feed a future feedback-learning loop (post v1).

EU AI Act Art. 14 (human oversight) requires this exact pattern: operator can override, the override is logged, and the system is constructed such that the operator can intervene before an action is irreversibly executed.

## Prompt-injection mitigation (Stage 11)

Every LLM call in the coordination flow receives a sanitized context:
- World-state snapshot is serialized as JSON, not natural language. JSON schema is enforced before injection into the prompt.
- Tool outputs (database row reads, external API responses) are sanitized via a prompt-injection filter (heuristic + classifier) before being included in any LLM context.
- Cross-session memory is namespaced by `incident_id`; the agent has no memory of other incidents in the same operator session.

## Failure modes

- **Sub-agent unreachable** — Embodied agent times out at 200 ms; falls back to a no-action proposal from that domain (logged as a SOFT_FAILURE).
- **LLM unreachable (Groq outage)** — Stage 11 acceptance: Ollama-local LLM (Llama 3 or Qwen 2.5) is the fallback. Decision tagged with `llm_source=ollama-local`.
- **World model unreachable** — Embodied agent falls back to "current state = predicted state" (no foresight); decision tagged as such.

## Hierarchy, message recording & access control (added 2026-05-31)

The coordinator is a **hierarchy**: L3 EmbodiedCoordinator → L2 Head agents (Robotics/Manufacturing/SupplyChain
+ Quality/Workforce-Safety/Energy/Facilities) → L1 domain/worker agents → L0 external A2A peers. Messages route
up (problem/report) and down (command/diagnose).

**Message types** now include the active-diagnosis pair (KB_25 §1b): `diagnose.request` (coordinator/head →
agent: run a named self-check) and `diagnose.report` (agent → up: result + health vector; timeout ⇒ fault).
**IMPLEMENTED Stage 29 (G-026):** `backend/conversation/active_diagnosis.py` runs the pair under an information-gain
(entropy-reduction) test-selection policy — the coordinator issues the `diagnose.request` that maximises mutual
information about the fault hypothesis, Bayes-updates on the `diagnose.report`, and commits/abstains; a non-responding
agent (timeout/exception) is localized as the fault. Each report is best-effort ledged (`diagnose.report` audit row).

**Recording (governance — KB_18):** every message records `{from,to,type,payload_hash,ts,correlation_id}`; a
`state_snapshot(pre)` and `state_snapshot(post)` bracket every incident/decision; every decision is signed into
`audit_chain`. **Access:** function-scoped RBAC (an agent acts only within its `function_category`) + Bell-LaPadula
MAC (no read-up / no write-down across hierarchy levels + categories). Enforced Stage 11.5/19; see KB_18.

## Stage 11 — concrete LangGraph runtime node graph (2026-06-14)

The bespoke OODA coordinator is now realised as a durable LangGraph `StateGraph` in `backend/agents/runtime/`
(`EmbodiedAgent.coordinate(incident)` delegates to it). Deterministic nodes, minimal Pydantic `AgentState`, one
checkpoint per super-step keyed by `thread_id`:

```
START → observe → orient (failure predictor + TTF world model) → diagnose (learned-causal, services.diagnosis)
      → explain (exact-SHAP) → decide (intervention_policy) → verify (neuro-symbolic plan_verifier, BINDING)
      ─(hitl_required = approved & SIL>=1)─→ hitl_confirm [interrupt()] → execute (sim-only) → log → END
                                          └────────────(else)──────────────────────────────→ execute
```

- **Checkpointer:** `agents/runtime/checkpointer.py` — pool-backed `PostgresSaver` when `DATABASE_URL` is reachable
  (tables via alembic `0002_langgraph_checkpoints` / idempotent `setup()`), else MemorySaver (named honestly).
  Verified: a run persists one checkpoint per super-step and a fresh saver durably reloads it.
- **HITL:** `interrupt()` on SIL-1+ decisions; fail-safe (never auto-approves). Full safety wrapper = Stage 17.
- **Tracing:** `agents/runtime/tracing.py` — always-on per-node `AgentState.trace`; optional Langfuse/LangSmith via
  env (`LANGFUSE_*` / `LANGCHAIN_TRACING_V2`), attached only when configured (no fake traces).
- **Verifier note (G-051):** the Stage-6 slice relaxed the PlantState (no-op gate); the runtime uses a BINDING
  PlantState so `verify` genuinely rejects unsafe plans. ADR `2026-06-14_stage11_langgraph_runtime_core.md`.

## Last verified
- 2026-05-11 — Plan-mode session. Coordinator + sub-agent files confirmed present; OODA structure intact; ML hooks pointing at fakes (Stage 4+ replaces).
- 2026-05-31 — Hierarchy levels, diagnose message types, full message/state/decision recording, RBAC + Bell-LaPadula MAC added (spec; Stages 11.5/19). Cross-ref KB_18 + KB_25.
- 2026-06-14 — Stage 11 LangGraph runtime node graph realised (above); durable Postgres checkpointer verified; HITL `interrupt()` + env-gated tracing wired.
