"""Stage 39 (G-045 + G-051) — slice decision-log persistence + a NON-relaxed, genuinely-rejecting Stage-6 verifier.

G-051: `_build_plant_state` now supplies BINDING constraints (limited crew, 60% throughput floor, SIL redundancy cap),
so the plan verifier can actually REJECT an unsafe slice plan — not just attach provenance. Tests prove both a genuine
REJECT and no false-reject on the normal safe case.
G-045: `_persist_decision_log` writes each live decision to Postgres `decision_logs` (Art-12) with input/output hashes;
honest no-op (None) without a DB, never a fabricated id.
"""
import os
import uuid

import pytest

from services.plan_verifier import PlannedAction, PREVENTIVE_MAINTENANCE, verify
from services.slice_runner import (
    _MAINT_CREW_TOTAL,
    _THROUGHPUT_FLOOR_FRAC,
    _build_plant_state,
    _persist_decision_log,
)

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))
_DSN = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


# ---- fake world (minimal shape _build_plant_state needs) -------------------

class _Cfg:
    def __init__(self, sid): self.stage_id = sid


class _Stage:
    def __init__(self, sid, status="nominal", prox=0.0):
        self.cfg = _Cfg(sid); self.status = status; self._prox = prox
    def crack_proximity(self): return self._prox


class _World:
    def __init__(self, stages): self.stages = {s.cfg.stage_id: s for s in stages}


# ---- G-051: the plant state now BINDS ---------------------------------------

def test_plant_state_is_not_relaxed():
    world = _World([_Stage(i, "nominal") for i in range(10)])
    ps = _build_plant_state(world)
    assert ps is not None
    assert ps.throughput_floor_frac == _THROUGHPUT_FLOOR_FRAC and ps.throughput_floor_frac > 0.0
    assert ps.max_concurrent_critical_offline == 1        # SIL cap, not n
    assert ps.available_crew == _MAINT_CREW_TOTAL         # no busy crew yet


def test_available_crew_reduced_by_busy_maintenance():
    # two stages already in maintenance → crew is exhausted (2 total − 2 busy = 0)
    world = _World([_Stage(0, "maintenance"), _Stage(1, "maintenance")] + [_Stage(i, "nominal") for i in range(2, 8)])
    ps = _build_plant_state(world)
    assert ps.available_crew == 0


def test_verifier_rejects_when_throughput_floor_breached():
    # 6 of 10 stages already offline → only 4 online (0.4); taking another offline (0.3) breaches the 0.6 floor
    stages = [_Stage(i, "broken") for i in range(6)] + [_Stage(i, "nominal") for i in range(6, 10)]
    world = _World(stages)
    ps = _build_plant_state(world)
    result = verify([PlannedAction(PREVENTIVE_MAINTENANCE, 6, "risk")], ps)
    assert result.approved is False
    assert any(v["constraint"] == "throughput_floor" for v in result.to_dict()["violations"])


def test_verifier_rejects_second_critical_offline():
    # one CRITICAL machine already down; planning maintenance on a second CRITICAL breaches the SIL redundancy cap
    stages = ([_Stage(0, "broken", prox=0.95)]                       # a critical already offline
              + [_Stage(1, "nominal", prox=0.95)]                    # a second critical, still online
              + [_Stage(i, "nominal", prox=0.1) for i in range(2, 10)])
    world = _World(stages)
    ps = _build_plant_state(world)
    result = verify([PlannedAction(PREVENTIVE_MAINTENANCE, 1, "risk")], ps)
    assert result.approved is False
    assert any(v["constraint"] == "critical_redundancy" for v in result.to_dict()["violations"])


def test_verifier_still_approves_safe_single_maintenance():
    # the normal case: a healthy line, one at-risk stage → the plan must still be APPROVED (no false-reject regression)
    stages = [_Stage(i, "nominal", prox=0.1) for i in range(10)]
    stages[3] = _Stage(3, "degraded", prox=0.5)
    world = _World(stages)
    ps = _build_plant_state(world)
    result = verify([PlannedAction(PREVENTIVE_MAINTENANCE, 3, "risk")], ps)
    assert result.approved is True


# ---- G-045: decision-log persistence ---------------------------------------

def test_persist_is_honest_noop_without_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    assert _persist_decision_log(caller="slice_runner", tool="preventive_maintenance",
                                 inputs={"a": 1}, outputs={"b": 2}) is None


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: decision_logs round-trip not exercisable")
def test_persist_writes_real_decision_log_row():
    import psycopg

    did = _persist_decision_log(
        caller="slice_runner", tool="preventive_maintenance",
        inputs={"stage_id": 3, "telemetry": {"torque_nm": 55.0}, "prediction": {"p_fail": 0.9}},
        outputs={"decision": {"kind": "preventive_maintenance"}, "verification": {"approved": True}, "executed": True})
    assert did is not None
    with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT caller, tool, input_hash, output_hash, inputs->>'stage_id' FROM decision_logs "
                    "WHERE decision_id = %s", (did,))
        row = cur.fetchone()
    assert row is not None
    caller, tool, ih, oh, sid = row
    assert caller == "slice_runner" and tool == "preventive_maintenance"
    assert len(ih) == 64 and len(oh) == 64 and ih != oh        # real SHA-256 provenance hashes
    assert sid == "3"
    # cleanup
    with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM decision_logs WHERE decision_id = %s", (did,))


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: non-uuid incident handling not exercisable")
def test_persist_stores_non_uuid_incident_ref_in_inputs():
    import psycopg

    did = _persist_decision_log(caller="slice_runner", tool="preventive_maintenance",
                                inputs={"stage_id": 5}, outputs={"executed": False}, incident_id="sim-tag-123")
    assert did is not None
    with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT incident_id, inputs->>'incident_ref' FROM decision_logs WHERE decision_id = %s", (did,))
        inc_fk, inc_ref = cur.fetchone()
        cur.execute("DELETE FROM decision_logs WHERE decision_id = %s", (did,))
    assert inc_fk is None and inc_ref == "sim-tag-123"   # non-uuid tag stored in inputs, not the FK
