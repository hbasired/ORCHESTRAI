"""Conformance tests for the model_inference MCP server (real stdio client)."""
import pytest

from tests.mcp.conftest import mcp_session, structured

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(120)]
SERVER = "model_inference_server"


async def test_manifest_matches_documented(manifest):
    async with mcp_session(SERVER) as s:
        tools = (await s.list_tools()).tools
    assert {t.name for t in tools} == set(manifest[SERVER])


async def test_input_schemas_have_expected_fields():
    async with mcp_session(SERVER) as s:
        tools = {t.name: t for t in (await s.list_tools()).tools}
    pf = tools["predict_failure"].inputSchema["properties"]
    for k in ("air_temp_k", "process_temp_k", "rot_speed_rpm", "torque_nm", "tool_wear_min", "type_"):
        assert k in pf, f"predict_failure missing input {k}"
    assert "history" in tools["predict_demand"].inputSchema["properties"]
    assert "image_path" in tools["classify_defect"].inputSchema["properties"]


async def test_predict_failure_returns_real_or_honest_unavailable():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("predict_failure", {
            "air_temp_k": 300.0, "process_temp_k": 312.0, "rot_speed_rpm": 1300.0,
            "torque_nm": 60.0, "tool_wear_min": 210.0, "type_": "M"}))
    assert isinstance(out, dict) and "available" in out
    if out["available"]:
        assert 0.0 <= out["p_fail"] <= 1.0
        assert isinstance(out["at_risk"], bool)
        assert out["arch"]  # real model arch label, not fabricated
    else:
        assert out["reason"]  # honest reason, never a fake number


async def test_classify_defect_missing_image_is_honest():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("classify_defect", {"image_path": "/no/such/file.png"}))
    assert out["available"] is False and out.get("input_error") is True
