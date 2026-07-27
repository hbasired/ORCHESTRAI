"""Stage 37 (G-024) — bidirectional CDC: value-edit → DIAGNOSE the induced problem → self-optimize.

Three tiers, honesty-discipline throughout:
  1. the PURE diagnostic reasoner (`diagnose_change`) — every rule + benign cases + magnitude-derived severity (no infra);
  2. `process_value_edit` closed-loop wrapper — diagnosed vs benign, and (DB) the audit-signed reasoning;
  3. a LIVE end-to-end roundtrip — a real Postgres value UPDATE fires the trigger → outbox → drain → SimWorld inject.
"""
import os
import uuid

import pytest

from ingestion.cdc_reasoner import diagnose_change, process_value_edit
from ingestion.cdc_listener import change_to_inject

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))
_DSN = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


# ---- 1. pure diagnostic reasoner (no infra) --------------------------------

def test_defect_rate_jump_is_defect_surge_critical():
    p = diagnose_change("stages", "defect_rate", 0.02, 0.15, target_id=3)
    assert p is not None and p.diagnosed_type == "defect_surge" and p.severity == "critical"
    assert p.basis and "defect" in p.rationale.lower()


def test_defect_rate_moderate_is_warning_not_critical():
    p = diagnose_change("stages", "defect_rate", 0.02, 0.09, target_id=3)
    assert p is not None and p.diagnosed_type == "defect_surge" and p.severity == "warning"


def test_defect_rate_below_band_is_benign():
    assert diagnose_change("stages", "defect_rate", 0.02, 0.04, target_id=3) is None


def test_defect_rate_decrease_is_benign():
    assert diagnose_change("stages", "defect_rate", 0.20, 0.05, target_id=3) is None


def test_throughput_drop_is_machine_crack_severity_scales():
    warn = diagnose_change("stages", "throughput", 100, 60, target_id=3)   # 40% drop
    crit = diagnose_change("stages", "throughput", 100, 45, target_id=3)   # 55% drop
    assert warn is not None and warn.diagnosed_type == "machine_crack" and warn.severity == "warning"
    assert crit is not None and crit.severity == "critical"


def test_small_throughput_drop_is_benign():
    assert diagnose_change("stages", "throughput", 100, 90, target_id=3) is None   # 10% — noise


def test_target_throughput_edit_is_ignored():
    assert diagnose_change("stages", "target_throughput", 100, 40, target_id=3) is None


def test_energy_spike_is_power_dip():
    p = diagnose_change("stages", "energy_consumption_kw", 12, 25, target_id=3)   # +108%
    assert p is not None and p.diagnosed_type == "power_dip" and p.severity == "critical"
    small = diagnose_change("stages", "energy_consumption_kw", 12, 15, target_id=3)  # +25%
    assert small is None


def test_inventory_below_reorder_is_late_delivery():
    p = diagnose_change("inventory", "current_stock", 800, 300, target_id=7, context={"reorder_point": 600})
    assert p is not None and p.diagnosed_type == "late_delivery" and p.severity == "critical"  # <= 0.5*reorder
    warn = diagnose_change("inventory", "current_stock", 800, 500, target_id=7, context={"reorder_point": 600})
    assert warn is not None and warn.severity == "warning"


def test_inventory_above_reorder_is_benign():
    assert diagnose_change("inventory", "current_stock", 800, 700, target_id=7, context={"reorder_point": 600}) is None


def test_inventory_no_reorder_context_is_benign():
    # without a reorder_point we cannot honestly diagnose a stockout — no fabrication
    assert diagnose_change("inventory", "current_stock", 800, 100, target_id=7) is None


def test_days_of_supply_low_is_late_delivery():
    p = diagnose_change("inventory", "days_of_supply", 10, 1.5, target_id=7)
    assert p is not None and p.diagnosed_type == "late_delivery"


def test_supplier_reliability_drop_is_late_delivery():
    p = diagnose_change("suppliers", "reliability_score", 0.92, 0.45, target_id=2)
    assert p is not None and p.diagnosed_type == "late_delivery" and p.severity == "critical"
    warn = diagnose_change("suppliers", "reliability_score", 0.92, 0.65, target_id=2)
    assert warn is not None and warn.severity == "warning"


