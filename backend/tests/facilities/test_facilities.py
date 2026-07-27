"""Stage 38 — Facilities / Energy head-agent tests (G-018).

Tiers: (1) the tariff (ToU + demand charge), (2) the MILP optimiser — real peak-shaving, production floor held,
deterministic, greedy fallback, honest 0% when unshiftable, (3) the orchestrator KB_25 loop — validator gate,
diagnosis, Hard Rule 3 (no actuator emitter), (4) the A/B artefact, (5) the API route.
"""
import os

import pytest

from agents.facilities.optimizer import baseline_plan, optimize_energy
from agents.facilities.orchestrator import ENERGY_LOAD_SHIFT_CONTRACT, EnergyOrchestrator
from agents.facilities.signals import FacilityProfile, StageLoad, observe_from_calibration
from agents.facilities.tariff import Tariff

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))


# ---- 1. tariff ------------------------------------------------------------

def test_tariff_periods_and_prices():
    t = Tariff()
    assert t.period(2) == "off_peak" and t.energy_price(2) == 0.10
    assert t.period(9) == "mid_peak" and t.energy_price(9) == 0.16
    assert t.period(14) == "on_peak" and t.energy_price(14) == 0.28
    assert t.period(23) == "off_peak"


def test_tariff_bill_energy_plus_demand():
    t = Tariff(horizon_slots=3, slot_hours=1.0, demand_charge_per_kw=1.0)
    # slots 0,1,2 are all off-peak (0.10); loads 10,20,10 kW → energy=(10+20+10)*0.10=4.0; peak=20 → demand=20
    bill = t.bill([10.0, 20.0, 10.0])
    assert bill["energy_cost"] == pytest.approx(4.0)
    assert bill["peak_kw"] == 20.0 and bill["demand_cost"] == pytest.approx(20.0)
    assert bill["total_cost"] == pytest.approx(24.0)


# ---- 2. optimiser ---------------------------------------------------------

def test_observe_uses_real_nominal_kw():
    prof = observe_from_calibration(required_slots=6)
    # the real calibration: intake 2.0, press 14.0, weld 18.0, machining 22.0, wash 8.0, paint 12.0 ...
    kw = {l.name: l.kw for l in prof.loads}
    assert kw["intake"] == 2.0 and kw["machining"] == 22.0 and kw["weld"] == 18.0
    assert prof.base_kw > 0  # a documented non-zero HVAC/lighting baseline


def test_milp_reduces_peak_and_holds_production_floor():
    prof = observe_from_calibration(required_slots=6)
    tar = Tariff()
    base = baseline_plan(prof, tar)
    opt = optimize_energy(prof, tar, prefer="milp")
    assert opt.method == "milp"
    # the MILP must not INCREASE the peak, and here it strictly reduces it
    assert opt.bill["peak_kw"] < base.bill["peak_kw"]
    # production floor: every stage still gets EXACTLY its required run-hours (no output dropped)
    for l in prof.loads:
        assert len(opt.schedule[l.stage_id]) == l.required_slots


def test_milp_is_deterministic():
    prof = observe_from_calibration(required_slots=6)
    a = optimize_energy(prof, Tariff(), prefer="milp")
    b = optimize_energy(prof, Tariff(), prefer="milp")
    assert a.bill == b.bill and a.schedule == b.schedule


def test_greedy_fallback_is_labelled_and_valid():
    prof = observe_from_calibration(required_slots=6)
    g = optimize_energy(prof, Tariff(), prefer="greedy")
    assert g.method == "greedy"
    for l in prof.loads:
        assert len(g.schedule[l.stage_id]) == l.required_slots


def test_unshiftable_facility_returns_zero_reduction_not_fabricated():
    # a single load that must run every slot of its window (no slack) — the optimiser cannot improve → honest 0%
    prof = FacilityProfile(horizon_slots=4,
                           loads=[StageLoad(0, "fixed", kw=10.0, required_slots=4, earliest_slot=0, latest_slot=3)],
                           base_kw=0.0)
    tar = Tariff(horizon_slots=4)
    base = baseline_plan(prof, tar)
    opt = optimize_energy(prof, tar, prefer="milp")
    assert opt.bill["peak_kw"] == base.bill["peak_kw"]  # no shifting possible → no fabricated saving


