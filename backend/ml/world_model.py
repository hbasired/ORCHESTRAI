"""Stage 8 — learned world model: time-to-failure (TTF) forecasting (KB_25 step 1, G-019).

Forecasts how many minutes until a degrading machine fails, from a short window of its AI4I-unit
telemetry. This is the timing signal the Stage-7 RL intervention lacked (it knew a machine was
at-risk but not *when* it would fail). The model is a small LSTM regressor trained on seeded
SimWorld crack rollouts (`backend/training/stage_08_world_model/`).

Honest by design (mirrors `failure_predictor.py`): if torch or the trained weights are absent it
raises `ModelUnavailableError` — it NEVER fabricates a forecast. The previous stub's
`np.random.randn(...)` fallbacks and untrained-random-weights path are removed.

Provenance: synthetic SimPy plant (KB_05), proxy/sim only — re-fit on real telemetry before any
production claim (G-035). Sim-only; not wired to any actuator.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import structlog

from ml.failure_predictor import ModelUnavailableError  # reuse the honest-unavailable contract

logger = structlog.get_logger(__name__)

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_WEIGHTS = _MODELS_DIR / "world_model_ttf.pt"

# Telemetry features the world model consumes, in order (must match the trainer / rollouts.py).
FEATURES = ("air_temp_k", "process_temp_k", "rot_speed_rpm", "torque_nm", "tool_wear_min")


class WorldModel:
    """LSTM time-to-failure forecaster. Honest about unavailability — never fabricates."""

    def __init__(self, weights_path: Optional[Path] = None) -> None:
        self._path = Path(weights_path) if weights_path else _WEIGHTS
        self._net = None
        self._meta: Optional[dict] = None
        self._torch = None

    # ---- availability ------------------------------------------------------

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
            import torch
            import torch.nn as nn
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"PyTorch not available: {e}")
        if not self._path.exists():
            raise ModelUnavailableError(
                f"trained world model not found: {self._path} — run "
                f"backend/training/stage_08_world_model/train.py"
            )
        ckpt = torch.load(str(self._path), map_location="cpu", weights_only=True)

        class TTFNet(nn.Module):
            def __init__(self, n_feat, hidden, layers, dropout=0.0):
                super().__init__()
                self.lstm = nn.LSTM(n_feat, hidden, num_layers=layers, batch_first=True,
                                    dropout=dropout if layers > 1 else 0.0)
                self.head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.head(out[:, -1, :]).squeeze(-1)

        net = TTFNet(int(ckpt["n_features"]), int(ckpt["hidden"]), int(ckpt["num_layers"]))
        net.load_state_dict(ckpt["state_dict"])
        net.eval()
        self._net = net
        self._torch = torch
        self._meta = {
            "window_len": int(ckpt["window_len"]),
            "features": list(ckpt["features"]),
            "feat_mean": np.asarray(ckpt["feat_mean"], dtype=np.float32),
            "feat_std": np.asarray(ckpt["feat_std"], dtype=np.float32),
        }

    # ---- inference ---------------------------------------------------------

    def predict_ttf(self, window) -> dict:
        """Forecast time-to-failure (minutes) from a telemetry window.

        `window`: array-like (window_len, n_features) in FEATURES order, OR a list of telemetry
        dicts (each containing the FEATURES keys). Returns
        ``{ttf_minutes, window_len, features}``. Raises ``ModelUnavailableError`` if no brain.
        """
        self._load()
        arr = self._coerce_window(window)
        x = (arr - self._meta["feat_mean"]) / self._meta["feat_std"]
        t = self._torch.as_tensor(x[None, :, :], dtype=self._torch.float32)
        with self._torch.no_grad():
            ttf = float(self._net(t).item())
        return {
            "ttf_minutes": max(0.0, ttf),
            "window_len": self._meta["window_len"],
            "features": self._meta["features"],
        }

    def _coerce_window(self, window) -> np.ndarray:
        if isinstance(window, np.ndarray):
            arr = window.astype(np.float32)
        elif window and isinstance(window[0], dict):
            arr = np.array([[float(s[f]) for f in FEATURES] for s in window], dtype=np.float32)
        else:
            arr = np.asarray(window, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] != len(FEATURES):
            raise ValueError(f"window must be (window_len, {len(FEATURES)}); got {arr.shape}")
        return arr

    # ---- back-compatible async surface (used by decision_engine; honest now) ----

    async def load(self) -> None:
        """Async-compat load. Does not raise on absence — sets availability; `predict` is the
        honest gate (decision_engine wraps it in try/except and falls back)."""
        try:
            self._load()
        except ModelUnavailableError as e:
            logger.warning("world model unavailable", error=str(e))

    async def predict(self, current_features, horizons=None) -> dict:
        """Back-compat path for `decision_engine`. The Stage-8 world model forecasts TTF, not the
        old multi-metric horizon dict, so this honestly raises `ModelUnavailableError` unless a
        valid telemetry window is supplied (decision_engine catches it and uses its own fallback).
        New callers should use `predict_ttf`."""
        arr = np.asarray(current_features, dtype=np.float32)
        if arr.ndim == 2 and arr.shape[1] == len(FEATURES):
            return {"ttf": self.predict_ttf(arr)}
        raise ModelUnavailableError(
            "Stage-8 world model forecasts TTF from a (window_len, 5) telemetry window; "
            "the legacy multi-metric horizon prediction is not provided. Use predict_ttf()."
        )

    @property
    def model_info(self) -> dict:
        return {"weights": str(self._path), "available": self._net is not None,
                "task": "time-to-failure (minutes) forecast", "features": list(FEATURES)}


_default: Optional[WorldModel] = None


def get_world_model() -> WorldModel:
    global _default
    if _default is None:
        _default = WorldModel()
    return _default


__all__ = ["WorldModel", "get_world_model", "ModelUnavailableError", "FEATURES"]
