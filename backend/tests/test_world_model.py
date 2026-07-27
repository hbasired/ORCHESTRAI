"""Stage 8 — world-model (TTF) + causal-attribution tests.

The TTF tests need the trained weights (`models/world_model_ttf.pt`) and skip honestly when absent.
The causal-attribution + honest-unavailable tests need neither weights nor xgboost.
"""
from __future__ import annotations

import numpy as np
import pytest

from ml.world_model import FEATURES, ModelUnavailableError, WorldModel, get_world_model


def _weights_available() -> bool:
    return get_world_model().is_available()


needs_weights = pytest.mark.skipif(not _weights_available(),
                                   reason="trained world model unavailable (honest skip)")


# ---- honest unavailability (no weights/torch needed) ------------------------

def test_world_model_honest_unavailable(tmp_path):
    wm = WorldModel(weights_path=tmp_path / "missing.pt")
    assert wm.is_available() is False
    with pytest.raises(ModelUnavailableError):
        wm.predict_ttf(np.zeros((6, len(FEATURES)), dtype=np.float32))


def test_world_model_window_validation():
    wm = WorldModel()
    if not wm.is_available():
        pytest.skip("weights absent")
    with pytest.raises(ValueError):
        wm.predict_ttf(np.zeros((6, 3), dtype=np.float32))  # wrong feature count


# ---- TTF forecasting (needs weights) ----------------------------------------

@needs_weights
def test_predict_ttf_on_real_rollout_is_accurate():
    from training.stage_08_world_model.rollouts import RolloutConfig, build_dataset
    X, y = build_dataset([61], RolloutConfig())
    assert len(X) > 0
    wm = get_world_model()
    errs = [abs(wm.predict_ttf(X[i])["ttf_minutes"] - float(y[i])) for i in range(min(40, len(X)))]
    mae = float(np.mean(errs))
    # Naive baseline MAE on this slice ~ mean-abs-deviation of TTF (several minutes); learned must beat it.
    naive = float(np.mean(np.abs(y[:min(40, len(y))] - y[:min(40, len(y))].mean())))
    assert mae < naive, f"learned MAE {mae:.2f} should beat naive {naive:.2f}"
    assert mae < 1.5, f"learned TTF MAE should be well under 1.5 min, got {mae:.2f}"


@needs_weights
def test_predict_ttf_accepts_dicts():
    wm = get_world_model()
    window = [{f: v for f, v in zip(FEATURES, [300.0, 309.0, 1500.0, 42.0, 30.0])} for _ in range(6)]
    out = wm.predict_ttf(window)
    assert out["ttf_minutes"] >= 0.0
    assert out["window_len"] == 6


# ---- causal attribution v1 (no weights needed) ------------------------------

def _telemetry(**ov):
    base = {"stage_id": 3, "name": "machining", "sim_time_seconds": 0.0, "status": "degraded",
            "type_": "M", "air_temp_k": 300.0, "process_temp_k": 310.0, "rot_speed_rpm": 1500.0,
            "torque_nm": 40.0, "tool_wear_min": 50.0, "queue_depth": 5, "crack_proximity": 0.5}
    base.update(ov); return base


def _pred(p, risk):
    return {"p_fail": p, "at_risk": risk, "threshold": 0.779, "arch": "XGBoost", "dataset": "AI4I"}


def test_attribution_machine_local_when_intrinsic_wear():
    from services.diagnosis import diagnose, MACHINE_LOCAL
    d = diagnose(_pred(0.95, True), _telemetry(tool_wear_min=225.0))
    ca = d.causal_attribution
    assert ca["attribution"] == MACHINE_LOCAL
    assert ca["intrinsic_fault_confirmed"] is True


def test_attribution_rules_out_coincident_external_incident():
    from services.diagnosis import diagnose, MACHINE_LOCAL
    # Genuine intrinsic wear AND a co-occurring power_dip → must stay machine_local (confounder ruled out).
    d = diagnose(_pred(0.95, True), _telemetry(tool_wear_min=225.0),
                 recent_incidents=[{"type": "power_dip"}])
    ca = d.causal_attribution
    assert ca["attribution"] == MACHINE_LOCAL
    assert "power_dip" in ca["confounders_considered"]
    assert ca["intrinsic_fault_confirmed"] is True


def test_attribution_externally_influenced_on_power_event():
    from services.diagnosis import diagnose, EXTERNALLY_INFLUENCED
    # power out-of-band + active power_dip → external_power_event primary → externally_influenced.
    t = _telemetry(torque_nm=10.0, rot_speed_rpm=1000.0, process_temp_k=312.0)
    d = diagnose(_pred(0.85, True), t, recent_incidents=[{"type": "power_dip"}])
    ca = d.causal_attribution
    assert ca["attribution"] == EXTERNALLY_INFLUENCED
    assert ca["intrinsic_fault_confirmed"] is False


def test_attribution_present_in_to_dict():
    from services.diagnosis import diagnose
    d = diagnose(_pred(0.95, True), _telemetry(tool_wear_min=225.0))
    assert "causal_attribution" in d.to_dict()
    assert d.to_dict()["causal_attribution"]["method"].startswith("do-operator")
