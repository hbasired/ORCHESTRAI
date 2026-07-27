# Stage 11 — Independent Review (task-auditor)

**Stage:** 11 — LangGraph + Pydantic AI durable agent runtime
**Reviewer:** independent `task-auditor` (did NOT implement Stage 11)
**Date:** 2026-06-14
**Scope:** `tasks/STAGE_11_langgraph_runtime.md`; ADRs `2026-06-14_stage11_langgraph_runtime_core.md` +
`2026-06-14_stage11_runtime_complete.md`; all new/modified runtime, service, test, KB, and config files.

---

## VERDICT: **PASS** (with one process caveat + minor housekeeping nits — none close-blocking)

The Stage 11 runtime is real, deep, and honest. Every claim I could verify statically holds; the new runtime
code introduces zero theatrical patterns; the two de-mocks (G-052, explainability) genuinely remove fabrication;
the binding verifier is grounded in real symbolic logic; G-044 is genuinely fixed. The audit `--no-baseline-drop`
hold is honestly justified (the de-mock is grep-invisible). The one caveat is an **execution-environment
limitation on my side** (below), mitigated by thorough static verification.

---

## EXECUTION LIMITATION (stated explicitly, per SKILL.md)

**I could NOT run pytest or `scripts/audit.sh` myself.** Both the `Bash` tool (for pytest) and the `PowerShell`
tool were **denied by the permission layer** in this session; only `git` invocations through Bash succeeded.
I therefore could **not** independently reproduce the green-test or `TOTAL 364` numbers by execution.

To compensate I performed a rigorous static review: read every runtime source + test file, the de-mocked files,
the conftest/lifespan harness, the alembic migration, the service dependencies the nodes call, `audit.sh`'s
pattern set, the requirements pins, `main.py` wiring, the KB/risk-register/KB_TASK_LOG diffs, and confirmed the
model weights the tests depend on exist on disk. Where I rely on static reasoning instead of a live run I say so
in the evidence table. **The claimed numbers are structurally consistent with the code, but a fresh live pytest +
audit run is still owed before close** (a clean re-run by an agent with Bash/PowerShell access would close this).

---

## Per-criterion evidence

| # | Criterion | Claimed | Independently confirmed? | Note |
|---|---|---|---|---|
| AC1 | `graph.py` StateGraph: observe→orient→diagnose→explain→decide→verify→[hitl]→execute→log | done | **Yes (static)** | `backend/agents/runtime/graph.py:35-57` — exact node set + conditional edge `_route_after_verify` (hitl iff `hitl_required`). Real LangGraph `StateGraph(AgentState)`. |
| AC2 | `state.py` minimal Pydantic `AgentState` + `Decision` | done | **Yes (static)** | `state.py:16-59` — `Decision`, `TraceEvent`, `AgentState`; partial-update merge model; per-node `trace`. |
| AC3 | `checkpointer.py` pool-backed PostgresSaver + honest MemorySaver fallback; alembic | done | **Partial (static)** | `checkpointer.py:26-49` returns `(PostgresSaver, "postgres")` via `psycopg_pool.ConnectionPool` when `DATABASE_URL` reachable + `cp.setup()`, else `(MemorySaver, "memory")` — backend named honestly. Alembic `0002_langgraph_checkpoints.py` invokes idempotent `setup()`, never hard-fails the chain. **Live PG round-trip NOT re-run by me** (ephemeral container gone); code path is correct. |
| AC4 | `hitl.py` `interrupt()` fail-safe (never auto-approves) | done | **Yes (static)** | `hitl.py:16-41` — consumes pre-supplied resolution; else `langgraph.types.interrupt(...)`; on exception leaves `hitl_resolution=None` (UNCONFIRMED) — explicitly NOT auto-approve. |
| AC5 | `embodied_agent.coordinate()` thin wrapper; legacy `run_all_agents` retained | done | **Yes (static)** | `embodied_agent.py:123-134` delegates to `agents.runtime.run_incident`; `run_all_agents` retained at :136. |
| AC6 | Tracing: always-on `AgentState.trace` + env-gated Langfuse/LangSmith; `main.py` startup | done | **Yes (static)** | `tracing.py:18-32` attaches Langfuse callback ONLY when `LANGFUSE_*` set; LangSmith via env; empty list otherwise (no fake handler). `main.py` diff builds runtime + logs `checkpointer` backend + `tracing_status()`. |
| AC7 | `pytest tests/agents/runtime/` green (7 incl. PG durability); regression green | done | **Structurally consistent; NOT executed** | `test_canned_decision.py` has **exactly 7** test fns (confirmed by count). `test_api.py` 32 defs → "24 passed" plausible. **Could not run pytest** (tool denied). |
| AC8 | `audit.sh` HOLDS 364 (`--no-baseline-drop`, Rule 1a) | done | **Yes (reasoned), NOT executed** | `.audit-baseline` = 364. New runtime files contain ZERO of `audit.sh`'s counted patterns (grep confirmed). De-mock removed only grep-invisible synthetic dict literals + a vestigial `import random` (not a counted pattern). Hold is honest. **Did not run `audit.sh`.** |

