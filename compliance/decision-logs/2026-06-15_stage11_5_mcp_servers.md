# ADR — Stage 11.5: MCP server suite + runtime mount

**Date**: 2026-06-15
**Status**: Accepted (Stage 11.5 — follows Stage 11 `2026-06-15_stage11_full_infra_verification.md`)
**Author personas**: `backend-engineer` (primary) + `agentic-governance-engineer` (architectural review)
**Relates**: KB_16 (server inventory), KB_07 (tool surface), KB_01 (topology). Research §18. Follows Hard Rule 1a
(honest-unavailable, no fabricated tool results), Rule 9 (free/OSS only), Rule 11/11a (deepest honest path; full
depth first pass), Rule 11b (finish completely; verify; ledger-and-fix).

---

## Context

Stage 11 built the durable LangGraph self-healing runtime consuming the Stage-4-10 models as direct Python imports.
Stage 11.5 exposes those models + the simulation + KPI + decision-log surfaces as **Model Context Protocol (MCP)**
tool servers and mounts them into the runtime — the standard agent↔tools boundary (KB_16), and the substrate the
A2A external boundary (Stage 14) and the memory layer (Stage 12) build on.

## Decisions

**D1 — Five FastMCP servers, each wrapping a REAL backend, honest-unavailable.** `backend/mcp_servers/` (official
`mcp` SDK's bundled `FastMCP`): `model_inference` (predict_failure/predict_demand/classify_defect → the real
XGBoost/LSTM/ResNet18 singletons), `policy_query` (recommend_action/explain_action → real diagnosis+intervention+
exact-SHAP), `kpi_query` (throughput/oee/utilization/queue_depth → real **A×P×Q** OEE from a plant snapshot, ideal
cycle time from the real stage calibration), `sim_world` (inject_event/query_state/subscribe_events → a real,
deterministic, synchronously-advanced SimPy world), `decision_log` (append/query → the real Postgres `decisions`
table). Every tool returns `{"available": false, "reason": …}` when its backend can't load — the truth, never a
fabricated result (Rule 1a). No `random.*`/mock patterns: audit holds **364**.

**D2 — Mount via a thin in-house stdio bridge, NOT `langchain-mcp-adapters`.** Every current
`langchain-mcp-adapters` release requires `langchain-core>=1.0`; our Stage-11 runtime is frozen on
`langchain-core 0.3.28` + `langgraph 0.2.60` (bumping it reintroduces the `Reviver` break resolved in Stage 11).
So `agents/runtime/mcp_mount.py::MCPToolMount` uses the official `mcp` stdio client directly (the same mechanism the
adapters package uses for stdio) and wraps each tool as a `langchain_core.tools.StructuredTool`, building the args
model from the tool's JSON `inputSchema`. Persistent sessions (one subprocess/server, kept alive) amortise the
heavy-ML import. `langchain-mcp-adapters` is ledgered for the future langchain-core-1.0 migration (research §18).

**D3 — Dependency pins (free/OSS).** `mcp==1.27.2`; **`starlette==0.41.3`** pinned as the cap for `fastapi 0.115.6`
(mcp's `starlette>=0.27` has no upper bound, so 0.41.3 satisfies it; stdio transport — CI + mount — doesn't touch
starlette); `pydantic` bumped `2.10.4→2.13.4` (mcp floor `>=2.11`; minor, suite green). `pytest-timeout` pinned.

**D4 — Three stdio-safety fixes (verified, not asserted).** A sync `@tool` runs in an anyio worker thread; a
first-time heavy import (torch/xgboost/numpy/simulation) **inside that thread deadlocks on the CPython import lock**
in an stdio subprocess (a silent hang — only reproduces over real stdio, not in-process). Fixes: (a) warm the heavy
imports at each server's module top-level (main thread); (b) advance SimPy **synchronously** (`env.run(until=…)`, no
background thread / no realtime `sleep`); (c) pass the **full parent env** to the spawned subprocess. Diagnosed +
fixed by running the real stdio path (Rule 11b: shallow work hides gaps; the in-process smoke had passed).

**D5 — Supervisor + runtime + CI.** `mcp_servers/__main__.py` runs the five as supervised streamable-HTTP services
(watchdog, ports 9101-9105; `--once` liveness smoke). `main.py` mounts the suite at startup when `MCP_MOUNT=1`
(env-gated; clean shutdown). CI gate **`mcp-conformance`** (Postgres service + the `backend/tests/mcp/` suite).

## Why
- MCP is the vendor-neutral agent↔tool standard (KB_16); making the models MCP tools is the prerequisite for A2A
  (Stage 14), the memory layer (Stage 12), and external tool-calling — and it is the "deepest honest" Stage-11.5
  build (real protocol, real backends, real conformance), not a stub.
- The in-house bridge keeps the working runtime pins frozen while still using the battle-tested official `mcp` SDK.

## Consequences
- New: `backend/mcp_servers/` (8 files), `backend/agents/runtime/mcp_mount.py`, `backend/tests/mcp/` (6 files,
  22 tests), the `mcp-conformance` CI job, this ADR, the explainer, KB_TASK_LOG entry. Modified: `main.py`
  (env-gated mount + shutdown), `requirements.txt`, KB_16/KB_07/KB_01.
- Verified end-to-end (real stdio + Docker Postgres@5544): MCP suite **22 passed / 1 skipped**; full backend suite
  **208 passed / 2 skipped**; supervisor `--once` all-alive; runtime mount loads 14 tools + invokes real ones.
  Audit holds **364** (`--no-baseline-drop`; the suite wraps real backends, adds no grep-counted theatre — Rule 1a).

## Honest residual / ledger
- `langchain-mcp-adapters` adoption deferred to the langchain-core-1.0 migration (G-056) — alongside the langgraph
  version-skew (G-055).
- `sim_world`/`kpi` servers run their OWN deterministic SimWorld per process (not the live app's world); cross-process
  shared-world wiring (or proxying to the app's REST inject/state) is a later integration (G-057).
- Streamable-HTTP transport is supervised + smoke-tested (`--once`); the runtime mount + CI use stdio. A live
  HTTP-client mount path is future (G-058, low).

## References
- `backend/mcp_servers/{__init__,_common,__main__,sim_world_server,kpi_query_server,decision_log_server,
  model_inference_server,policy_query_server}.py` · `backend/agents/runtime/mcp_mount.py` · `backend/tests/mcp/*` ·
  `backend/main.py` · `.github/workflows/ci.yml` (mcp-conformance). KB_16/07/01. Research §18.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:30+00:00 -->
<!-- signature: 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 -->
