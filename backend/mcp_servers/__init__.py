"""Stage 11.5 — MCP server suite.

Five Model-Context-Protocol tool servers (official `mcp` Python SDK, bundled FastMCP) that expose the REAL
Stage-4-10 models + the simulation + KPI + decision-log surfaces as typed MCP tools. The Stage-11 LangGraph runtime
mounts them via `backend/agents/runtime/mcp_mount.py` (a thin in-house bridge over the official `mcp` stdio client —
`langchain-mcp-adapters` is deferred because it requires langchain-core>=1.0, a major migration off our frozen
0.3.28 runtime; research §18).

Honesty (Hard Rule 1 / 1a): every tool wraps a real model/service with the same honest-unavailable contract as the
runtime nodes — a missing model returns ``{"available": false, "reason": ...}`` (the truth), never a fabricated
result. No `random.*`, no hardcoded result literals.

Transports: **stdio** for CI tests + the runtime mount (the client spawns the server as a subprocess); the
`__main__` supervisor runs them as long-lived **streamable-HTTP** services with a watchdog.

Server inventory (matches KB_16):

| name                   | tools                                                  |
|------------------------|--------------------------------------------------------|
| sim_world_server       | inject_event, query_state, subscribe_events            |
| kpi_query_server       | throughput, oee, utilization, queue_depth              |
| decision_log_server    | append_decision, query_decisions                       |
| model_inference_server | predict_demand, predict_failure, classify_defect       |
| policy_query_server    | recommend_action, explain_action                       |
"""
from __future__ import annotations

# name -> (import path of the module exposing `mcp`, default streamable-HTTP port for the supervisor)
SERVER_REGISTRY: dict[str, tuple[str, int]] = {
    "sim_world_server": ("mcp_servers.sim_world_server", 9101),
    "kpi_query_server": ("mcp_servers.kpi_query_server", 9102),
    "decision_log_server": ("mcp_servers.decision_log_server", 9103),
    "model_inference_server": ("mcp_servers.model_inference_server", 9104),
    "policy_query_server": ("mcp_servers.policy_query_server", 9105),
}

# Documented tool manifest (the schema tests assert tools/list matches this exactly).
SERVER_TOOLS: dict[str, tuple[str, ...]] = {
    "sim_world_server": ("inject_event", "query_state", "subscribe_events"),
    "kpi_query_server": ("throughput", "oee", "utilization", "queue_depth"),
    "decision_log_server": ("append_decision", "query_decisions"),
    "model_inference_server": ("predict_demand", "predict_failure", "classify_defect"),
    "policy_query_server": ("recommend_action", "explain_action"),
}

__all__ = ["SERVER_REGISTRY", "SERVER_TOOLS"]
