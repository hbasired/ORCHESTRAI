"""Conformance tests for the policy_query MCP server (real stdio client)."""
import pytest

from tests.mcp.conftest import mcp_session, structured

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(120)]
SERVER = "policy_query_server"

_TELE = {"stage_id": 3, "air_temp_k": 300.0, "process_temp_k": 312.0, "rot_speed_rpm": 1300.0,
         "torque_nm": 60.0, "tool_wear_min": 210.0}


async def test_manifest_matches_documented(manifest):
    async with mcp_session(SERVER) as s:
        tools = (await s.list_tools()).tools
    assert {t.name for t in tools} == set(manifest[SERVER])


async def test_recommend_action_returns_real_decision():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("recommend_action", {"telemetry": _TELE}))
    assert isinstance(out, dict) and "available" in out
    if out["available"]:
        assert out["kind"] in ("monitor", "preventive_maintenance", "wait_external")
        assert out["stage_id"] == 3
        assert "diagnosis" in out
    else:
        assert out["reason"]


async def test_recommend_action_missing_features_is_honest():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("recommend_action", {"telemetry": {"stage_id": 3}}))
    assert out["available"] is False and out.get("input_error") is True


async def test_explain_action_shape():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("explain_action", {"telemetry": _TELE, "top_k": 3}))
    assert isinstance(out, dict) and "available" in out
    if out["available"]:
        assert isinstance(out["top_drivers"], list) and out["method"]
    else:
        assert out["reason"]