### Routed CTO #2 remediations

| Item | Claimed | Confirmed? | Note |
|---|---|---|---|
| Wire deepened models into live runtime | DONE | **Yes (static)** | `nodes.py` imports the real `failure_predictor`, `world_model`, `services.diagnosis`, `failure_explainer`, `intervention_policy`, `plan_verifier`; each degrades honestly (records unavailability, never fabricates — `nodes.py:46-49,95-96,104-105`). |
| Ollama-local LLM failover | **PARTIAL (ledgered)** | **Honest scoping** | Self-healing loop is genuinely LLM-free (runs ML models); a live failover proof needs an Ollama daemon. Disclosed in both ADRs + KB_TASK_LOG. Acceptable. |
| G-044 test harness | RESOLVED | **Yes (static)** | `conftest.py:28-41` `client` now enters `app.router.lifespan_context(app)`; `test_websocket_smoke.py:17-24` `sync_client` is `with TestClient(app)`. Both genuinely run the lifespan → services initialise → no more 503/hang. |
| Risk-register refresh | DONE | **Yes** | `compliance/risk-register.md` +26 lines (substantive, not cosmetic). |
| Process-gap sweep G-015/G-038/G-039/G-048 | DONE | not re-audited here | Out of Stage-11-runtime scope; logged as resolved in separate increments. |
| 5 owed per-increment independent reviews + independent CTO #2 | **OPEN `[ ]`** | confirmed open | Honestly left unchecked in the task doc. Tracked as G-049/G-050. |

---

## Adversarial findings

