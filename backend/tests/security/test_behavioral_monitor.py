"""Stage 31 (G-064-tail) — continuous behavioural anomaly monitor tests: robust-Z spikes, trajectory anomalies,
honest insufficient-history, and no false alarm on a stable baseline. Pure computation — no DB, no model, no network."""
from __future__ import annotations

from security.behavioral_monitor import BehavioralMonitor

_NORMAL = {"decision_count": 2, "tool_calls": 3, "actuation_attempts": 1, "verifier_rejections": 0,
           "node_revisits": 0, "duration_s": 1.5}


def _warm(m, n=12):
    for _ in range(n):
        m.observe(dict(_NORMAL))


def test_insufficient_history_before_warmup():
    m = BehavioralMonitor(audit=False)
    v = m.observe(dict(_NORMAL))
    assert v.insufficient_history is True
    assert v.anomalous is False


def test_stable_baseline_is_not_flagged():
    m = BehavioralMonitor(audit=False)
    _warm(m)
    v = m.observe(dict(_NORMAL))                 # identical to the baseline
    assert v.anomalous is False and v.insufficient_history is False


def test_robust_z_spike_is_flagged():
    m = BehavioralMonitor(audit=False)
    _warm(m)
    v = m.observe({**_NORMAL, "tool_calls": 40})  # a 13x tool-call explosion
    assert v.anomalous is True
    assert any("tool_calls" in r for r in v.reasons)


def test_trajectory_loop_flagged_even_without_warmup():
    m = BehavioralMonitor(audit=False)
    v = m.observe({**_NORMAL, "node_revisits": 5})   # loop — an absolute trajectory check, not baseline-relative
    assert v.anomalous is True
    assert any("loop" in r for r in v.reasons)


def test_redundant_actions_and_invalid_tool_args_flagged():
    m = BehavioralMonitor(audit=False)
    assert m.observe({**_NORMAL, "redundant_actions": 3}).anomalous is True
    assert m.observe({**_NORMAL, "invalid_tool_args": 2}).anomalous is True


def test_actuation_exceeding_decisions_flagged():
    m = BehavioralMonitor(audit=False)
    v = m.observe({**_NORMAL, "actuation_attempts": 6, "decision_count": 2})
    assert v.anomalous is True
    assert any("actuation_attempts exceed" in r for r in v.reasons)


def test_features_from_a_real_run_incident_result():
    """The monitor consumes REAL runtime output: a run_incident-shaped result maps to the monitored features,
    and a looping trace (repeated nodes) surfaces node_revisits."""
    from security.behavioral_monitor import features_from_run
    result = {
        "decisions": [{"kind": "preventive_maintenance", "executed": True}],
        "trace": [{"node": "observe", "ok": True}, {"node": "predict", "ok": True},
                  {"node": "predict", "ok": True}, {"node": "decide", "ok": False}],  # 'predict' revisited + a rejection
        "audit_seqs": [101, 102], "duration_s": 2.0,
    }
    f = features_from_run(result)
    assert f["decision_count"] == 1
    assert f["actuation_attempts"] == 1
    assert f["node_revisits"] == 1          # 'predict' appears twice
    assert f["verifier_rejections"] == 1    # the ok=False trace event
    assert f["duration_s"] == 2.0
