"""Stage 6 — diagnose v0 unit tests (AC2): deterministic root-cause ranking.

Pure-function tests: no model, no sim, no I/O. Telemetry dicts are constructed
to land in (or out of) the AI4I failure-mode regimes the rules encode.
"""
from __future__ import annotations

import math

from services.diagnosis import (
    EXTERNAL_POWER_EVENT,
    HEAT_DISSIPATION,
    NO_FAULT_FOUND,
    OVERSTRAIN,
    POWER_ANOMALY,
    WEAR_BREACH,
    diagnose,
)


def _telemetry(**overrides) -> dict:
    base = {
        "stage_id": 3,
        "name": "machining",
        "sim_time_seconds": 1000.0,
        "status": "degraded",
        "type_": "M",
        "air_temp_k": 300.0,
        "process_temp_k": 310.0,   # gap = 10 K (HDF-safe unless overridden)
        "rot_speed_rpm": 1500.0,
        "torque_nm": 40.0,         # power ≈ 6283 W (PWF-safe band)
        "tool_wear_min": 50.0,
        "queue_depth": 5,
        "crack_proximity": 0.5,
    }
    base.update(overrides)
    return base


def _prediction(p_fail: float, at_risk: bool, threshold: float = 0.779) -> dict:
    return {"p_fail": p_fail, "at_risk": at_risk, "threshold": threshold,
            "arch": "XGBoost", "dataset": "AI4I 2020"}


def test_not_at_risk_returns_no_fault_monitor():
    d = diagnose(_prediction(0.05, False), _telemetry())
    assert d.at_risk is False
    assert d.primary.cause == NO_FAULT_FOUND
    assert d.primary.recommended_action == "monitor"


def test_wear_breach_primary_when_wear_in_twf_band():
    d = diagnose(_prediction(0.95, True), _telemetry(tool_wear_min=220.0, torque_nm=20.0))
    assert d.at_risk is True
    assert d.primary.cause == WEAR_BREACH
    assert d.primary.recommended_action == "preventive_maintenance"
    assert any("tool_wear" in e for e in d.primary.evidence)


def test_overstrain_fires_on_wear_torque_product():
    # wear 150 (< TWF 0.8*200=160) so wear_breach stays quiet; 150×80 = 12,000 minNm > OSF.
    d = diagnose(_prediction(0.9, True), _telemetry(tool_wear_min=150.0, torque_nm=80.0))
    causes = [h.cause for h in d.hypotheses]
    assert OVERSTRAIN in causes
    assert d.primary.cause == OVERSTRAIN


def test_heat_dissipation_fires_on_collapsed_gap_and_low_rpm():
    d = diagnose(
        _prediction(0.9, True),
        _telemetry(process_temp_k=304.0, air_temp_k=299.0, rot_speed_rpm=1200.0, torque_nm=45.0),
    )
    assert d.primary.cause == HEAT_DISSIPATION
    assert any("rpm" in e for e in d.primary.evidence)


def test_power_anomaly_local_when_no_power_dip_incident():
    # torque 10 Nm @ 1000 rpm → power ≈ 1047 W < 3500 W; temp gap kept HDF-safe.
    t = _telemetry(torque_nm=10.0, rot_speed_rpm=1000.0, process_temp_k=312.0)
    assert t["rot_speed_rpm"] < 1380.0 and (t["process_temp_k"] - t["air_temp_k"]) > 8.6
    d = diagnose(_prediction(0.85, True), t, recent_incidents=[])
    assert d.primary.cause == POWER_ANOMALY


def test_external_power_event_attributed_when_power_dip_active():
    t = _telemetry(torque_nm=10.0, rot_speed_rpm=1000.0, process_temp_k=312.0)
    d = diagnose(_prediction(0.85, True), t, recent_incidents=[{"type": "power_dip", "target_id": None}])
    assert d.primary.cause == EXTERNAL_POWER_EVENT
    assert d.primary.recommended_action == "wait_for_power_recovery"


def test_at_risk_with_no_rule_reports_no_fault_found_honestly():
    d = diagnose(_prediction(0.85, True), _telemetry())  # all signals in healthy bands
    assert d.primary.cause == NO_FAULT_FOUND
    assert d.primary.recommended_action == "preventive_maintenance_on_model_signal"
    # The evidence states the mismatch instead of inventing a cause.
    assert any("no AI4I rule threshold met" in e for e in d.primary.evidence)


def test_determinism_same_input_same_output():
    pred, tel = _prediction(0.92, True), _telemetry(tool_wear_min=230.0)
    a, b = diagnose(pred, tel), diagnose(pred, tel)
    assert a.to_dict() == b.to_dict()


def test_power_helper_matches_ai4i_definition():
    # power = torque · ω = torque · rpm · 2π/60 — same formula the brain's features use.
    t = _telemetry(torque_nm=40.0, rot_speed_rpm=1500.0)
    expected = 40.0 * 1500.0 * 2.0 * math.pi / 60.0
    d = diagnose(_prediction(0.9, True), t)
    assert d.at_risk  # construction sanity; power in-band so no PWF hypothesis
    assert all(h.cause != POWER_ANOMALY for h in d.hypotheses)
    assert 6200.0 < expected < 6400.0
