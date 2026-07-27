"""Stage 6 — live predict path tests (AC1): real telemetry → real brain.

The telemetry tests run everywhere (no model needed). The brain-integration
tests run the REAL XGBoost predictor and skip honestly when it is absent —
they never fabricate a probability.
"""
from __future__ import annotations

import pytest

from ml.failure_predictor import get_failure_predictor
from simulation.sim_world import SimWorld

BRAIN_AVAILABLE = get_failure_predictor().is_available()
needs_brain = pytest.mark.skipif(not BRAIN_AVAILABLE, reason="trained Stage-4 brain unavailable (honest skip)")


def _world(seed: int = 1234) -> SimWorld:
    # In-environment use: never world.start() — drive env.run() directly.
    return SimWorld(seed=seed)


def test_telemetry_shape_and_units():
    w = _world()
    w.env.run(until=120.0)
    t = w.stages[3].telemetry()
    for key in ("stage_id", "air_temp_k", "process_temp_k", "rot_speed_rpm",
                "torque_nm", "tool_wear_min", "status", "crack_proximity"):
        assert key in t
    assert 290.0 < t["air_temp_k"] < 310.0
    assert 295.0 < t["process_temp_k"] < 325.0
    assert t["rot_speed_rpm"] > 0
    assert t["tool_wear_min"] >= 0
    assert t["crack_proximity"] == 0.0  # healthy machine


def test_telemetry_is_deterministic_per_seed():
    a, b = _world(seed=777), _world(seed=777)
    a.env.run(until=300.0)
    b.env.run(until=300.0)
    assert a.stages[2].telemetry() == b.stages[2].telemetry()


def test_degraded_telemetry_drifts_toward_failure_regime():
    w = _world()
    w.env.run(until=60.0)
    healthy = w.stages[3].telemetry()
    w.stages[3].schedule_crack(eta_seconds=600.0)
    w.env.run(until=60.0 + 540.0)  # 90% of the way to failure
    degraded = w.stages[3].telemetry()
    assert degraded["crack_proximity"] > 0.8
    assert degraded["tool_wear_min"] > healthy["tool_wear_min"] + 100.0   # → TWF band
    assert degraded["rot_speed_rpm"] < healthy["rot_speed_rpm"] * 0.8     # → HDF band
    assert degraded["torque_nm"] > healthy["torque_nm"] * 1.4             # → OSF regime
    gap_h = healthy["process_temp_k"] - healthy["air_temp_k"]
    gap_d = degraded["process_temp_k"] - degraded["air_temp_k"]
    assert gap_d < gap_h  # heat-dissipation margin collapses


@needs_brain
def test_brain_scores_degraded_higher_than_healthy():
    predictor = get_failure_predictor()
    w = _world()
    w.env.run(until=60.0)
    healthy = w.stages[3].telemetry()
    w.stages[3].schedule_crack(eta_seconds=600.0)
    w.env.run(until=60.0 + 570.0)
    degraded = w.stages[3].telemetry()

    def _p(t: dict) -> dict:
        return predictor.predict_failure(
            type_=t["type_"], air_temp_k=t["air_temp_k"], process_temp_k=t["process_temp_k"],
            rot_speed_rpm=t["rot_speed_rpm"], torque_nm=t["torque_nm"], tool_wear_min=t["tool_wear_min"])

    p_healthy, p_degraded = _p(healthy), _p(degraded)
    assert p_degraded["p_fail"] > p_healthy["p_fail"]
    assert p_degraded["at_risk"] is True


@needs_brain
def test_slice_loop_emits_predictions_on_live_world():
    from services.slice_runner import SliceLoop
    from simulation.entities import Incident, InjectRequest

    w = _world(seed=2026)

    def inject(env):
        yield env.timeout(60.0)
        w._apply_incident(Incident.from_request(
            InjectRequest(type="machine_crack", target_id=3, details={}, severity="warning")))

    w.env.process(inject(w.env))
    loop = SliceLoop(w, sample_period_seconds=30.0)
    loop.start()
    w.env.run(until=900.0)
    assert loop.trail.counts()["predictions"] >= 1
    first = loop.trail.predictions[0].payload
    assert first["stage_id"] == 3
    assert first["prediction"]["at_risk"] is True
