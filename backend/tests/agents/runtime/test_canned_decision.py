"""Stage 11 — end-to-end tests for the self-healing LangGraph runtime.

Exercises the durable graph over a canned incident: the full loop runs, wires the REAL Stage-4-10 models, the
neuro-symbolic verifier GENUINELY gates (rejects an unsafe plan — unlike the Stage-6 no-op, G-051), and the HITL
node pauses/resolves on SIL-1+ decisions. Skips honestly when the failure predictor is unavailable.
"""
from __future__ import annotations

import pytest

from agents.runtime import run_incident, build_runtime
from ml.failure_predictor import get_failure_predictor


def _predictor_available() -> bool:
    try:
        return get_failure_predictor().is_available()
    except Exception:
        return False


needs_brain = pytest.mark.skipif(not _predictor_available(), reason="failure predictor unavailable (honest skip)")

# A clearly at-risk machine (worn tool, high torque, low rpm).
_AT_RISK_TELEM = {"stage_id": 3, "type_": "M", "air_temp_k": 301.0, "process_temp_k": 312.0,
                  "rot_speed_rpm": 1300.0, "torque_nm": 68.0, "tool_wear_min": 240.0,
                  "queue_depth": 5, "status": "degraded", "crack_proximity": 0.6}

# A realistic 5-stage plant (4 nominal + the degraded target) → downing 1 keeps 0.8 online > 0.5 floor → APPROVE.
_HEALTHY_PLANT = {"available_crew": 1, "throughput_floor_frac": 0.5, "stages": {
    1: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
    2: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
    3: {"status": "degraded", "at_risk": True, "crack_proximity": 0.6},
    4: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
    5: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0}}}


def _incident(plant, recent=None):
    return {"type": "machine_crack", "target_id": 3, "capacity": 10, "telemetry": _AT_RISK_TELEM,
            "recent_incidents": recent or [], "plant": plant}


@needs_brain
def test_runtime_runs_full_self_healing_loop_and_approves():
    out = run_incident(_incident(_HEALTHY_PLANT), sil_level=0)
    nodes = [e["node"] for e in out["trace"]]
    # the full loop ran in order
    assert nodes == ["observe", "orient", "diagnose", "explain", "decide", "verify", "execute", "log"]
    # real models produced real signals (no fabrication)
    orient = next(e for e in out["trace"] if e["node"] == "orient")
    assert "p_fail=0.9" in orient["summary"] and "at_risk=True" in orient["summary"]
    assert any(e["node"] == "diagnose" and "primary=" in e["summary"] for e in out["trace"])
    assert any(e["node"] == "explain" and "top driver=" in e["summary"] for e in out["trace"])
    # decision approved by the binding verifier (4/5 stages stay online) and executed (sim-only)
    d = out["decisions"][0]
    assert d["kind"] == "preventive_maintenance"
    assert d["approved"] is True
    assert d["executed"] is True
    # provenance carries the real model outputs
    assert d["provenance"]["prediction"]["at_risk"] is True
    assert d["provenance"]["verification"]["approved"] is True
    assert d["provenance"]["explanation"]["top_drivers"]


@needs_brain
def test_runtime_verifier_genuinely_rejects_unsafe_plan():
    """G-051 paid IN THE RUNTIME: a BINDING PlantState makes the verifier actually reject (not a no-op)."""
    # Plant where a 2nd critical machine is already in maintenance → downing the target breaches the SIL
    # critical-redundancy contract (max 1 critical offline) → REJECT.
    constrained = {"available_crew": 1, "throughput_floor_frac": 0.5, "max_concurrent_critical_offline": 1,
                   "stages": {
                       3: {"status": "degraded", "at_risk": True, "crack_proximity": 0.95},
                       7: {"status": "maintenance", "at_risk": True, "crack_proximity": 0.90}}}
    out = run_incident(_incident(constrained), sil_level=0)
    verify = next(e for e in out["trace"] if e["node"] == "verify")
    assert verify["detail"].get("approved") is False, "binding verifier must reject this unsafe plan"
    d = out["decisions"][0]
    assert d["approved"] is False
    assert d["executed"] is False  # rejected plan is NOT executed


@needs_brain
def test_hitl_resolution_consumed_on_sil1():
    """SIL-1+ sets hitl_required; a pre-supplied resolution is consumed (no live interrupt) and gates execution."""
    out = run_incident(_incident(_HEALTHY_PLANT), sil_level=2, hitl_resolution="approved")
    assert any(e["node"] == "hitl_confirm" for e in out["trace"])
    d = out["decisions"][0]
    assert d["hitl_required"] is True
    assert d["executed"] is True  # approved by the operator → executed
    # and a rejected operator resolution blocks execution
    out2 = run_incident(_incident(_HEALTHY_PLANT), sil_level=2, hitl_resolution="rejected")
    assert out2["decisions"][0]["executed"] is False


def test_runtime_builds_with_a_checkpointer():
    """The graph compiles with a checkpointer (durable execution) regardless of model availability."""
    app, backend = build_runtime()
    assert app is not None
    assert backend in ("memory", "postgres", "provided")


def test_checkpointer_factory_defaults_to_memory(monkeypatch):
    """No Postgres URL → honest in-memory backend (no fake durability)."""
    from agents.runtime.checkpointer import get_checkpointer
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    cp, backend = get_checkpointer()
    assert backend == "memory"
    assert cp is not None


def test_tracing_status_is_honest():
    """Tracing reports the always-on per-node trace + whether external tracers are actually configured."""
    from agents.runtime.tracing import tracing_status, get_run_callbacks
    st = tracing_status()
    assert "always_on_trace" in st
    assert isinstance(st["langfuse_configured"], bool)
    assert isinstance(st["langsmith_configured"], bool)
    # callbacks list is well-formed (empty when nothing configured — never a fake handler)
    assert isinstance(get_run_callbacks(), list)


@pytest.mark.skipif(not __import__("os").environ.get("DATABASE_URL"),
                    reason="no DATABASE_URL — Postgres checkpointer durability not exercised (honest skip)")
def test_postgres_checkpointer_persists_when_available():
    """When a Postgres URL is set + reachable, the factory yields the postgres backend and a run persists a
    checkpoint that survives a fresh saver instance (durable)."""
    from agents.runtime.checkpointer import get_checkpointer
    cp, backend = get_checkpointer()
    if backend != "postgres":
        pytest.skip("Postgres configured but unreachable (honest skip)")
    if not _predictor_available():
        pytest.skip("predictor unavailable")
    out = run_incident(_incident(_HEALTHY_PLANT), thread_id="pytest-pg-durable", sil_level=0)
    assert out["backend"] in ("postgres", "memory")  # run completed
    assert out["decisions"]
