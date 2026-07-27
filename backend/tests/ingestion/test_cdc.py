"""Stage 13 — CDC ingestion: the row-diff→inject converter (no infra) + a live outbox→NOTIFY→drain→inject roundtrip."""
import os
import uuid

import pytest

from ingestion.cdc_listener import change_to_inject

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))
_DSN = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


# ---- pure converter (no infra) ---------------------------------------------

def test_incidents_change_becomes_inject():
    req = change_to_inject("incidents", {"type": "machine_crack", "target_id": 3,
                                         "details": {"eta_seconds": 60}, "severity": "warning"})
    assert req is not None
    assert req.type == "machine_crack" and req.target_id == 3
    assert req.details["source"] == "cdc:incidents" and req.details["eta_seconds"] == 60


def test_stage_trouble_status_becomes_machine_crack():
    req = change_to_inject("stages", {"stage_id": 5, "name": "paint", "old_status": "nominal", "new_status": "broken"})
    assert req is not None and req.type == "machine_crack" and req.target_id == 5
    assert req.severity == "critical" and req.details["source"] == "cdc:stages.status"


def test_benign_stage_status_is_not_actionable():
    assert change_to_inject("stages", {"stage_id": 5, "new_status": "nominal"}) is None


def test_unknown_table_is_none():
    assert change_to_inject("inventory", {"x": 1}) is None


# ---- live end-to-end (outbox → NOTIFY → drain → inject) --------------------

@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: live CDC roundtrip not exercisable")
@pytest.mark.timeout(60)
async def test_db_insert_drains_into_simworld():
    import asyncio
    import psycopg
    from simulation.sim_world import SimWorld
    from api.simulation_routes import set_sim_world
    from ingestion.cdc_listener import CDCListener

    sw = SimWorld(seed=20260524)  # worker thread not needed: inject() queues; we assert the listener injected
    set_sim_world(sw)
    listener = CDCListener()
    assert await listener.start() is True
    try:
        # Snapshot AFTER the startup drain so we assert an INCREASE caused by THIS insert's NOTIFY (not backlog).
        baseline = listener.injected
        iid = str(uuid.uuid4())
        with psycopg.connect(_DSN, autocommit=True) as wc, wc.cursor() as cur:
            cur.execute("INSERT INTO incidents(incident_id,started_at,type,target_id,details,severity) "
                        "VALUES (%s, now(), 'machine_crack', 3, '{\"eta_seconds\":60}'::jsonb, 'warning')", (iid,))
        for _ in range(50):  # up to ~5s for notify→drain
            if listener.injected > baseline:
                break
            await asyncio.sleep(0.1)
        assert listener.injected > baseline, "the NOTIFY→drain path did not inject the new incident"
    finally:
        await listener.stop()
        set_sim_world(None)


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: durability drain-on-connect not exercisable")
@pytest.mark.timeout(60)
async def test_drain_on_connect_catches_offline_writes():
    """A row written while NO listener is running must be picked up by the startup drain (durability)."""
    import psycopg
    from simulation.sim_world import SimWorld
    from api.simulation_routes import set_sim_world
    from ingestion.cdc_listener import CDCListener

    iid = str(uuid.uuid4())
    with psycopg.connect(_DSN, autocommit=True) as wc, wc.cursor() as cur:  # no listener yet
        cur.execute("INSERT INTO incidents(incident_id,started_at,type,target_id,details,severity) "
                    "VALUES (%s, now(), 'robot_down', 1, '{}'::jsonb, 'warning')", (iid,))
    sw = SimWorld(seed=20260524)
    set_sim_world(sw)
    listener = CDCListener()
    assert await listener.start() is True  # start() drains the backlog
    try:
        assert listener.injected >= 1, "startup drain did not catch the offline-written row"
    finally:
        await listener.stop()
        set_sim_world(None)
