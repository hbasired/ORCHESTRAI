"""Stage 26 — supply-chain layer tests: consensus determinism, safety gating, disruption→replan,
honest-unavailable/abstention, audit emission, and the closed material loop. Infra-free except where marked."""
from __future__ import annotations

import os

import pytest

from agents.supply_chain.consensus import Cfp, ContractNetCoordinator, SUPPLY_CHAIN_ORDER_CONTRACT
from agents.supply_chain.disruption_monitor import (
    MIN_OBS, STARVATION_TICKS, DisruptionMonitor,
)
from agents.supply_chain.roles import DemandAgent, DemandEstimate, InventoryAgent
from agents.supply_chain.signals import SignalObserver


def _snapshot(t: float, queues: dict[int, int], suppliers: dict[int, tuple[int, int]],
              throughput: float = 50.0) -> dict:
    return {
        "sim_time_seconds": t,
        "throughput_units_per_hour": throughput,
        "stages": [{"stage_id": sid, "queue_depth": q, "status": "nominal"} for sid, q in queues.items()],
        "suppliers": [{"id": sid, "sku": "default", "fulfilled": f, "failed": x}
                      for sid, (f, x) in suppliers.items()],
    }


def _observer_with_leads(leads_by_supplier: dict[int, list[float]], throughput_ticks: int = 10) -> SignalObserver:
    obs = SignalObserver()
    for i in range(throughput_ticks):
        obs.observe(_snapshot(300.0 * (i + 1), {0: 10, 1: 10},
                              {sid: (len(v), 0) for sid, v in leads_by_supplier.items()}))
    for sid, leads in leads_by_supplier.items():
        for lead in leads:
            obs.note_lead(sid, lead)
    return obs


# ---------------------------------------------------------------------------
# Honest abstention (no fabricated numbers)
# ---------------------------------------------------------------------------

def test_demand_agent_abstains_without_history():
    assert DemandAgent().estimate(SignalObserver()) is None


def test_inventory_agent_abstains_without_demand():
    assert InventoryAgent().needs(SignalObserver(), None, {0: 50}) == []


def test_cold_start_is_single_labelled_bootstrap_order():
    obs = _observer_with_leads({0: []})  # throughput history exists; NO lead observations
    est = DemandAgent().estimate(obs)
    assert est is not None and est.source == "empirical (SimWorld throughput history)"
    needs = InventoryAgent().needs(obs, est, {0: 50, 1: 50})
    assert len(needs) == 1 and needs[0].order_qty == 1
    assert "bootstrap exploration" in needs[0].policy  # labelled, not a fabricated ROP


def test_unobserved_supplier_bid_is_labelled_exploration_not_performance_claim():
    obs = _observer_with_leads({0: [], 1: []})
    coord = ContractNetCoordinator(obs)
    bids = coord.collect_bids(Cfp("c1", 0, "default", 1, 5, 50))
    # Unobserved suppliers bid at the EXPLICIT exploration cost — a labelled policy choice, never a
    # fabricated performance claim.
    assert bids and all(b.cost == 1e6 and "exploration bid" in b.basis for b in bids)


# ---------------------------------------------------------------------------
# CNP determinism + award logic
# ---------------------------------------------------------------------------

def test_award_is_deterministic_same_inputs_same_winner():
    obs = _observer_with_leads({0: [300.0] * 6, 1: [900.0] * 6})
    a1 = ContractNetCoordinator(obs).award(Cfp("c1", 0, "default", 3, 5, 50))
    a2 = ContractNetCoordinator(obs).award(Cfp("c1", 0, "default", 3, 5, 50))
    assert a1.supplier_id == a2.supplier_id == 0  # faster observed supplier wins, reproducibly
    assert a1.allowed and a2.allowed


def test_exploration_round_awards_least_observed_supplier():
    obs = _observer_with_leads({0: [300.0] * 20, 1: [900.0] * 6})
    coord = ContractNetCoordinator(obs, exploration_every=2)
    first = coord.award(Cfp("c1", 0, "default", 1, 5, 50))
    second = coord.award(Cfp("c2", 0, "default", 1, 5, 50))  # round 2 -> exploration
    assert first.supplier_id == 0 and not first.exploration
    assert second.supplier_id == 1  # least-observed eligible, deterministically
    assert second.exploration  # surfaced on the award (and in its audit payload)


