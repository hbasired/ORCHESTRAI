"""Stage 21 (CTO #3 remediation) — runtime determinism regression test.

The durable LangGraph runtime relies on STRUCTURAL determinism (same incident in → same trajectory + decisions out);
today that is only indirectly tested. This pins it: two independent runs of the SAME incident (distinct thread_ids, so
each re-executes the full loop rather than resuming a checkpoint) must produce identical node trajectories AND identical
decision (kind, approved, rationale) tuples. A regression that injects nondeterminism (an RNG, wall-clock branch, dict
ordering) breaks this. Honest-skips when the runtime/predictor is unavailable.
"""
from __future__ import annotations

import pytest

from agents.runtime import run_incident
from ml.failure_predictor import get_failure_predictor


def _predictor_available() -> bool:
    try:
        return get_failure_predictor().is_available()
    except Exception:
        return False


needs_brain = pytest.mark.skipif(not _predictor_available(), reason="failure predictor unavailable (honest skip)")

_TELEM = {"stage_id": 3, "type_": "M", "air_temp_k": 301.0, "process_temp_k": 312.0,
          "rot_speed_rpm": 1300.0, "torque_nm": 68.0, "tool_wear_min": 240.0,
          "queue_depth": 5, "status": "degraded", "crack_proximity": 0.6}
_PLANT = {"available_crew": 1, "throughput_floor_frac": 0.5, "stages": {
    1: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
    3: {"status": "degraded", "at_risk": True, "crack_proximity": 0.6},
    5: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0}}}


def _incident():
    return {"type": "machine_crack", "target_id": 3, "capacity": 10, "telemetry": dict(_TELEM),
            "recent_incidents": [], "plant": _PLANT}


def _trajectory(out) -> list[str]:
    return [(t.get("node") if isinstance(t, dict) else getattr(t, "node", None)) for t in out.get("trace", [])]


def _decisions(out) -> list[tuple]:
    norm = []
    for d in out.get("decisions", []):
        d = d if isinstance(d, dict) else (d.model_dump() if hasattr(d, "model_dump") else {})
        norm.append((d.get("kind"), d.get("approved"), d.get("rationale")))
    return norm


@needs_brain
def test_same_incident_yields_identical_trajectory_and_decisions():
    out1 = run_incident(_incident(), thread_id="determinism-run-1", sil_level=0)
    out2 = run_incident(_incident(), thread_id="determinism-run-2", sil_level=0)

    traj1, traj2 = _trajectory(out1), _trajectory(out2)
    assert traj1 == traj2, f"non-deterministic trajectory:\n run1={traj1}\n run2={traj2}"
    assert traj1, "empty trajectory — runtime did not execute"

    dec1, dec2 = _decisions(out1), _decisions(out2)
    assert dec1 == dec2, f"non-deterministic decisions:\n run1={dec1}\n run2={dec2}"
