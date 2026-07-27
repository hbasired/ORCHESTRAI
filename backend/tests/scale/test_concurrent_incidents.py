"""Stage 25 (G-066 foothold) — pilot-scale concurrent-incident load test + exactly-once verification.

Infra-free legs test the sharding math + local duplicate suppression. The DB-gated leg runs REAL concurrent
incidents through the live LangGraph runtime (PG@5544 checkpointer + real models) and asserts:
no lost incidents, no duplicate processing, and honest throughput numbers printed (not asserted against a
made-up SLA — the measurement IS the deliverable; a target SLA comes with a real pilot)."""
from __future__ import annotations

import os
import threading

import pytest

from agents.runtime.shard_router import IncidentLock, run_incident_guarded, shard_of


# ---------------------------------------------------------------------------
# Sharding math (pure)
# ---------------------------------------------------------------------------

def test_shard_is_deterministic_and_stable():
    assert shard_of("incident-abc", 8) == shard_of("incident-abc", 8)


def test_shards_are_spread():
    slots = {shard_of(f"incident-{i}", 8) for i in range(200)}
    assert len(slots) == 8  # 200 ids must reach every one of 8 slots


def test_zero_shards_rejected():
    with pytest.raises(ValueError):
        shard_of("x", 0)


def test_incident_without_id_rejected():
    with pytest.raises(ValueError):
        run_incident_guarded({"type": "anomaly"})


# ---------------------------------------------------------------------------
# Exactly-once guard — in-process fallback (no DB)
# ---------------------------------------------------------------------------

def test_local_lock_suppresses_concurrent_duplicate(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    inner: list[bool] = []
    with IncidentLock("dup-1") as outer:
        assert outer.acquired
        def contender():
            with IncidentLock("dup-1") as lk:
                inner.append(lk.acquired)
        t = threading.Thread(target=contender)
        t.start(); t.join()
    assert inner == [False]  # the concurrent claim was refused
    with IncidentLock("dup-1") as again:
        assert again.acquired  # and released after exit


# ---------------------------------------------------------------------------
# DB-gated: advisory lock + REAL concurrent load through the live runtime
# ---------------------------------------------------------------------------

requires_db = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")),
    reason="no DATABASE_URL/POSTGRES_URL — live load test needs the Docker stack",
)


@requires_db
def test_advisory_lock_is_cross_connection():
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        probe = psycopg.connect(dsn, connect_timeout=5); probe.close()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    with IncidentLock("adv-1") as first:
        assert first.acquired
        with IncidentLock("adv-1") as second:  # separate PG connection
            assert not second.acquired
    with IncidentLock("adv-1") as third:
        assert third.acquired  # released


def _real_incident(i: int) -> dict:
    """Realistic incident (the shape the Stage-8 predictor expects — mirrors test_runtime_determinism)."""
    telemetry = {"stage_id": 3, "type_": "M", "air_temp_k": 301.0 + i * 0.1, "process_temp_k": 312.0,
                 "rot_speed_rpm": 1300.0 + i * 5, "torque_nm": 68.0, "tool_wear_min": 240.0,
                 "queue_depth": 5, "status": "degraded", "crack_proximity": 0.6}
    plant = {"available_crew": 1, "throughput_floor_frac": 0.5, "stages": {
        1: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
        3: {"status": "degraded", "at_risk": True, "crack_proximity": 0.6},
        5: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0}}}
    return {"id": f"load-{i}", "type": "machine_crack", "target_id": 3, "capacity": 10,
            "telemetry": telemetry, "recent_incidents": [], "plant": plant}


@requires_db
@pytest.mark.timeout(600)
def test_pilot_scale_concurrent_incidents_no_loss_no_dup():
    """The G-066 load test: 8 distinct + 4 duplicate incidents, concurrently, against the REAL stack.

    Duplicate semantics (finding of the FIRST run of this test, 2026-07-02): a duplicate is suppressed either
    CONCURRENTLY (advisory lock) or SEQUENTIALLY (at-most-once processed ledger) — both are honest named
    suppressions; what is forbidden is a silent second execution."""
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn, conn.cursor() as cur:
            # Clean slate for THIS test's ids (the ledger is persistent by design).
            cur.execute("CREATE TABLE IF NOT EXISTS incident_processed (incident_id text PRIMARY KEY, processed_at timestamptz NOT NULL DEFAULT now())")
            cur.execute("DELETE FROM incident_processed WHERE incident_id LIKE 'load-%'")
            conn.commit()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    from agents.runtime.shard_router import run_many

    distinct = [_real_incident(i) for i in range(8)]
    dupes = [dict(distinct[0]) for _ in range(4)]  # same id 4x
    out = run_many(distinct + dupes, max_workers=6, sil_level=0)

    assert out["n"] == 12
    # No loss, no double-run: every DISTINCT incident processed exactly once...
    assert out["processed"] == 8, f"lost or duplicated work: { {r['incident_id']: r['status'] for r in out['results']} }"
    # ...and every duplicate honestly suppressed (concurrently or via the at-most-once ledger).
    assert out["suppressed"] == 4
    processed_ids = sorted(r["incident_id"] for r in out["results"] if r["status"] == "processed")
    assert processed_ids == sorted(f"load-{i}" for i in range(8))
    # Every processed run traversed the REAL loop (trace present, full node path).
    for r in out["results"]:
        if r["status"] == "processed":
            assert r["trace"], f"no trace for {r['incident_id']}"
            nodes = [t.get("node") for t in r["trace"]]
            assert "orient" in nodes and "log" in nodes, f"partial trajectory for {r['incident_id']}: {nodes}"
    # Honest measurement — printed, not asserted against an invented SLA.
    print(f"\nG-066 foothold: processed={out['processed']} suppressed={out['suppressed']} "
          f"workers={out['max_workers']} elapsed={out['elapsed_s']}s "
          f"throughput={out['throughput_per_s']}/s backend={out['backend']}")