def test_quarantined_supplier_gets_no_award():
    obs = _observer_with_leads({0: [300.0] * 6})
    coord = ContractNetCoordinator(obs, quarantined={0})
    aw = coord.award(Cfp("c1", 0, "default", 1, 5, 50))
    assert aw.supplier_id is None and not aw.allowed
    assert "no eligible bids" in aw.gate_reason


# ---------------------------------------------------------------------------
# Safety gating (Hard Rule 3 at the supply-chain boundary)
# ---------------------------------------------------------------------------

def test_gate_blocks_order_exceeding_free_capacity():
    obs = _observer_with_leads({0: [300.0] * 6})
    coord = ContractNetCoordinator(obs)
    # buffer 48 of 50 -> free capacity 2; qty 10 must be BLOCKED by the contract precondition
    aw = coord.award(Cfp("c1", 0, "default", 10, 48, 50))
    assert aw.supplier_id == 0
    assert not aw.allowed
    assert "qty_positive_bounded" in aw.gate_reason


def test_gate_blocks_insane_buffer_reading():
    obs = _observer_with_leads({0: [300.0] * 6})
    aw = ContractNetCoordinator(obs).award(Cfp("c1", 0, "default", 1, 60, 50))  # buffer > capacity
    assert not aw.allowed and "buffer_capacity_sane" in aw.gate_reason


def test_contract_is_sil0_and_fail_safe_no_action():
    assert SUPPLY_CHAIN_ORDER_CONTRACT.sil == 0
    assert SUPPLY_CHAIN_ORDER_CONTRACT.fail_safe_path == "no_action"


# ---------------------------------------------------------------------------
# Disruption monitor
# ---------------------------------------------------------------------------

def test_overdue_pending_detects_a_frozen_supplier():
    """Drill-verified semantics (4th detector design): a freeze-type delay produces NO lead observations, so
    detection watches the OTHER side — orders placed but unfulfilled past a log-space 3.5-sigma age."""
    obs = _observer_with_leads({0: [300.0, 310.0, 295.0, 305.0, 302.0, 298.0, 300.0, 307.0,
                                    303.0, 299.0, 306.0, 301.0]})  # 12 observed leads (sound basis)
    mon = DisruptionMonitor(obs, raise_incident=lambda inc: None)
    assert mon.check() == []  # baseline: nothing outstanding
    # Three orders placed at t=3000, never fulfilled; the clock advances far past the age threshold.
    for _ in range(3):
        obs.note_outstanding(0, 3000.0)
    obs.observe(_snapshot(3000.0 + 300.0 * 40, {0: 10, 1: 10}, {0: (12, 0), 1: (0, 0)}))  # now-placed = 12000s
    found = mon.check()
    hits = [d for d in found if d.kind == "latency_spike" and d.subject == "supplier:0"]
    assert hits and hits[0].detail["detector"] == "overdue_pending"
    assert hits[0].detail["threshold_basis"] == "own_history"


def test_overdue_uses_fleet_pooled_basis_when_own_history_thin():
    """Drill finding #5 (seed 42): the freeze STARVES the detector's own threshold basis — a recently-promoted
    supplier has too few leads. The fleet-pooled distribution is the labelled fallback."""
    obs = _observer_with_leads({0: [300.0] * 12, 1: [300.0, 305.0]})  # supplier 1: only 2 own leads
    mon = DisruptionMonitor(obs, raise_incident=lambda inc: None)
    for _ in range(3):
        obs.note_outstanding(1, 3000.0)
    obs.observe(_snapshot(3000.0 + 300.0 * 40, {0: 10, 1: 10}, {0: (12, 0), 1: (2, 0)}))
    found = mon.check()
    hits = [d for d in found if d.kind == "latency_spike" and d.subject == "supplier:1"]
    assert hits and hits[0].detail["threshold_basis"] == "fleet_pooled"


def test_normal_pendings_and_single_tail_do_not_false_positive():
    obs = _observer_with_leads({0: [300.0, 310.0, 295.0, 305.0, 302.0, 298.0, 300.0, 307.0,
                                    303.0, 299.0, 306.0, 301.0]})
    mon = DisruptionMonitor(obs, raise_incident=lambda inc: None)
    obs.note_lead(0, 330.0)          # +10% single draw: noise
    obs.note_outstanding(0, 11800.0)  # one FRESH pending order (age ~200s at t=12000)
    obs.note_outstanding(0, 11900.0)
    obs.observe(_snapshot(12000.0, {0: 10, 1: 10}, {0: (13, 0), 1: (0, 0)}))
    assert mon.check() == []  # young pendings + a single tail draw fire nothing


