"""Stage 30 (G-025-tail) — SHADOW-mode RL intervention recommender (research §41.2).

The Stage-7 MaskablePPO policy genuinely beat the hand-coded rule on the group/opportunistic maintenance MDP, but it
was never consulted by the live runtime. The SOTA deployment protocol for a sim-trained policy is **shadow mode
first**: run inference on live data, LOG the recommendation, and DO NOT act — so we measure RL-vs-rule agreement on
real states before ever trusting it. The existing neuro-symbolic verifier + safety validator remain the shield
(post-decision), and promotion shadow→active is gated by the Stage-28 progressive-autonomy ladder + HITL.

Honesty:
 * The policy was trained on the FLEET-scheduling distribution (which zone to batch-maintain), so this builds the
   group-env observation FROM REAL fleet signals (degrading / crack-proximity / broken) — its own distribution — NOT
   the single-incident runtime state. It maps the real stages into the model's 9-machine / 3-zone layout (disclosed).
 * It NEVER actuates and NEVER fabricates: SB3/policy absent → `available=False` (honest), never a made-up action.
"""
from __future__ import annotations

import os
from typing import Any, Optional

# The trained group-env geometry (must match training/stage_07_rl_intervention/group_env.py:GroupEnvConfig).
_N_ZONES = 3
_MACHINES_PER_ZONE = 3
_N_MACHINES = _N_ZONES * _MACHINES_PER_ZONE       # 9
_ETA_MAX = 70.0


def shadow_enabled() -> bool:
    return os.environ.get("RUNTIME_RL_SHADOW", "0") == "1"


def _machine_features(stage: dict[str, Any]) -> tuple[float, float, float]:
    """(degrading, eta_norm, broken) for one machine from REAL stage signals."""
    status = str(stage.get("status", "")).lower()
    prox = float(stage.get("crack_proximity", 0.0))
    degrading = 1.0 if (status == "degraded" or bool(stage.get("at_risk")) or prox > 0.0) else 0.0
    broken = 1.0 if status == "broken" else 0.0
    # eta_norm: 1.0 = far from failure, →0 as the crack approaches (proximity→1). Healthy machines report 1.0.
    eta_norm = max(0.0, min(1.0, 1.0 - prox)) if degrading else 1.0
    return degrading, eta_norm, broken


def _build_obs(fleet: list[dict[str, Any]]):
    """Construct the 30-dim group-env observation from real fleet state (most-at-risk first into the 9 slots)."""
    import numpy as np
    ranked = sorted(fleet, key=lambda s: float(s.get("crack_proximity", 0.0))
                    + (1.0 if str(s.get("status", "")).lower() == "broken" else 0.0), reverse=True)
    slots = ranked[:_N_MACHINES]
    per = []
    zone_risk = [0.0] * _N_ZONES
    for i in range(_N_MACHINES):
        if i < len(slots):
            deg, eta_norm, broken = _machine_features(slots[i])
        else:
            deg, eta_norm, broken = 0.0, 1.0, 0.0     # pad healthy (disclosed) when fewer than 9 real machines
        per.extend([deg, eta_norm, broken])
        zone = i // _MACHINES_PER_ZONE
        zone_risk[zone] += (1.0 - eta_norm) + broken
    tail = [0.0, 1.0, 0.0]     # crew free, neutral demand, fresh decision — a single-shot recommendation
    obs = np.array(per + tail, dtype=np.float32)
    return obs, zone_risk, slots


def _rule_action(zone_risk: list[float]) -> int:
    """The hand-coded baseline: dispatch to the highest-risk zone if any risk exists, else no-op (action 0)."""
    if max(zone_risk, default=0.0) <= 0.0:
        return 0
    return 1 + max(range(_N_ZONES), key=lambda z: zone_risk[z])


def shadow_recommend(fleet: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the RL policy in SHADOW over a real fleet snapshot; compare to the rule. Never acts. Honest-unavailable."""
    if not fleet:
        return {"available": False, "reason": "no fleet snapshot to observe"}
    try:
        from ml.group_scheduler_rl import GroupSchedulerRL
        from ml.failure_predictor import ModelUnavailableError
        rl = GroupSchedulerRL()
        if not rl.is_available():
            return {"available": False, "reason": "MaskablePPO policy / sb3-contrib unavailable (honest — no action invented)"}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"RL substrate unavailable: {e}"}

    import numpy as np
    obs, zone_risk, slots = _build_obs(fleet)
    action_masks = np.ones(_N_ZONES + 1, dtype=bool)   # all actions valid for a single-shot recommendation
    try:
        rl_action = int(rl.act(obs, action_masks=action_masks))
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"RL inference failed: {e}"}

    rule_action = _rule_action(zone_risk)

    def _describe(a: int) -> str:
        return "no-op (hold)" if a == 0 else f"batch-maintain zone {a} (machines {[i for i in range((a-1)*_MACHINES_PER_ZONE, a*_MACHINES_PER_ZONE)]})"

    return {
        "available": True, "mode": "shadow",         # LOGGED, NOT ACTED
        "rl_action": rl_action, "rl_recommendation": _describe(rl_action),
        "rule_action": rule_action, "rule_recommendation": _describe(rule_action),
        "agree": rl_action == rule_action,
        "zone_risk": [round(z, 3) for z in zone_risk],
        "n_observed_machines": len(slots),
        "note": "SHADOW mode (§41.2): the RL recommendation is logged for RL-vs-rule agreement measurement and does "
                "NOT drive actuation; the safety verifier/validator remains the shield; promotion is autonomy-ladder + HITL gated.",
    }


__all__ = ["shadow_enabled", "shadow_recommend"]
