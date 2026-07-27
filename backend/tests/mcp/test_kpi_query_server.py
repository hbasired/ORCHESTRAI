"""Conformance tests for the kpi_query MCP server (real stdio client)."""
import pytest

from tests.mcp.conftest import mcp_session, structured

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(120)]
SERVER = "kpi_query_server"

# A real plant snapshot (the shape sim_world.query_state returns), so KPI math is deterministic + offline.
_STATE = {
    "sim_time_seconds": 3600.0,
    "throughput_units_per_hour": 48.0,
    "amr_utilization": 0.7,
    "stages": [{"stage_id": 3, "name": "machining", "queue_depth": 4, "units_produced": 50,
                "units_defective": 2, "time_broken_seconds": 120.0, "time_maintenance_seconds": 60.0}],
    "robots": [{"id": 0, "utilization": 0.7}],
}


async def test_manifest_matches_documented(manifest):
    async with mcp_session(SERVER) as s:
        tools = (await s.list_tools()).tools
    assert {t.name for t in tools} == set(manifest[SERVER])


async def test_oee_is_real_availability_performance_quality():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("oee", {"state": _STATE, "stage_id": 3}))
    assert out["available"] is True
    row = out["per_stage"][0]
    # quality = (50-2)/50 = 0.96; availability = (3600-180)/3600 = 0.95; all in [0,1]; product is the OEE.
    assert abs(row["quality"] - 0.96) < 1e-6
    assert abs(row["availability"] - (3420.0 / 3600.0)) < 1e-6
    assert 0.0 <= row["oee"] <= 1.0
    assert abs(row["oee"] - row["availability"] * row["performance"] * row["quality"]) < 1e-3


async def test_queue_depth_and_utilization_from_state():
    async with mcp_session(SERVER) as s:
        qd = structured(await s.call_tool("queue_depth", {"state": _STATE}))
        ut = structured(await s.call_tool("utilization", {"state": _STATE}))
    assert qd["available"] and qd["total_wip"] == 4
    assert ut["available"] and abs(ut["fleet_utilization"] - 0.7) < 1e-6


async def test_oee_zero_elapsed_is_honest_unavailable():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("oee", {"state": {"sim_time_seconds": 0.0, "stages": []}}))
    assert out["available"] is False and out["reason"]
