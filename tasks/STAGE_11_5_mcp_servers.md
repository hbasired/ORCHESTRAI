---
status: done
stage: 11.5
slug: mcp_servers
created: 2026-05-18
closed: 2026-06-15
progress: "CLOSED 2026-06-15. 5 FastMCP servers (backend/mcp_servers/) wrapping real models/sim/KPI/Postgres-ledger, honest-unavailable; multiprocess+watchdog supervisor (HTTP); runtime mount via in-house stdio bridge (agents/runtime/mcp_mount.py::MCPToolMount) — langchain-mcp-adapters deferred (needs langchain-core>=1.0, G-056); main.py env-gated MCP_MOUNT. 22 conformance tests + CI mcp-conformance. Full suite 208 passed/2 skipped; audit 364. Independent review PASS (DYNAMIC). Residual: graph-node MCP consumption → Stage 12 (G-059); per-process sim world (G-057); HTTP mount path (G-058). ADR 2026-06-15_stage11_5_mcp_servers.md."
---

# Stage 11.5 — MCP Server Suite (FastMCP × 5)

> Five FastMCP-based servers under `backend/mcp_servers/`. Mounted into the LangGraph runtime from Stage 11 via `langchain-mcp-adapters`. See KB_16 for the server inventory and tool list.

## Pre-requisites

- Stage 11 closed; LangGraph runtime live.

## Acceptance criteria

- [x] Five servers exist and start cleanly under `python -m mcp_servers` (run from `backend/`):
  - `sim_world_server` — `inject_event`, `query_state`, `subscribe_events`
  - `kpi_query_server` — `throughput`, `oee`, `utilization`, `queue_depth`
  - `decision_log_server` — `append_decision`, `query_decisions` (direct Postgres write/read now; routes through `backend/memory/audit_chain.py` when Stage 13.5 lands)
  - `model_inference_server` — `predict_demand`, `predict_failure`, `classify_defect`
  - `policy_query_server` — `recommend_action`, `explain_action`
  — DONE: supervisor `--once` shows all 5 ALIVE (streamable-HTTP, ports 9101-9105). Each tool wraps a REAL backend, honest-unavailable.
- [x] `backend/mcp_servers/__main__.py` is a multiprocess supervisor with watchdog. — DONE (restart-on-death + `--once` smoke).
- [x] LangGraph runtime mounts all five — DONE via `backend/agents/runtime/mcp_mount.py::MCPToolMount` (a thin in-house bridge over the official `mcp` stdio client), NOT `langchain-mcp-adapters` (requires langchain-core>=1.0, off our frozen 0.3.28 — deferred, **G-056**). The mount loads all **14** tools (server.tool) + invokes real ones; `main.py` mounts when `MCP_MOUNT=1`. [~] **Graph-NODE consumption is deferred to Stage 12 (G-059)**: tools land on `app.state.mcp_tools`; the self-healing loop nodes still call models via direct imports (latency). Honest residual, ledgered.
- [x] Each tool has a schema test under `backend/tests/mcp/` (tools/list == documented manifest; input/output schema validates). — DONE: 22 tests pass (real stdio client) incl. a real Postgres decision-log round-trip + the runtime mount.
- [x] CI gate `mcp-conformance` runs on every PR. — DONE (`.github/workflows/ci.yml`, Postgres service + the MCP suite).
- [x] `KB_16_A2A_MCP_Protocols.md` server inventory matches reality. — DONE (reconciled 2026-06-15).
- [x] Independent review PASS (Rule 11b) — `audits/STAGE_11_5_independent_review.md` (DYNAMIC: reviewer re-ran audit.sh=364 + pytest tests/mcp/=22 passed/1 skipped).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/mcp_servers/__init__.py` | Package marker |
| `backend/mcp_servers/__main__.py` | Multiprocess supervisor |
| `backend/mcp_servers/sim_world_server.py` | Sim world tools |
| `backend/mcp_servers/kpi_query_server.py` | KPI query tools |
| `backend/mcp_servers/decision_log_server.py` | Decision-log writer tools |
| `backend/mcp_servers/model_inference_server.py` | Model inference tools |
| `backend/mcp_servers/policy_query_server.py` | Policy query tools |
| `backend/tests/mcp/test_<server>.py` × 5 | Schema + tool tests |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/agents/runtime/graph.py` | Mount MCP tools |
| `backend/requirements.txt` | Add `fastmcp`, `langchain-mcp-adapters`, `mcp` (Python SDK) — pin versions |
| `docker/docker-compose.yml` | Optional `mcp-servers` service (or run in backend process) |
| `.github/workflows/ci.yml` | Add `mcp-conformance` job |
| `knowledge-base/KB_16_A2A_MCP_Protocols.md` | Confirm server list matches |
| `knowledge-base/KB_07_API_Contracts.md` | Document MCP tool surface |

## KB files this stage updates

- `KB_16_A2A_MCP_Protocols.md`
- `KB_07_API_Contracts.md`
- `KB_01_System_Architecture.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
python -m backend.mcp_servers &
sleep 2
cd backend && pytest tests/mcp/ -v
# Verify MCP inspector if available
```

## Audit target

- Strict decrease; the bespoke direct-call paths from the coordinator drop as tools route through MCP.

## Role

- Primary: `backend-engineer`
- Secondary: `agentic-governance-engineer` (architectural review)

## Hand-off

- What is now true: internal agent → tool interactions are MCP-mediated; each tool has a typed schema.
- What the next stage (12) starts with: an MCP-ready runtime that can call into the memory layer once it's wired.
