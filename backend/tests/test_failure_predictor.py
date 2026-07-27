"""Stage 4 — tests for the failure-risk predictor.

Verifies (a) the honest "no brain / no torch -> raise, never fabricate" contract (runs everywhere), and
(b) real inference when torch + the trained brain are present (skipped otherwise).
"""
import pytest

from ml.failure_predictor import FailurePredictor, ModelUnavailableError, get_failure_predictor


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except Exception:
        return False


def test_raises_when_brain_absent_never_fabricates(tmp_path):
    # Pointing at an empty dir => no brain => must raise, NOT return a made-up probability.
    p = FailurePredictor(models_dir=tmp_path)
    assert p.is_available() is False
    with pytest.raises(ModelUnavailableError):
        p.predict_failure(air_temp_k=300.0, process_temp_k=310.0, rot_speed_rpm=1500,
                          torque_nm=40.0, tool_wear_min=100.0)


@pytest.mark.skipif(not _torch_available(), reason="torch not installed (brain inference needs torch)")
def test_real_brain_inference_when_available():
    p = get_failure_predictor()
    if not p.is_available():
        pytest.skip("trained brain not present in models/ (run the Colab notebook first)")
    out = p.predict_failure(type_="L", air_temp_k=300.0, process_temp_k=312.0,
                            rot_speed_rpm=1380, torque_nm=65.0, tool_wear_min=210.0)
    assert {"p_fail", "at_risk", "threshold"} <= set(out)
    assert 0.0 <= out["p_fail"] <= 1.0
    assert isinstance(out["at_risk"], bool)
