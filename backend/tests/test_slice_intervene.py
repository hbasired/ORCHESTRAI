"""Stage 6 — intervene v0 tests (AC3): policy rules + sim-only execution.

Policy tests are pure (no model). The closed-loop test uses the real brain and
skips honestly when it is absent. Sim runs are seeded → deterministic.
"""
from __future__ import annotations

import pytest

from agents.embodied_agent import EmbodiedAgent
from ml.failure_predictor import get_failure_predictor
from services.diagnosis import diagnose
from services.intervention_policy import (
    MONITOR,
    PREVENTIVE_MAINTENANCE,
    WAIT_EXTERNAL,
    decide_intervention,
)
from simulation.sim_world import SimWorld

BRAIN_AVAILABLE = get_failure_predictor().is_available()
needs_brain = pytest.mark.skipif(not BRAIN_AVAILABLE, reason="trained Stage-4 brain unavailable (honest skip)")


def _telemetry(**overrides) -> dict:
    base = {"stage_id": 3, "name": "machining", "sim_time_seconds": 0.0, "status": "degraded",
            "type_": "M", "air_temp_k": 300.0, "process_temp_k": 310.0, "rot_speed_rpm": 1500.0,
            "torque_nm": 40.0, "tool_wear_min": 50.0, "queue_depth": 5, "crack_proximity": 0.5}
    base.update(overrides)
    return base


def _pred(p, risk):
    return {"p_fail": p, "at_risk": risk, "threshold": 0.779, "arch": "XGBoost", "dataset": "AI4I 2020"}


# ---- policy rules (pure) ----------------------------------------------------

def test_policy_monitors_when_not_at_risk():
    d = diagnose(_pred(0.1, False), _telemetry())
    decision = decide_intervention(d)
    assert decision.kind == MONITOR


def test_policy_waits_on_external_power_event():
    t = _telemetry(torque_nm=10.0, rot_speed_rpm=1000.0, process_temp_k=312.0)
    d = diagnose(_pred(0.85, True), t, recent_incidents=[{"type": "power_dip"}])
    decision = decide_intervention(d)
    assert decision.kind == WAIT_EXTERNAL
    assert "power event" in decision.rationale


def test_policy_maintains_on_wear_breach_with_evidence_in_rationale():
    d = diagnose(_pred(0.95, True), _telemetry(tool_wear_min=225.0))
    decision = decide_intervention(d, queue_depth=4, capacity=15)
    assert decision.kind == PREVENTIVE_MAINTENANCE
    assert "wear_breach" in decision.rationale
    assert decision.diagnosis["primary_cause"] == "wear_breach"


def test_policy_monitors_on_weak_uncorroborated_model_signal():
    d = diagnose(_pred(0.80, True), _telemetry())  # at-risk, healthy physics, p<0.9
    decision = decide_intervention(d)
    assert decision.kind == MONITOR


def test_coordinator_method_delegates_to_shared_policy():
    d = diagnose(_pred(0.95, True), _telemetry(tool_wear_min=225.0))
    via_agent = EmbodiedAgent.decide_intervention(d, queue_depth=4, capacity=15)
    direct = decide_intervention(d, queue_depth=4, capacity=15)
    assert via_agent.to_dict() == direct.to_dict()


# ---- maintenance mechanics (sim, deterministic per seed) --------------------

def test_start_maintenance_cancels_crack_and_recovers():
    w = SimWorld(seed=7)
    stage = w.stages[9]  # packaging: mtbf 10 h — natural failure in window is unlikely & seed-fixed
    w.env.run(until=30.0)
    stage.schedule_crack(eta_seconds=720.0)
    assert stage.status == "degraded" and stage.crack_failure_at is not None
    assert stage.start_maintenance() is True
    assert stage.status == "maintenance"
    assert stage.crack_failure_at is None  # crack repaired before it fails
    # Maintenance duration = 0.5 × mttr(6 min) = 180 s; run past it + the stale wake-up.
    w.env.run(until=30.0 + 1200.0)
    assert stage.status == "nominal"
    assert stage.tool_wear_accum_min == 0.0
    assert stage.maintenance_count == 1
    assert stage.crack_breakdown_count == 0  # the stale crack wake-up did NOT fire a breakdown
    assert stage.time_maintenance_seconds > 0


def test_start_maintenance_refuses_when_broken():
    w = SimWorld(seed=7)
    stage = w.stages[9]
    stage.status = "broken"
    assert stage.start_maintenance() is False


def test_unintervened_crack_costs_multiplied_repair():
    w = SimWorld(seed=11)
    stage = w.stages[9]
    w.env.run(until=10.0)
    stage.schedule_crack(eta_seconds=300.0)
    w.env.run(until=10.0 + 300.0 + 6 * 60.0 * 2.5 * 4)  # generous window for 2.5× mttr draw
    assert stage.crack_breakdown_count == 1
    assert stage.time_broken_seconds > 0


# ---- closed loop (real brain) ------------------------------------------------

@needs_brain
def test_slice_loop_prevents_crack_breakdown_end_to_end():
    from services.slice_runner import SliceLoop
    from simulation.entities import Incident, InjectRequest

    w = SimWorld(seed=2026)

    def inject(env):
        yield env.timeout(60.0)
        w._apply_incident(Incident.from_request(
            InjectRequest(type="machine_crack", target_id=3, details={}, severity="warning")))

    w.env.process(inject(w.env))
    loop = SliceLoop(w, sample_period_seconds=30.0)
    loop.start()
    w.env.run(until=2400.0)  # 40 sim-min: crack eta 12 min + maintenance 12.5 min + margin

    stage = w.stages[3]
    executed = [e for e in loop.trail.interventions if e.payload.get("executed")]
    assert len(executed) >= 1, "the loop should have executed at least one preventive maintenance"
    assert executed[0].payload["kind"] == "preventive_maintenance"
    assert stage.maintenance_count >= 1
    assert stage.crack_breakdown_count == 0, "the predicted crack must not become a breakdown"
    # Decision provenance: rationale carries the evidence trail.
    assert "Evidence:" in executed[0].payload["rationale"]