def test_failing_supplier_is_quarantined_and_incident_raised():
    raised: list[dict] = []
    obs = SignalObserver()
    # 8 observed orders, 6 failed -> failure rate 0.75 >= 0.5
    obs.observe(_snapshot(300, {0: 10}, {0: (2, 6)}))
    mon = DisruptionMonitor(obs, raise_incident=raised.append)
    found = mon.check()
    assert any(d.kind == "supplier_failure" for d in found)
    assert 0 in mon.quarantined
    assert raised and raised[0]["type"] == "supply_chain_supplier_failure"


def test_stockout_detected_after_persistent_starvation():
    obs = SignalObserver()
    mon = DisruptionMonitor(obs, raise_incident=lambda inc: None)
    for i in range(STARVATION_TICKS + 1):
        obs.observe(_snapshot(300.0 * (i + 1), {3: 0}, {0: (0, 0)}))
        found = mon.check()
    assert any(d.kind == "stockout" and d.subject == "stage:3" for d in found) or \
           ("stockout", "stage:3") in mon._raised


def test_incident_raised_exactly_once_per_episode():
    raised: list[dict] = []
    obs = SignalObserver()
    obs.observe(_snapshot(300, {0: 10}, {0: (2, 6)}))
    mon = DisruptionMonitor(obs, raise_incident=raised.append)
    mon.check(); mon.check(); mon.check()
    assert len([r for r in raised if r["type"] == "supply_chain_supplier_failure"]) == 1


# ---------------------------------------------------------------------------
# End-to-end on the REAL SimWorld (closed material loop + audit emission)
# ---------------------------------------------------------------------------

def test_simworld_loop_orders_deliver_and_feed_buffers():
    from simulation.sim_world import SimWorld
    from agents.supply_chain import SupplyChainOrchestrator

    w = SimWorld(seed=7)
    orch = SupplyChainOrchestrator(w)
    total_orders = 0
    for i in range(40):
        w.env.run(until=(i + 1) * 300)
        total_orders += orch.tick().orders_placed
    assert total_orders > 0, "the layer must place real orders"
    delivered = sum(s.fulfilled for s in w.suppliers.values())
    assert delivered > 0, "fulfilled orders must exist"
    # exact leads observed via the delivery callback (the closed loop is measurable)
    assert any(s.lead_total > 0 for s in orch.observer.suppliers.values())


def test_simworld_determinism_same_seed_same_orders():
    from simulation.sim_world import SimWorld
    from agents.supply_chain import SupplyChainOrchestrator

    def run(seed: int) -> list[int]:
        w = SimWorld(seed=seed)
        orch = SupplyChainOrchestrator(w)
        out = []
        for i in range(30):
            w.env.run(until=(i + 1) * 300)
            out.append(orch.tick().orders_placed)
        return out

    assert run(11) == run(11)  # runtime-determinism invariant holds for the supply-chain layer


requires_db = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")),
    reason="no DATABASE_URL/POSTGRES_URL — audit-row emission needs Postgres",
)


@requires_db
def test_award_writes_signed_audit_rows():
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        probe = psycopg.connect(dsn, connect_timeout=5); probe.close()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    obs = _observer_with_leads({0: [300.0] * 6})
    aw = ContractNetCoordinator(obs).award(Cfp("audit-test-1", 0, "default", 2, 5, 50))
    assert aw.audited and aw.audit_seq is not None, "award must be a signed audit row when the DB is up"
    # Under pytest the R1 test-isolation conftest points audit writes at a THROWAWAY DB — read the row from
    # the SAME chain the append used (never the real attestable chain; that isolation is load-bearing).
    chain_dsn = os.environ.get("AUDIT_CHAIN_DATABASE_URL") or dsn
    with psycopg.connect(chain_dsn, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute("SELECT action, payload->>'cfp_id' FROM audit_chain WHERE seq = %s", (aw.audit_seq,))
        action, cfp_id = cur.fetchone()
    assert action == "supply_chain.award" and cfp_id == "audit-test-1"
