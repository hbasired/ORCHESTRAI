"""Stage 12 — Neo4j ISA-95 schema migrator: idempotent constraints + hierarchy upsert/query."""
import os
import uuid

import pytest

def _neo4j_reachable() -> bool:
    """True only if Neo4j is configured AND actually accepting connections — so a transient down-Neo4j SKIPS
    (not fails) the suite (the infra-gated-test robustness lesson). Quick-probe with a short timeout."""
    if not os.environ.get("NEO4J_PASSWORD"):
        return False
    try:
        from neo4j import GraphDatabase
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        d = GraphDatabase.driver(uri, auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
                                 connection_timeout=3.0)
        d.verify_connectivity()
        d.close()
        return True
    except Exception:
        return False


_HAS_NEO4J = _neo4j_reachable()
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.timeout(60),
    pytest.mark.skipif(not _HAS_NEO4J, reason="Neo4j not configured/reachable: ISA-95 tests not exercisable"),
]


async def test_run_migrations_is_idempotent():
    from memory.graph_isa95 import run_migrations, ISA95_CLASSES
    r1 = await run_migrations()
    r2 = await run_migrations()  # second run must not error (CREATE CONSTRAINT IF NOT EXISTS)
    assert r1["available"] is True and r2["available"] is True
    assert len(r1["constraints_ensured"]) == len(ISA95_CLASSES)


async def test_upsert_node_and_hierarchy_query():
    from memory.graph_isa95 import run_migrations, upsert_node, query_descendants
    await run_migrations()
    sid, aid = f"site-{uuid.uuid4()}", f"area-{uuid.uuid4()}"
    await upsert_node("Site", sid, "Plant Test")
    await upsert_node("Area", aid, "Area Test", parent_id=sid, parent_class="Site")
    desc = await query_descendants(sid)
    assert any(d["id"] == aid for d in desc)  # the area is a descendant of the site


async def test_upsert_mirrors_to_postgres():
    if not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")):
        pytest.skip("no DATABASE_URL for the relational mirror check")
    import psycopg
    from memory.graph_isa95 import run_migrations, upsert_node
    await run_migrations()
    wid = f"wu-{uuid.uuid4()}"
    await upsert_node("WorkUnit", wid, "Press 1", attributes={"sil": 2})
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT isa95_class, name FROM isa95_metadata WHERE id=%s", (wid,))
        row = cur.fetchone()
    assert row == ("WorkUnit", "Press 1")  # the Neo4j upsert mirrored into the PG table