### Theatre / fabrication: **NONE in Stage 11 scope**
- `backend/agents/runtime/` — grep for `audit.sh`'s full pattern set (`random.uniform|random.choice|random.choices|
  _generate_mock_detections|_generate_mock_predictions|_generate_heuristic_actions|_get_demo_metrics`) → **0 matches**.
- `decision_engine.py` de-mock is real: `_get_predictions` (:255-262) is honest naive-persistence, **no ×1.02/×1.01
  growth**; `predict_future_state` (:441-480) labels `is_naive_baseline`/`confidence_basis`/fixed-low-0.25 confidence
  and emits bounds **only** when model-derived; `explain_decision` (:507-538) returns honest-empty on failure with
  **no hardcoded SHAP/attention/counterfactual dicts**; `key_factors` derived from real reasoning text. The only
  hits for `1.02`/`0.9 -`/`±10`/`lstm-v1` are in **comments documenting the removal**, not live code.
- `rl_policy.py` diff (:270-280) removed the vestigial `import random` and re-documented `_generate_heuristic_actions`
  as a deterministic threshold heuristic — verified it makes no `random.*` calls.
- `explainability.py:1-15` confirms the Stage-10 de-mock (real TreeSHAP for failure features, honest-empty otherwise).

### Verifier genuinely gates (G-051 paid in runtime): **confirmed real**
`nodes.py:127-156` builds a **binding** `PlantState` (real `available_crew`, throughput floor,
`max_concurrent_critical_offline`). `services/plan_verifier.py:153-166` enforces the SIL critical-redundancy
contract (`total_critical_down > max_concurrent_critical_offline` → violation). `test_runtime_verifier_genuinely_
rejects_unsafe_plan` constrains the plant so two critical machines (crack_proximity 0.95 + 0.90, both > the 0.85
critical threshold) are downed → 2 > max 1 → **REJECT**, asserts `approved is False` AND `executed is False`.
This is a real, behaviour-asserting test — not the Stage-6 no-op.

### Tests are honest, not no-ops
The 3 `@needs_brain` tests carry strong, specific assertions (full node-order equality; `"p_fail=0.9" in summary`;
real provenance present; reject not executed; HITL approve→executed / reject→blocked). **The model weights they
gate on exist** (`models/pdm_failure_predictor.pt` + `.scaler.pkl`), so `is_available()` should be True and these
tests **run rather than skip** — the high-value path is genuinely exercised. The non-brain tests (checkpointer
default-to-memory, tracing-status honesty, builds-with-checkpointer) assert real behaviour.

### Bypass / hard-rule violations: **NONE**
No `--no-verify`, no `--force`, no edited ADR, no classical-only crypto (n/a pre-13.5), no LLM-direct actuator
(loop is LLM-free; execute is sim-only, gated on approved+HITL). `--no-baseline-drop` is used on a stage with a
genuinely grep-invisible de-mock — legitimate per Rule 1a.

---

## Minor nits (housekeeping, NOT close-blockers)

1. **Stale comment — wrong migration name.** `checkpointer.py:10` still says the alembic migration is
   `0006_langgraph_checkpoints`; the actual (and correct) file is `0002_langgraph_checkpoints.py`. The ADR + the
   migration file both correctly explain the 0006→0002 rename, so this is only a stale docstring. Same hypothetical
   "0006" name lingers in the task doc's "Files to CREATE" table (cosmetic).
2. **Original audit target not met (documented).** The task doc's "Audit target" (line 80) called for a *strict
   decrease* by dropping `rl_policy.py` heuristic-action fallbacks as the runtime delegates to real PPO.
   `_generate_heuristic_actions` is fully **retained** (3 grep-counted occurrences remain) — the runtime routes
   through `intervention_policy`, not `rl_policy.get_action`, so that fallback is untouched. The stage instead held
   at 364 with a justified `--no-baseline-drop`. This is honest scoping (disclosed in the ADR + KB_TASK_LOG), but
   the original strict-decrease intent was **not** achieved; retiring the `rl_policy`/`decision_engine` heuristic
   fallbacks remains future work.
3. **Prebuilt runtime not reused.** `main.py` builds `agent_runtime` at startup, but `coordinate()` →
   `run_incident()` builds its own graph per call (the `app=` param is unused by the wrapper). Minor inefficiency;
   the startup log is still accurate. Not theatre.
4. **`langsmith` package not added** to requirements (only `langfuse==4.7.1`); LangSmith works via env + langchain
   auto-trace, consistent with `tracing.py`'s comment — so functionally fine, but the task doc's "add langsmith"
   line is technically unmet (no dedicated package needed).

---

## Owed before final close (process)

- **A fresh live `pytest` + `scripts/audit.sh` run** by an agent with shell access, to reproduce: runtime 7,
  test_api 24, ws 2, 80-test regression green, and `TOTAL 364`. (I could not execute these — tools denied.)
- The **5 per-increment independent reviews + independent CTO #2** (G-049/G-050) remain open `[ ]` in the task doc;
  this Stage-11 review does not discharge them.

## Honesty assessment

High. The ADRs and KB_TASK_LOG are candid about scope, residuals (legacy `run_all_agents` retained, Ollama
failover PARTIAL), the dependency conflict (langgraph-checkpoint 4.x pin), and the grep-invisible nature of the
de-mock. No overclaim found in the code I read. The "depth in the first pass" bar (Rule 11a) is met: durable
PostgresSaver (pool-backed, the documented durable pattern), binding verifier, real `interrupt()` HITL, env-gated
real tracing, and real model wiring — not a shallow placeholder runtime.

**VERDICT: PASS.** Recommend close once the live pytest + audit run is reproduced by a shell-capable agent (and
fix the stale `0006` docstring opportunistically).
