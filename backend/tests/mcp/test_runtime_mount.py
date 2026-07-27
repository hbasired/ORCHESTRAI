"""Stage 11.5 — the LangGraph runtime mounts the MCP servers (real stdio, persistent sessions)."""
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(180)]


async def test_mount_loads_all_documented_tools():
    from agents.runtime.mcp_mount import MCPToolMount
    from mcp_servers import SERVER_TOOLS
    expected = {f"{srv}.{tool}" for srv, tools in SERVER_TOOLS.items() for tool in tools}
    async with MCPToolMount() as mount:
        got = {t.name for t in mount.tools}
    assert got == expected  # all 14 tools across the 5 servers, namespaced server.tool


async def test_mount_invokes_a_real_model_tool():
    from agents.runtime.mcp_mount import MCPToolMount
    async with MCPToolMount(["model_inference_server"]) as mount:
        tool = next(t for t in mount.tools if t.name == "model_inference_server.predict_failure")
        out = await tool.ainvoke({
            "air_temp_k": 300.0, "process_temp_k": 310.0, "rot_speed_rpm": 1500.0,
            "torque_nm": 40.0, "tool_wear_min": 100.0, "type_": "M"})
    assert isinstance(out, dict) and "available" in out
    if out["available"]:
        assert 0.0 <= out["p_fail"] <= 1.0  # real prediction routed through MCP
    else:
        assert out["reason"]


async def test_mount_call_helper_and_clean_close():
    from agents.runtime.mcp_mount import MCPToolMount
    async with MCPToolMount(["kpi_query_server"]) as mount:
        out = await mount.call("kpi_query_server", "oee", {"state": {
            "sim_time_seconds": 3600.0, "stages": [{"stage_id": 0, "name": "intake", "queue_depth": 0,
            "units_produced": 40, "units_defective": 1, "time_broken_seconds": 0.0,
            "time_maintenance_seconds": 0.0}], "robots": []}})
    assert out["available"] is True and 0.0 <= out["plant_oee"] <= 1.0