# ---- 3. orchestrator (KB_25 loop) -----------------------------------------

def test_cycle_diagnoses_demand_breach_and_gate_allows():
    orch = EnergyOrchestrator(demand_cap_kw=100.0)
    res = orch.run_cycle(required_slots=6)
    assert res.diagnosed == "demand_charge_breach"     # baseline peak (130.8) > cap (100)
    assert res.allowed is True and res.gate_reason == "ok"
    assert res.committed is True
    assert res.peak_reduction_pct > 0 and res.plan.method == "milp"


def test_cycle_no_breach_when_cap_high():
    orch = EnergyOrchestrator(demand_cap_kw=10_000.0)
    res = orch.run_cycle(required_slots=6)
    assert res.diagnosed is None


def test_contract_rejects_a_peak_increasing_plan():
    # the precondition must FAIL if a plan claims to raise the peak (guards against a bad optimiser)
    from safety.validator import validate
    from safety.contract import Action
    ws = {"production_floor_met": True, "windows_respected": True,
          "baseline_peak_kw": 100.0, "optimized_peak_kw": 120.0,   # WORSE
          "optimized_kwh": 50.0, "required_kwh": 50.0}
    action = Action(contract=ENERGY_LOAD_SHIFT_CONTRACT.name, actuator="energy.load_shift", params={}, target="facility")
    decision = validate(action, ws, ENERGY_LOAD_SHIFT_CONTRACT)
    assert decision.allow is False


def test_contract_rejects_dropped_production():
    from safety.validator import validate
    from safety.contract import Action
    ws = {"production_floor_met": False, "windows_respected": True,
          "baseline_peak_kw": 100.0, "optimized_peak_kw": 70.0,
          "optimized_kwh": 40.0, "required_kwh": 50.0}   # energy not conserved + floor not met
    action = Action(contract=ENERGY_LOAD_SHIFT_CONTRACT.name, actuator="energy.load_shift", params={}, target="facility")
    assert validate(action, ws, ENERGY_LOAD_SHIFT_CONTRACT).allow is False


def test_hard_rule_3_no_actuator_emitter_in_facilities():
    """Hard Rule 3: the facilities agent PROPOSES (routes through the validator) and never actuates directly —
    no actuator.* emit, no dispatch_order() call. (Doc/comment mentions that EXPLAIN the rule are fine.)"""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2] / "agents" / "facilities"
    calls_validate = False
    for py in root.glob("*.py"):
        src = py.read_text(encoding="utf-8")
        # no actual emitter CALLS (the sole codebase emitter is master.dispatch_order(...))
        assert "dispatch_order(" not in src, f"{py.name} calls the actuator emitter"
        assert "actuator." not in src, f"{py.name} emits an actuator.* command/span"
        if "validate(" in src:
            calls_validate = True
    # the agent DOES route its proposal through the safety validator
    assert calls_validate, "the facilities orchestrator must route its load-shift through safety.validator.validate()"


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: audit signing not exercisable")
def test_cycle_signs_audit_row():
    res = EnergyOrchestrator(demand_cap_kw=100.0).run_cycle(required_slots=6)
    assert res.audited is True and res.audit_seq is not None


# ---- 4. A/B artefact ------------------------------------------------------

def test_ab_artifact_is_honest_and_floors_hold():
    import json
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[2] / "training" / "evals" / "results" / "energy_ab.json"
    if not p.exists():
        pytest.skip("energy_ab.json not generated yet")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["all_floor_ok"] is True
    assert "SimWorld" in data["honest_label"] and "G-035" in data["honest_label"]
    assert data["aggregate_milp"]["peak_reduction_pct"]["mean"] > 0


# ---- 5. API route ---------------------------------------------------------

def test_route_optimize_energy():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.facilities_routes import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.post("/facilities/optimize-energy", json={"required_slots": 6, "demand_cap_kw": 100.0}).json()
    assert r["method"] == "milp"
    assert r["optimized_peak_kw"] < r["baseline_peak_kw"]
    assert r["diagnosed"] == "demand_charge_breach"
    assert "never actuates" in r["note"]
