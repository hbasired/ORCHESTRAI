# ADR — Stage 11 (increment 1): LangGraph self-healing runtime CORE

**Date**: 2026-06-14
**Status**: Accepted (Stage 11 increment 1 of N — the runtime core; Stage 11 remains IN-PROGRESS)
**Stage**: 11 (LangGraph + durable agent runtime)
**Author personas**: `backend-engineer` (primary) + `ml-engineer` (model wiring) + `agentic-governance-engineer` (ADR)
**Relates**: consumes the Stage 4-10 depth-hardened models; pays CTO #2 remediation #1 (wire the deepened models into
a live runtime) and the spirit of G-051 (a genuinely-gating verifier). Research §17. Follows Hard Rule 11/11a/11b.

---

## Context

Stage 11 migrates the bespoke coordinator to a durable LangGraph runtime that gives the deepened models a live body.
It is a large, multi-increment stage (it also carries 5 routed CTO #2 remediations). This ADR records **increment 1
— the runtime core** — built deep + complete + tested, with the remaining items honestly scoped as continuation
(Rule 11b: a complete coherent sub-unit, not a half-stage claimed done).

## Decisions

**D1 — A deterministic, durable LangGraph `StateGraph` self-healing runtime** (`backend/agents/runtime/`):
`observe → orient (predict + TTF forecast) → diagnose (learned-causal) → explain (SHAP) → decide → verify
(neuro-symbolic) → [hitl_confirm] → execute → log`. Minimal Pydantic `AgentState` (research §17: small state =
clean checkpoint diffs); nodes return partial updates + append a `trace` event (the Annex-IV/audit-chain provenance).
Files: `state.py`, `nodes.py`, `hitl.py`, `checkpointer.py`, `graph.py`, `__init__.py`.

**D2 — Real deepened models wired as direct Python imports** (they become MCP tools in Stage 11.5): the XGBoost
failure predictor, the Stage-8 TTF world model (when a telemetry window is supplied), `services.diagnosis` (with the
Stage-8B learned-causal attribution), the Stage-10 exact-SHAP `failure_explainer`, `services.intervention_policy`,
and the Stage-8C `plan_verifier`. **Honest by design:** every node degrades gracefully and records what actually
ran in the trace — a missing model is reported, never fabricated (no node returns a plausible fake).

**D3 — The runtime verifier GENUINELY gates (pays G-051 in the runtime).** Unlike the Stage-6 slice (unlimited-crew,
relaxed PlantState → never rejects), the runtime's `verify` node builds a **BINDING** PlantState (real
`available_crew`, throughput floor, SIL critical-redundancy from the incident's plant snapshot), so it **actually
rejects** unsafe plans — proven by `test_runtime_verifier_genuinely_rejects_unsafe_plan` (a 2nd critical machine
already offline → reject → not executed). Execution only fires on an APPROVED, HITL-cleared plan.

**D4 — HITL via the `interrupt()` primitive.** `hitl_confirm` pauses (durably, via the checkpointer) on SIL-1+
decisions and resumes with the operator's resolution; pre-supplied resolutions are consumed deterministically
(tests/replays). Fail-safe: if `interrupt()` is unavailable it leaves the decision UNCONFIRMED (never auto-approves).
The full functional-safety wrapper is Stage 17.

**D5 — Durable checkpointer, honestly tiered.** `get_checkpointer()` returns PostgresSaver when
`langgraph-checkpoint-postgres` + a DB URL are present and reachable, else MemorySaver — and names the backend in
use (no fake durability). The Postgres checkpoint table + alembic migration land with the DB-wiring increment.

**D6 — Public contract.** `EmbodiedAgent.coordinate(incident) -> list[Decision]` added as a thin wrapper delegating
to `agents.runtime.run_incident`. The legacy `run_all_agents` coordination is retained alongside; its full migration
is continuation.

**D7 — Audit holds 364 (`--no-baseline-drop`), additive.** The runtime core adds zero theatrical patterns. (Also
this session: the live `decision_engine.explain_decision` fabrication found by the independent CTO #2 was de-mocked.)
The strict-decrease audit target for Stage 11 (dropping the `rl_policy`/`decision_engine` heuristic fallbacks, G-052)
lands with the de-mock increment.

## Why
- The deepened models were "brains without a body"; a durable, deterministic graph is the credible, SOTA way (research
  §17) to run them with resumability + HITL + provenance — the EU-AI-Act Art-12 evidence path.
- Building the core complete + tested (rather than a sprawling half-migration) honours Rule 11b; the binding verifier
  fixes the exact no-op weakness the independent review caught in Stage 6.

## Consequences
- New: `backend/agents/runtime/{__init__,state,nodes,hitl,checkpointer,graph}.py`,
  `backend/tests/agents/runtime/test_canned_decision.py` (4 tests, all pass). Modified: `agents/embodied_agent.py`
  (+`coordinate()`).
- 40 tests pass (runtime + model + diagnosis + verifier regression); audit holds 364; no regression.
- **Stage 11 remains IN-PROGRESS.** Continuation (honest hand-off): Postgres checkpointer + alembic table; Langfuse/
  LangSmith tracing + `main.py` startup wiring; full `embodied_agent` migration; `decision_engine`/`rl_policy`
  de-mock (G-052, strict-decrease); G-044 test-harness fix; risk-register refresh; process-gap sweep
  (G-015/G-038/G-039/G-048); KB_06/KB_01 topology updates; and the per-stage INDEPENDENT review before close.

## Alternatives rejected
1. **Rip out the whole bespoke coordinator now.** Rejected — a large risky refactor; the wrapper + retained legacy
   path is the safe, incremental migration. 2. **Reuse the Stage-6 relaxed PlantState in the runtime.** Rejected —
   that is the G-051 no-op; the runtime must genuinely gate. 3. **Auto-approve HITL when `interrupt()` absent.**
   Rejected — fail-safe leaves it unconfirmed.

## References
- `backend/agents/runtime/graph.py` (the StateGraph) · `nodes.py` (model wiring) · `tests/agents/runtime/test_canned_decision.py`.
- Research §17. KB: KB_06, KB_25. Continuation tracked in `tasks/STAGE_11_langgraph_runtime.md` + the gaps ledger.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:30+00:00 -->
<!-- signature: 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 -->
