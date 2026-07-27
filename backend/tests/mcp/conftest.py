"""Shared fixtures for the Stage 11.5 MCP conformance tests.

These are REAL integration tests: each opens a stdio session to an actual MCP server subprocess (the official `mcp`
client driving our FastMCP servers) and asserts the documented manifest + schemas + a real tool call. No mocks.
"""
from __future__ import annotations

import contextlib
import os

import pytest

# Keep the SimWorld warm-up tiny + BLAS single-threaded so the sim/kpi servers respond fast in CI.
os.environ.setdefault("MCP_SIM_WARM_SECONDS", "120")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


@contextlib.asynccontextmanager
async def mcp_session(server_name: str):
    """Open a stdio MCP ClientSession to `server_name` (spawns the server subprocess). Yields an initialized session."""
    from agents.runtime.mcp_mount import _server_params, SERVER_REGISTRY
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    module, _port = SERVER_REGISTRY[server_name]
    async with stdio_client(_server_params(module)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def structured(call_result):
    """Extract a tool's structured dict result from a CallToolResult (mirrors mcp_mount._extract_result)."""
    from agents.runtime.mcp_mount import _extract_result
    return _extract_result(call_result)


@pytest.fixture
def manifest():
    from mcp_servers import SERVER_TOOLS
    return SERVER_TOOLS
