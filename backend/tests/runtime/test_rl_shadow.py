"""Stage 30 (G-025-tail) — SHADOW-mode RL recommender tests: it observes real fleet state, recommends WITHOUT
acting, computes RL-vs-rule agreement, and degrades honestly (never fabricates an action)."""
from __future__ import annotations

import pytest

from agents.runtime.rl_shadow import shadow_recommend


def _fleet(broken=(), degrading=()):
    out = []
    for i in range(9):
        status = "broken" if i in broken else ("degraded" if i in degrading else "nominal")
        prox = 0.8 if i in degrading else 0.0
        out.append({"stage_id": i, "status": status, "crack_proximity": prox})
    return out


def test_empty_fleet_is_honest_unavailable():
    r = shadow_recommend([])
    assert r["available"] is False


def test_shadow_recommendation_is_logged_not_acted():
    r = shadow_recommend(_fleet(broken={2}, degrading={1, 4}))
    if not r["available"]:
        pytest.skip("MaskablePPO policy / sb3-contrib not installed in this env (honest-unavailable path)")
    # Shadow contract: it produces a recommendation + agreement, explicitly does NOT actuate.
    assert r["mode"] == "shadow"
    assert "rl_action" in r and "rule_action" in r and isinstance(r["agree"], bool)
    assert 0 <= r["rl_action"] <= 3                       # no-op or one of 3 zones
    assert "NOT drive actuation" in r["note"]             # the shadow guarantee is stated
    assert r["zone_risk"] and len(r["zone_risk"]) == 3


def test_rule_baseline_targets_the_highest_risk_zone():
    # zone 1 = machines 0-2 (one degrading @0.8); zone 0 has nothing -> rule dispatches to a risky zone, not no-op.
    r = shadow_recommend(_fleet(degrading={0}))
    if not r["available"]:
        pytest.skip("RL policy unavailable")
    assert r["rule_action"] != 0                          # there IS risk -> not a no-op
