"""Stage 7 — RL intervention policy inference glue (INTERVENE step, KB_25).

Loads the PPO policy trained by `backend/training/stage_07_rl_intervention/` and
exposes a fleet-level chooser: given the per-machine observation, decide which
(if any) at-risk machine the single maintenance crew should service. The learned
net is wrapped by a HARD SAFETY SHIELD (ml-engineer mandate: "no policy that
allows known-unsafe actions even at low probability") — if a machine's risk is
at/above the critical threshold and the crew is free, maintenance is FORCED on
the highest-risk machine regardless of what the stochastic net sampled.

Honesty (Stage 7 finding): at v0 scope the rule-based chooser is near-optimal and
PPO does not beat it (see `models/rl_intervention_policy.metrics.json`). The rules
therefore remain the DEFAULT chooser; this RL policy ships as the trained,
safety-shielded, learnable substrate for Stage 8's richer recovery action space.
Like every brain in this repo it is honest about unavailability — it raises
`ModelUnavailableError` and NEVER fabricates an action.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from ml.failure_predictor import ModelUnavailableError  # reuse the honest-unavailable contract

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_WEIGHTS = _MODELS_DIR / "rl_intervention_policy.pt"

# Mirror the env constants (kept in sync; the env is the source of truth).
N_STAGES = 10
FEATURES_PER_STAGE = 5
OBS_DIM = N_STAGES * FEATURES_PER_STAGE + 1
ACT_DIM = N_STAGES + 1
CRITICAL_PROXIMITY = 0.85
AT_RISK_THRESHOLD = 0.30


def _safety_shield(obs: np.ndarray, action: int, critical: float = CRITICAL_PROXIMITY) -> tuple[int, bool]:
    """If the crew is free and some at-risk machine's risk >= critical, FORCE
    maintenance on the highest-risk one. Returns (action, shield_fired)."""
    crew_free = obs[-1] > 0.5
    if not crew_free:
        return action, False
    best_sid, best_risk = None, -1.0
    for sid in range(N_STAGES):
        base = sid * FEATURES_PER_STAGE
        if obs[base] > 0.5 and obs[base + 1] > best_risk:   # at_risk flag, risk score
            best_risk = obs[base + 1]
            best_sid = sid
    if best_sid is not None and best_risk >= critical:
        forced = best_sid + 1
        return forced, (forced != action)
    return action, False


class RLInterventionPolicy:
    """Fleet-level PPO chooser + safety shield. Honest about unavailability."""

    def __init__(self, weights_path: Optional[Path] = None) -> None:
        self._path = Path(weights_path) if weights_path else _WEIGHTS
        self._net = None
        self._torch = None

    def is_available(self) -> bool:
        try:
            self._load()
            return True
        except ModelUnavailableError:
            return False

    def _load(self) -> None:
        if self._net is not None:
            return
        try:
            import torch  # noqa: F401
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"PyTorch not available: {e}")
        if not self._path.exists():
            raise ModelUnavailableError(
                f"trained PPO policy not found: {self._path} — run "
                f"backend/training/stage_07_rl_intervention/train.py"
            )
        # Local import keeps this module import-safe without the training package on sys.path.
        import sys
        backend_root = Path(__file__).resolve().parents[1]
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        from training.stage_07_rl_intervention.ppo import PPO
        self._net = PPO.load_net(str(self._path))
        import torch
        self._torch = torch

    def act(self, obs: np.ndarray, *, deterministic: bool = True, shield: bool = True) -> dict:
        """Return {action, shielded, shield_fired}. action: 0=wait; k=dispatch to stage k-1.
        Raises ModelUnavailableError if the brain/lib is absent (never fabricates)."""
        self._load()
        raw, _logp, _v = self._net.act(np.asarray(obs, dtype=np.float32), deterministic=deterministic)
        if shield:
            shielded, fired = _safety_shield(np.asarray(obs, dtype=np.float32), raw)
            return {"action": int(shielded), "raw_action": int(raw), "shielded": True, "shield_fired": bool(fired)}
        return {"action": int(raw), "raw_action": int(raw), "shielded": False, "shield_fired": False}

    def decide(self, obs: np.ndarray, stages: dict, diagnoses: Optional[dict] = None) -> Any:
        """Fleet-level decision → an `InterventionDecision` for the chosen machine
        (or a MONITOR decision for 'wait'). Proves the RL path produces the SAME
        contract as the rules chooser. `stages` maps stage_id -> Stage; `diagnoses`
        optionally maps stage_id -> Diagnosis for richer rationale."""
        from services.intervention_policy import (
            MONITOR, PREVENTIVE_MAINTENANCE, InterventionDecision,
        )
        out = self.act(obs)
        action = out["action"]
        if action == 0:
            return InterventionDecision(
                stage_id=-1, kind=MONITOR,
                rationale="RL fleet chooser: wait (no dispatch this decision point)",
                diagnosis={},
            )
        sid = action - 1
        diag = (diagnoses or {}).get(sid)
        diag_dict = diag.to_dict() if diag is not None else {"stage_id": sid, "source": "rl_fleet_chooser"}
        rationale = (
            f"RL fleet chooser dispatched the maintenance crew to stage {sid}"
            + (" (safety shield forced)" if out["shield_fired"] else "")
            + f"; raw_action={out['raw_action']}, shielded={out['shielded']}"
        )
        return InterventionDecision(
            stage_id=sid, kind=PREVENTIVE_MAINTENANCE, rationale=rationale, diagnosis=diag_dict,
        )


_default: Optional[RLInterventionPolicy] = None


def get_rl_intervention_policy() -> RLInterventionPolicy:
    global _default
    if _default is None:
        _default = RLInterventionPolicy()
    return _default


__all__ = ["RLInterventionPolicy", "get_rl_intervention_policy", "ModelUnavailableError"]
