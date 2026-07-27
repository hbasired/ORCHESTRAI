"""Stage 7 depth-hardening — MaskablePPO group-maintenance scheduler inference glue.

Loads the Stable-Baselines3 sb3-contrib **MaskablePPO** policy trained by
`backend/training/stage_07_rl_intervention/train_sb3.py` on the richer group/opportunistic maintenance
scheduling MDP, and selects a (masked) action. Honest by design (mirrors the other inference glues): raises
`ModelUnavailableError` if SB3 / the trained policy is absent — NEVER fabricates an action.

Scope (honest): this is the deepened RL substrate on the scheduling-MDP abstraction (group batching + opportunistic
demand timing + crew contention). Whether it is the PRODUCTION chooser depends on the measured CRN-paired
RL-vs-rules result recorded in `models/rl_intervention_maskable_ppo.metrics.json` — the better policy wins, not the
fancier one (the original Stage-7 finding stands until RL demonstrably beats the best rule). Not actuator-wired.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from ml.failure_predictor import ModelUnavailableError  # reuse the honest-unavailable contract

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_WEIGHTS = _MODELS_DIR / "rl_intervention_maskable_ppo.zip"


class GroupSchedulerRL:
    """MaskablePPO maintenance-scheduling policy. Honest about unavailability — never fabricates."""

    def __init__(self, weights_path: Optional[Path] = None) -> None:
        self._path = Path(weights_path) if weights_path else _WEIGHTS
        self._model = None

    def is_available(self) -> bool:
        try:
            self._load()
            return True
        except ModelUnavailableError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sb3_contrib import MaskablePPO
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"sb3-contrib not available: {e}")
        if not self._path.exists():
            raise ModelUnavailableError(
                f"trained MaskablePPO not found: {self._path} — run "
                f"backend/training/stage_07_rl_intervention/train_sb3.py")
        self._model = MaskablePPO.load(str(self._path.with_suffix("")))

    def act(self, obs, action_masks=None) -> int:
        """Select a (masked) discrete action for the group-maintenance env. Raises if no policy/lib."""
        self._load()
        kwargs = {"deterministic": True}
        if action_masks is not None:
            kwargs["action_masks"] = np.asarray(action_masks, dtype=bool)
        a, _ = self._model.predict(np.asarray(obs, dtype=np.float32), **kwargs)
        return int(a)

    @property
    def model_info(self) -> dict:
        return {"weights": str(self._path), "available": self._model is not None,
                "algorithm": "MaskablePPO (sb3-contrib, action masking)",
                "env": "GroupMaintenanceEnv (group + opportunistic maintenance scheduling MDP)"}


_default: Optional[GroupSchedulerRL] = None


def get_group_scheduler_rl() -> GroupSchedulerRL:
    global _default
    if _default is None:
        _default = GroupSchedulerRL()
    return _default


__all__ = ["GroupSchedulerRL", "get_group_scheduler_rl", "ModelUnavailableError"]
