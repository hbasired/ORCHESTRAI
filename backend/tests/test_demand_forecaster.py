"""Stage 5 — tests for the demand forecaster (honest-unavailable contract + real inference when torch present)."""
import pytest

from ml.demand_forecaster import DemandForecaster, ModelUnavailableError, get_demand_forecaster


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except Exception:
        return False


def test_raises_when_brain_absent_never_fabricates(tmp_path):
    f = DemandForecaster(models_dir=tmp_path)
    assert f.is_available() is False
    with pytest.raises(ModelUnavailableError):
        f.forecast([{"cnt": 100} for _ in range(48)])


@pytest.mark.skipif(not _torch_available(), reason="torch not installed (LSTM inference needs torch)")
def test_real_forecast_when_available():
    f = get_demand_forecaster()
    if not f.is_available():
        pytest.skip("demand brain not present in models/")
    hist = [{"cnt": 100 + (i % 50), "temp": 0.5, "atemp": 0.5, "hum": 0.6, "windspeed": 0.2,
             "hr": i % 24, "weekday": (i // 24) % 7, "mnth": 6, "workingday": 1,
             "holiday": 0, "weathersit": 1, "season": 2} for i in range(48)]
    out = f.forecast(hist)
    assert "forecast" in out and out["forecast"] >= 0.0
