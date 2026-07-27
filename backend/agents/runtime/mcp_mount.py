"""Stage 11.5 — mount the MCP tool servers into the LangGraph runtime.

A thin bridge over the **official `mcp` Python SDK stdio client**: spawn each server as a subprocess, list its
tools, and wrap each as a `langchain_core.tools.StructuredTool`. This is the same mechanism `langchain-mcp-adapters`
uses for stdio — but without that package's `langchain-core>=1.0` requirement, so it works on our frozen
langchain-core 0.3.28 runtime (research §18). When we migrate to langchain-core 1.0, swap this for
`langchain-mcp-adapters` directly.

`MCPToolMount` is the primary API: it opens **persistent** sessions (one subprocess per server, kept alive) so the
heavy ML import a tool triggers is paid once, not per call. `call_mcp_tool` is a per-call one-shot for light servers
/ scripts / transport tests. The production HTTP supervisor (`python -m mcp_servers`) is the long-lived service path.
"""
from __future__ import annotations

import sys
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp_servers import SERVER_REGISTRY, SERVER_TOOLS

# JSON-schema -> python type map for building a pydantic args model from a tool's inputSchema.
_JSON_PY = {"number": float, "integer": int, "string": str, "boolean": bool,
            "object": dict, "array": list}


def _server_params(module: str):
    import os

    from mcp import StdioServerParameters
    # Pass the FULL parent environment (not mcp's minimal default): on Windows the spawned subprocess needs the
    # inherited PATH (numpy/scipy/simpy DLLs) + DATABASE_URL etc., otherwise a lazy `import simulation` can hang.
    # Pin BLAS/OMP to a single thread: a multi-thread BLAS in the spawned subprocess can thrash/stall under the
    # stdio server's anyio worker-thread context on Windows.
    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    return StdioServerParameters(command=sys.executable, args=["-m", module], env=env)


def _model_from_schema(tool_name: str, schema: Optional[dict]):
    """Build a pydantic model class from a tool's JSON inputSchema (the simple types our tools use)."""
    from pydantic import create_model
    props = (schema or {}).get("properties", {}) or {}
    required = set((schema or {}).get("required", []) or [])
    fields: dict[str, tuple] = {}
    for fname, spec in props.items():
        jtype = spec.get("type")
        if isinstance(jtype, list):  # e.g. ["integer", "null"] for Optional
            jtype = next((t for t in jtype if t != "null"), "string")
        py = _JSON_PY.get(jtype, Any)
        if fname in required and "default" not in spec:
            fields[fname] = (py, ...)
        else:
            fields[fname] = (Optional[py], spec.get("default", None))
    if not fields:
        return create_model(f"{tool_name}_Args")
    return create_model(f"{tool_name}_Args", **fields)


def _extract_result(call_result: Any) -> Any:
    """Prefer the MCP structured result; fall back to parsing the first text block as JSON, else raw text."""
    structured = getattr(call_result, "structuredContent", None)
    if structured is not None:
        if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
            return structured["result"]  # FastMCP wraps non-dict returns under {"result": ...}
        return structured
    for block in getattr(call_result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            import json
            try:
                return json.loads(text)
            except Exception:  # noqa: BLE001
                return text
    return None


class MCPToolMount:
    """Async context manager holding persistent stdio sessions to the MCP servers.

        async with MCPToolMount(["kpi_query_server"]) as mount:
            tools = mount.tools                  # list[StructuredTool], bound to live sessions
            out = await mount.call("kpi_query_server", "queue_depth", {})
    """

    def __init__(self, server_names: Optional[list[str]] = None) -> None:
        self.server_names = server_names or list(SERVER_REGISTRY.keys())
        self._stack: Optional[AsyncExitStack] = None
        self._sessions: dict[str, Any] = {}
        self.tools: list = []

    async def __aenter__(self) -> "MCPToolMount":
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client
        self._stack = AsyncExitStack()
        for server in self.server_names:
            module, _port = SERVER_REGISTRY[server]
            read, write = await self._stack.enter_async_context(stdio_client(_server_params(module)))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[server] = session
            listed = await session.list_tools()
            for t in listed.tools:
                self.tools.append(self._bind_tool(server, t.name, t.description or "", t.inputSchema))
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._sessions.clear()

    async def call(self, server: str, tool: str, arguments: dict) -> Any:
        from observability.otel_init import traced_span
        with traced_span(f"mcp.tool.{server}.{tool}", **{"mcp.server": server, "mcp.tool": tool}):
            return _extract_result(await self._sessions[server].call_tool(tool, arguments))

    def _bind_tool(self, server: str, name: str, description: str, schema: Optional[dict]):
        from langchain_core.tools import StructuredTool
        session = self._sessions[server]

        async def _call(**kwargs: Any) -> Any:
            from observability.otel_init import traced_span
            with traced_span(f"mcp.tool.{server}.{name}", **{"mcp.server": server, "mcp.tool": name}):
                return _extract_result(await session.call_tool(name, kwargs))

        return StructuredTool(
            name=f"{server}.{name}",
            description=description or f"MCP tool {name} on {server}",
            args_schema=_model_from_schema(name, schema),
            coroutine=_call,
        )


async def call_mcp_tool(server: str, tool: str, arguments: dict) -> Any:
    """One-shot: open a stdio session to `server`, call `tool`, return the structured result, close.

    Spawns a fresh subprocess per call — fine for the light servers / scripts / transport tests; for the runtime use
    `MCPToolMount` (persistent) so a heavy-ML tool import is paid once, not per call.
    """
    module, _port = SERVER_REGISTRY[server]
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    async with stdio_client(_server_params(module)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return _extract_result(await session.call_tool(tool, arguments))


__all__ = ["MCPToolMount", "call_mcp_tool", "SERVER_REGISTRY", "SERVER_TOOLS"]
