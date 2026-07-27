"""Stage 30 (G-036) — demand-forecast-service tests: real serving path + honest labelled baseline (NO fabricated
confidence). The legacy placeholder's synthetic per-day `confidence` is gone."""
from __future__ import annotations

from services.demand_forecast_service import seven_day_forecast


def _schema_history(n=24):
    return [{"cnt": 200 + i, "temp": 0.5, "atemp": 0.48, "hum": 0.6, "windspeed": 0.2, "hr": i % 24,
             "weekday": 3, "month": 6, "workingday": 1, "holiday": 0, "weathersit": 1, "season": 2} for i in range(n)]


def test_baseline_is_honest_and_carries_no_fabricated_confidence():
    r = seven_day_forecast()                       # no real feed
    assert r["served"] is False
    assert r["source"] == "deterministic_planning_baseline"
    assert r["horizon_days"] == 7 and len(r["forecast"]) == 7
    for day in r["forecast"]:
        assert "confidence" not in day             # the fabricated synthetic constant is GONE (Rule 1a)
        assert day["lower_bound"] is None and day["upper_bound"] is None   # honest: no invented bounds
        assert "planning baseline" in day["basis"]
    assert "G-035" in r["note"]                     # discloses the real-data dependency


def test_empirical_path_serves_from_observed_daily():
    r = seven_day_forecast(observed_daily=[980, 1010, 1005, 990, 1020])
    assert r["served"] is True
    assert r["source"].startswith("empirical")
    d0 = r["forecast"][0]
    assert d0["lower_bound"] < d0["predicted_demand"] < d0["upper_bound"]   # real mean±std band


def test_lstm_serving_path_when_model_present():
    """If the trained LSTM loads, a schema-compatible history yields a real model-sourced forecast; else it degrades
    honestly to the baseline (never fabricates)."""
    r = seven_day_forecast(hourly_history=_schema_history())
    if r["served"]:
        assert "demand_forecaster" in r["source"] or "LSTM" in r["source"]
        d0 = r["forecast"][0]
        assert d0["predicted_demand"] > 0
        assert d0["lower_bound"] < d0["predicted_demand"] < d0["upper_bound"]   # MAE-derived band
    else:
        # model absent in this env -> honest baseline, not a fabricated forecast
        assert r["source"] == "deterministic_planning_baseline"


def test_state_manager_surfaces_forecast_provenance():
    """The operator-facing supply-chain state now carries the forecast SOURCE + served flag (no silent placeholder)."""
    from services.state_manager import StateManager
    sc = StateManager()._create_initial_supply_chain()
    assert "demand_forecast_source" in sc and "demand_forecast_served" in sc
    for day in sc["demand_forecast"]:
        assert "confidence" not in day             # the legacy fabricated confidence is gone from the live state
