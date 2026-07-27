"""Conformance tests for the sim_world MCP server (real stdio client + real SimPy engine)."""
import pytest

from tests.mcp.conftest import mcp_session, structured

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(120)]
SERVER = "sim_world_server"


async def test_manifest_matches_documented(manifest):
    async with mcp_session(SERVER) as s:
        tools = (await s.list_tools()).tools
    assert {t.name for t in tools} == set(manifest[SERVER])


async def test_query_state_returns_real_snapshot():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("query_state", {"scope": "summary"}))
    assert out["available"] is True
    assert out["sim_time_seconds"] > 0  # the engine was actually advanced
    assert "throughput_units_per_hour" in out


async def test_inject_event_and_subscribe_roundtrip():
    async with mcp_session(SERVER) as s:
        inj = structured(await s.call_tool("inject_event", {
            "event_type": "machine_crack", "target_id": 3, "details": {"eta_seconds": 60}}))
        assert inj["available"] is True and inj["type"] == "machine_crack"
        sub = structured(await s.call_tool("subscribe_events", {}))
    assert sub["available"] is True
    assert any(e.get("type") == "machine_crack" for e in sub["events"])  # the injected event is observable


async def test_unknown_event_type_is_honest():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("inject_event", {"event_type": "not_a_real_event"}))
    assert out["available"] is False and out.get("input_error") is True