def test_supplier_reliability_improvement_is_benign():
    assert diagnose_change("suppliers", "reliability_score", 0.6, 0.95, target_id=2) is None


def test_supplier_lead_time_spike_is_late_delivery():
    p = diagnose_change("suppliers", "lead_time_days", 4, 9, target_id=2)   # +125%, >=5
    assert p is not None and p.diagnosed_type == "late_delivery"


def test_unmonitored_column_is_benign():
    assert diagnose_change("stages", "name", "a", "b", target_id=3) is None
    assert diagnose_change("widgets", "color", 1, 2, target_id=3) is None


def test_to_incident_shape_and_source():
    inc = diagnose_change("stages", "defect_rate", 0.02, 0.15, target_id=3).to_incident()
    assert inc["type"] == "defect_surge" and inc["source"] == "cdc:value_edit"
    assert inc["details"]["source"] == "cdc:value_edit" and inc["diagnosis"]


# ---- 2. the listener routing (value edits reach the reasoner) --------------

def test_listener_routes_value_edit_to_reasoner():
    req = change_to_inject("stages", {"table": "stages", "column": "defect_rate",
                                      "old": 0.02, "new": 0.15, "target_id": 3})
    assert req is not None and req.type == "defect_surge" and req.severity == "critical"


def test_listener_value_edit_benign_is_none():
    assert change_to_inject("stages", {"table": "stages", "column": "utilization",
                                       "old": 0.9, "new": 0.95, "target_id": 3}) is None


def test_status_change_still_works_after_value_branch():
    # regression: the Stage-13 status path must survive the new value-edit branch
    req = change_to_inject("stages", {"stage_id": 5, "new_status": "broken"})
    assert req is not None and req.type == "machine_crack" and req.severity == "critical"


# ---- 3. process_value_edit closed-loop wrapper -----------------------------

def test_process_value_edit_benign_does_not_diagnose():
    out = process_value_edit("stages", "utilization", 0.9, 0.95, target_id=3)
    assert out["diagnosed"] is False and "benign" in out["reason"].lower()


def test_process_value_edit_diagnoses_without_running_loop():
    out = process_value_edit("stages", "defect_rate", 0.02, 0.15, target_id=3, run_loop=False)
    assert out["diagnosed"] is True and out["problem"]["type"] == "defect_surge"
    assert "loop" not in out and out["note"]


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: audit-chain signing not exercisable")
def test_process_value_edit_signs_audit_row():
    out = process_value_edit("suppliers", "reliability_score", 0.92, 0.4, target_id=2)
    assert out["diagnosed"] is True
    assert out.get("audit_seq") is not None, "the diagnosis reasoning should be signed to the audit chain"


# ---- 4. LIVE end-to-end: real DB value UPDATE → trigger → outbox → drain → inject ----

@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: live value-edit roundtrip not exercisable")
@pytest.mark.timeout(60)
async def test_db_value_edit_drains_into_simworld():
    import asyncio
    import psycopg
    from simulation.sim_world import SimWorld
    from api.simulation_routes import set_sim_world
    from ingestion.cdc_listener import CDCListener

    sw = SimWorld(seed=20260524)
    set_sim_world(sw)
    sid = 90000 + (uuid.uuid4().int % 1000)
    with psycopg.connect(_DSN, autocommit=True) as wc, wc.cursor() as cur:
        cur.execute("INSERT INTO stages (id, name, defect_rate, throughput, energy_consumption_kw, utilization, status) "
                    "VALUES (%s,'t',0.02,100,12,0.9,'normal') ON CONFLICT (id) DO UPDATE SET defect_rate=0.02", (sid,))
    listener = CDCListener()
    assert await listener.start() is True
    try:
        baseline = listener.injected
        with psycopg.connect(_DSN, autocommit=True) as wc, wc.cursor() as cur:
            cur.execute("UPDATE stages SET defect_rate=0.15 WHERE id=%s", (sid,))   # the operator edit
        for _ in range(50):
            if listener.injected > baseline:
                break
            await asyncio.sleep(0.1)
        assert listener.injected > baseline, "the value-edit NOTIFY→diagnose→inject path did not fire"
    finally:
        await listener.stop()
        set_sim_world(None)
        with psycopg.connect(_DSN, autocommit=True) as wc, wc.cursor() as cur:
            cur.execute("DELETE FROM stages WHERE id=%s", (sid,))
