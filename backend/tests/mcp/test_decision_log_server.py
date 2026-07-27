"""Conformance tests for the decision_log MCP server (real stdio client; real Postgres when DATABASE_URL is set)."""
import os
import uuid

import pytest

from tests.mcp.conftest import mcp_session, structured

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(120)]
SERVER = "decision_log_server"
_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))


async def test_manifest_matches_documented(manifest):
    async with mcp_session(SERVER) as s:
        tools = (await s.list_tools()).tools
    assert {t.name for t in tools} == set(manifest[SERVER])


async def test_append_validates_input_without_db():
    async with mcp_session(SERVER) as s:
        # missing required field
        out = structured(await s.call_tool("append_decision", {"decision": {"reasoning": "x", "confidence": 0.5}}))
        assert out["available"] is False and out.get("input_error") is True
        # out-of-range confidence
        out2 = structured(await s.call_tool("append_decision", {
            "decision": {"decision_type": "t", "reasoning": "x", "confidence": 1.7}}))
    assert out2["available"] is False and out2.get("input_error") is True


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: decision-log Postgres round-trip not exercisable")
async def test_append_then_query_roundtrip_real_db():
    did = f"test-{uuid.uuid4()}"
    async with mcp_session(SERVER) as s:
        ap = structured(await s.call_tool("append_decision", {"decision": {
            "decision_id": did, "decision_type": "preventive_maintenance",
            "reasoning": "mcp conformance roundtrip", "confidence": 0.81, "actions": [{"stage": 3}]}}))
        assert ap["available"] is True and ap["persisted"] is True and ap["decision_id"] == did
        q = structured(await s.call_tool("query_decisions", {"decision_type": "preventive_maintenance", "limit": 50}))
    assert q["available"] is True
    assert any(d["decision_id"] == did for d in q["decisions"])  # the row we wrote is readable back


@pytest.mark.skipif(_HAS_DB, reason="DATABASE_URL set: unavailable path not exercisable")
async def test_query_honest_unavailable_without_db():
    async with mcp_session(SERVER) as s:
        out = structured(await s.call_tool("query_decisions", {}))
    assert out["available"] is False and "Postgres" in out["reason"]
