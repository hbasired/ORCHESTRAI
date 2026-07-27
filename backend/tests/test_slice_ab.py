"""Stage 6 — A/B harness smoke test (AC4).

Verifies the experiment runs both arms and reports the measured fields. It
deliberately does NOT assert that ON beats OFF — the delta is reported, never
asserted (honesty rule). Skips honestly when the brain is absent.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ml.failure_predictor import get_failure_predictor

BRAIN_AVAILABLE = get_failure_predictor().is_available()
needs_brain = pytest.mark.skipif(not BRAIN_AVAILABLE, reason="trained Stage-4 brain unavailable (honest skip)")


@needs_brain
def test_run_arm_reports_measured_fields():
    from run_slice_ab import run_arm

    m = run_arm(seed=42, sim_hours=1.0, loop_on=False, campaign=((10.0, 3),))
    for key in ("orders_complete", "throughput_units_per_hour", "unplanned_downtime_min",
                "planned_maintenance_min", "total_downtime_min", "breakdowns",
                "crack_breakdowns", "planned_maintenances", "cracks_injected"):
        assert key in m
        assert math.isfinite(float(m[key]))
    assert m["arm"] == "off"
    assert m["cracks_injected"] == 1


@needs_brain
def test_experiment_pairs_arms_on_same_seed():
    from run_slice_ab import run_experiment

    summary = run_experiment([42], sim_hours=1.0)
    assert summary["seeds"] == [42]
    assert len(summary["pairs"]) == 1
    pair = summary["pairs"][0]
    assert pair["off"]["arm"] == "off" and pair["on"]["arm"] == "on"
    assert pair["off"]["seed"] == pair["on"]["seed"] == 42
    # The ON arm carries the slice provenance trail.
    assert "slice_trail" in pair["on"]
    # The measured delta is REPORTED (sign not asserted — honesty rule).
    d = summary["measured_delta"]
    assert set(d) >= {"unplanned_downtime_min", "total_downtime_min", "throughput_units_per_hour"}
    assert math.isfinite(d["unplanned_downtime_min"])


@needs_brain
def test_arms_are_deterministic_per_seed():
    from run_slice_ab import run_arm

    a = run_arm(seed=99, sim_hours=0.5, loop_on=False, campaign=((5.0, 2),))
    b = run_arm(seed=99, sim_hours=0.5, loop_on=False, campaign=((5.0, 2),))
    assert a == b
