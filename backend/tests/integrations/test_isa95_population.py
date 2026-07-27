"""Stage 15 — ISA-95 graph populated from inbound OPC UA / Sparkplug B events (skipif Neo4j unreachable)."""
import os
import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(60)]


def _neo4j_reachable() -> bool:
    if not os.environ.get("NEO4J_PASSWORD"):
        return False
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                                 auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
                                 connection_timeout=3.0)
        d.verify_connectivity(); d.close()
        return True
    except Exception:
        return False


_HAS_NEO4J = _neo4j_reachable()
skip = pytest.mark.skipif(not _HAS_NEO4J, reason="Neo4j not configured/reachable")


@skip
async def test_populate_from_sparkplug_event_creates_isa95_equipment():
    from memory.graph_isa95 import populate_from_ot_event, query_descendants, run_migrations
    await run_migrations()
    wc_id = f"wc-{uuid.uuid4().hex[:8]}"
    eq_id = f"eq-{uuid.uuid4().hex[:8]}"
    res = await populate_from_ot_event("sparkplug", eq_id, "Robot1",
                                       {"OEE": 0.85, "Status": "running"},
                                       work_center_id=wc_id, work_center_name="Line1")
    assert res["available"] is True and res["id"] == eq_id and res["class"] == "Equipment"
    # the equipment is now a descendant of the work center in the graph
    desc = await query_descendants(wc_id)
    assert any(d["id"] == eq_id for d in desc)


@skip
async def test_populate_from_opcua_event_idempotent():
    from memory.graph_isa95 import populate_from_ot_event
    eq_id = f"eq-{uuid.uuid4().hex[:8]}"
    r1 = await populate_from_ot_event("opcua", eq_id, "Stage0_Intake", {"OEE": 0.5})
    r2 = await populate_from_ot_event("opcua", eq_id, "Stage0_Intake", {"OEE": 0.6})  # re-event → no dup
    assert r1["id"] == r2["id"] == eq_id


async def test_invalid_source_rejected():
    from memory.graph_isa95 import populate_from_ot_event
    with pytest.raises(ValueError):
        await populate_from_ot_event("modbus", "x", "y", {})  # only opcua/sparkplug allowed
