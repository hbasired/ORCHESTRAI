"""Stage 12 — Neo4j ISA-95 Part 2 schema migrator + equipment-hierarchy access (KB_14 §"Neo4j ISA-95 schema").

The equipment hierarchy lives in Neo4j (Cypher beats recursive SQL for hierarchy queries). `run_migrations()` is
**idempotent** — `CREATE CONSTRAINT IF NOT EXISTS` per ISA-95 node label — so it is safe to run on every boot and
under concurrent agent startup. `upsert_node()` MERGEs a node (+ optional parent edge) into the graph AND mirrors it
into the `isa95_metadata` Postgres table (migration `0004`) for SQL joins. Honest: if Neo4j is unreachable the
functions raise `Neo4jUnavailable` — they never pretend the graph was migrated (Rule 1a).
"""
from __future__ import annotations

import os
from typing import Any, Optional

# ISA-95 Part 2 object classes (node labels) + the parent relationship used for the hierarchy.
ISA95_CLASSES = (
    "Enterprise", "Site", "Area", "WorkCenter", "WorkUnit",
    "EquipmentClass", "Equipment", "MaterialClass", "MaterialLot", "MaterialSublot",
    "ProcessSegment", "OperationsDefinition", "OperationsRequest", "OperationsResponse",
    "Personnel", "PersonnelClass",
)
# Hierarchy edge by level (KB_14 relationships). Generic CONTAINS used for the equipment tree.
_PARENT_REL = {
    "Site": "HAS_SITE", "Area": "HAS_AREA", "WorkCenter": "HAS_WORK_CENTER", "WorkUnit": "HAS_WORK_UNIT",
}


class Neo4jUnavailable(RuntimeError):
    """Raised when Neo4j is not reachable — never swallowed, never faked."""


def _settings() -> tuple[str, str, str]:
    try:
        from config import settings
        uri = getattr(settings, "neo4j_uri", None) or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = getattr(settings, "neo4j_user", None) or os.environ.get("NEO4J_USER", "neo4j")
        pw = getattr(settings, "neo4j_password", None) or os.environ.get("NEO4J_PASSWORD", "")
    except Exception:  # noqa: BLE001
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        pw = os.environ.get("NEO4J_PASSWORD", "")
    return uri, user, str(pw)


def _driver():
    uri, user, pw = _settings()
    try:
        from neo4j import AsyncGraphDatabase
        return AsyncGraphDatabase.driver(uri, auth=(user, pw))
    except Exception as e:  # noqa: BLE001
        raise Neo4jUnavailable(f"cannot create Neo4j driver for {uri}: {e}") from e


async def run_migrations() -> dict[str, Any]:
    """Idempotently ensure a uniqueness constraint on `id` for every ISA-95 label. Returns a summary dict."""
    driver = _driver()
    created = []
    try:
        async with driver.session() as session:
            try:
                await session.run("RETURN 1")  # connectivity probe
            except Exception as e:  # noqa: BLE001
                raise Neo4jUnavailable(f"Neo4j not reachable: {e}") from e
            for label in ISA95_CLASSES:
                cname = f"isa95_{label.lower()}_id"
                await session.run(
                    f"CREATE CONSTRAINT {cname} IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE")
                created.append(cname)
        return {"available": True, "constraints_ensured": created, "labels": list(ISA95_CLASSES)}
    finally:
        await driver.close()


async def upsert_node(isa95_class: str, node_id: str, name: str, *, parent_id: Optional[str] = None,
                      parent_class: Optional[str] = None, attributes: Optional[dict] = None,
                      mirror_to_pg: bool = True) -> dict[str, Any]:
    """MERGE a node (+ optional parent edge) into Neo4j and mirror it into `isa95_metadata` (Postgres)."""
    if isa95_class not in ISA95_CLASSES:
        raise ValueError(f"unknown ISA-95 class {isa95_class!r}")
    driver = _driver()
    attrs = attributes or {}
    try:
        async with driver.session() as session:
            await session.run(
                f"MERGE (n:{isa95_class} {{id: $id}}) "
                f"SET n.name = $name, n.attributes = $attrs",
                id=node_id, name=name, attrs=__import__("json").dumps(attrs))
            if parent_id and parent_class:
                rel = _PARENT_REL.get(isa95_class, "CONTAINS")
                await session.run(
                    f"MATCH (p:{parent_class} {{id: $pid}}), (c:{isa95_class} {{id: $cid}}) "
                    f"MERGE (p)-[:{rel}]->(c)",
                    pid=parent_id, cid=node_id)
    finally:
        await driver.close()
    if mirror_to_pg:
        _mirror_pg(isa95_class, node_id, name, parent_id, attrs)
    return {"available": True, "id": node_id, "class": isa95_class}


def _mirror_pg(isa95_class: str, node_id: str, name: str, parent_id: Optional[str], attrs: dict) -> None:
    """Upsert the relational mirror row (best-effort; the graph is source of truth)."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not dsn:
        return
    import json

    import psycopg
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO isa95_metadata (id, isa95_class, name, parent_id, attributes, updated_at)
               VALUES (%s, %s, %s, %s, %s::jsonb, now())
               ON CONFLICT (id) DO UPDATE SET isa95_class=EXCLUDED.isa95_class, name=EXCLUDED.name,
                 parent_id=EXCLUDED.parent_id, attributes=EXCLUDED.attributes, updated_at=now()""",
            (node_id, isa95_class, name, parent_id, json.dumps(attrs)),
        )


async def query_descendants(node_id: str) -> list[dict]:
    """Return all descendants of a node in the hierarchy (Cypher variable-length path)."""
    driver = _driver()
    try:
        async with driver.session() as session:
            res = await session.run(
                "MATCH (n {id: $id})-[*1..]->(d) RETURN labels(d)[0] AS class, d.id AS id, d.name AS name",
                id=node_id)
            return [{"class": r["class"], "id": r["id"], "name": r["name"]} async for r in res]
    finally:
        await driver.close()


async def populate_from_ot_event(source: str, equipment_id: str, name: str, telemetry: dict[str, Any], *,
                                 work_center_id: Optional[str] = None, work_center_name: Optional[str] = None,
                                 equipment_class: str = "Equipment") -> dict[str, Any]:
    """Map an inbound **OPC UA** datachange or **Sparkplug B** DBIRTH/DDATA into the ISA-95 graph (Stage 15).

    Idempotent: MERGEs the (optional) parent WorkCenter, then the Equipment/WorkUnit node, storing the telemetry +
    provenance (`source`, `last_seen`) as node attributes. Honest: raises `Neo4jUnavailable` if the graph is down
    (never pretends the event was recorded). `source` ∈ {"opcua","sparkplug"}.
    """
    if source not in ("opcua", "sparkplug"):
        raise ValueError(f"source must be 'opcua' or 'sparkplug', got {source!r}")
    import time as _time
    if work_center_id and work_center_name:
        await upsert_node("WorkCenter", work_center_id, work_center_name)
    attrs = {**telemetry, "source": source, "last_seen": int(_time.time() * 1000)}
    return await upsert_node(equipment_class, equipment_id, name,
                             parent_id=work_center_id, parent_class="WorkCenter" if work_center_id else None,
                             attributes=attrs)


__all__ = ["run_migrations", "upsert_node", "query_descendants", "populate_from_ot_event",
           "Neo4jUnavailable", "ISA95_CLASSES"]
