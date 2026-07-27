"""Stage 8B — learned causal discovery (PC) tests.

Verifies that the PC algorithm, run on SimWorld telemetry, recovers crack_proximity as the
common-cause HUB (the robust, sample-size-stable invariant) — empirically supporting the known-SCM
assumption that `services.diagnosis.attribute_cause` relies on. The headline skeleton-F1 / 4-of-5-hub
numbers live in the committed canonical report (100 seeds); this test re-derives the robust invariant
on a small seed set and checks the report when present.
"""
from __future__ import annotations

from ml.causal_discovery import discover_and_validate, load_report, VARS


def test_pc_recovers_proximity_as_common_cause_hub():
    # Small but sufficient seed set; the hub property is stable across sample sizes.
    r = discover_and_validate(seeds=range(500, 524), persist=False)
    assert r["n_samples"] > 100
    assert set(r["variables"]) == set(VARS)
    # Robust invariant: crack_proximity is the highest-degree node (the common cause).
    assert r["proximity_is_max_degree_hub"] is True
    assert r["proximity_hub_n"] >= 2, f"proximity should be adjacent to >=2 sensors, got {r['proximity_hub_n']}"
    # The degree of crack_proximity is the max across all variables.
    deg = r["node_degrees"]
    assert deg["crack_proximity"] == max(deg.values())


def test_canonical_report_supports_known_scm():
    rep = load_report()
    if rep is None:
        import pytest
        pytest.skip("canonical PC-discovery report not generated yet (run discover_and_validate)")
    # The committed 100-seed run: strong skeleton F1 + 4-of-5 hub recovery + verdict True.
    assert rep["skeleton_metrics"]["f1"] >= 0.6
    assert rep["proximity_hub_n"] >= 3
    assert rep["proximity_is_max_degree_hub"] is True
    assert rep["supports_known_scm"] is True
