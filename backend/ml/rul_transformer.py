"""Stage 8 depth-hardening — attention/Transformer Remaining-Useful-Life (RUL) model.

A small Transformer **encoder** RUL regressor trained on the canonical **C-MAPSS FD001** benchmark
(NASA turbofan; `training/stage_08_world_model/cmapss_data.py`). This replaces the toy 1-layer-LSTM
TTF model's *architecture* with the attention-based design the RUL literature uses (self-attention
over a window of sensor readings → spatial-temporal degradation features), and — crucially — reports
a **real benchmark RMSE/NASA-score**, comparable to published numbers, instead of a near-trivial
SimWorld signal.

Honesty (mirrors `world_model.py` / `failure_predictor.py`): if torch or the trained weights are
absent it raises `ModelUnavailableError` — it NEVER fabricates a forecast. The benchmark RMSE/score
and provenance are recorded in `models/rul_transformer_cmapss.metrics.json` + the model card. FD001 is
a public benchmark (single operating condition / single fault mode); generalisation to a real fleet
still requires re-fit on real telemetry (G-035).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import numpy as np
import structlog

from ml.failure_predictor import ModelUnavailableError  # reuse the honest-unavailable contract

logger = structlog.get_logger(__name__)

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_WEIGHTS = _MODELS_DIR / "rul_transformer_cmapss.pt"

# The 14 informative FD001 sensors (must match cmapss_data._INFORMATIVE_SENSORS, in order).
RUL_FEATURES = ("s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21")


def build_rul_transformer(n_features: int, window: int, d_model: int = 64, nhead: int = 4,
                          num_layers: int = 2, dim_feedforward: int = 128, dropout: float = 0.1):
    """Construct the RUL Transformer-encoder regressor (torch imported lazily).

    Shared by the trainer and the inference wrapper so there is a single source of truth for the arch.
    Input: (batch, window, n_features) → output: (batch,) predicted RUL in cycles.
    """
    import torch
    import torch.nn as nn

    class _PositionalEncoding(nn.Module):
        """Fixed sinusoidal positional encoding over the time axis."""

        def __init__(self, d_model: int, max_len: int):
            super().__init__()
            pe = torch.zeros(max_len, d_model)
            pos = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
            div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(pos * div)
            pe[:, 1::2] = torch.cos(pos * div)
            self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, d_model)

        def forward(self, x):
            return x + self.pe[:, : x.size(1), :]

    class _RULTransformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_proj = nn.Linear(n_features, d_model)
            self.pos = _PositionalEncoding(d_model, window)
            enc = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward,
                dropout=dropout, batch_first=True, activation="gelu")
            self.encoder = nn.TransformerEncoder(enc, num_layers=num_layers)
            self.head = nn.Sequential(
                nn.Linear(d_model, d_model // 2), nn.GELU(), nn.Dropout(dropout),
                nn.Linear(d_model // 2, 1))

        def forward(self, x):                    # x: (B, window, n_features)
            h = self.pos(self.input_proj(x))
            h = self.encoder(h)                  # (B, window, d_model)
            h = h.mean(dim=1)                    # temporal mean-pool
            return self.head(h).squeeze(-1)      # (B,)

    return _RULTransformer()


class RULTransformer:
    """Inference wrapper for the C-MAPSS RUL Transformer. Honest about unavailability."""

    def __init__(self, weights_path: Optional[Path] = None) -> None:
        self._path = Path(weights_path) if weights_path else _WEIGHTS
        self._net = None
        self._meta: Optional[dict] = None
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
            import torch
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"PyTorch not available: {e}")
        if not self._path.exists():
            raise ModelUnavailableError(
                f"trained RUL transformer not found: {self._path} — run "
                f"backend/training/stage_08_world_model/train_cmapss.py")
        ckpt = torch.load(str(self._path), map_location="cpu", weights_only=True)
        net = build_rul_transformer(
            n_features=int(ckpt["n_features"]), window=int(ckpt["window"]),
            d_model=int(ckpt["d_model"]), nhead=int(ckpt["nhead"]),
            num_layers=int(ckpt["num_layers"]), dim_feedforward=int(ckpt["dim_feedforward"]),
            dropout=float(ckpt.get("dropout", 0.1)))
        net.load_state_dict(ckpt["state_dict"])
        net.eval()
        self._net = net
        self._torch = torch
        self._meta = {
            "window": int(ckpt["window"]),
            "sensors": list(ckpt["sensors"]),
            "feat_min": np.asarray(ckpt["feat_min"], dtype=np.float32),
            "feat_max": np.asarray(ckpt["feat_max"], dtype=np.float32),
            "rul_cap": float(ckpt.get("rul_cap", 125.0)),
        }

    def predict_rul(self, window) -> dict:
        """Forecast remaining-useful-life (cycles) from a window of RAW FD001 sensor readings.

        `window`: array-like (window_len, 14) of the RUL_FEATURES sensors in order (raw units — the
        model applies the train-fit min-max scaler internally). Returns
        ``{rul_cycles, window, sensors, capped_at}``. Raises ``ModelUnavailableError`` if no brain.
        """
        self._load()
        arr = np.asarray(window, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] != len(RUL_FEATURES):
            raise ValueError(f"window must be (window_len, {len(RUL_FEATURES)}); got {arr.shape}")
        denom = np.where((self._meta["feat_max"] - self._meta["feat_min"]) < 1e-8, 1.0,
                         self._meta["feat_max"] - self._meta["feat_min"])
        x = (arr - self._meta["feat_min"]) / denom
        t = self._torch.as_tensor(x[None, :, :], dtype=self._torch.float32)
        with self._torch.no_grad():
            rul = float(self._net(t).item())
        return {
            "rul_cycles": max(0.0, rul),
            "window": self._meta["window"],
            "sensors": self._meta["sensors"],
            "capped_at": self._meta["rul_cap"],
        }

    @property
    def model_info(self) -> dict:
        return {"weights": str(self._path), "available": self._net is not None,
                "task": "remaining-useful-life (cycles) — C-MAPSS FD001",
                "arch": "Transformer encoder (self-attention over sensor window)",
                "features": list(RUL_FEATURES)}


_default: Optional[RULTransformer] = None


def get_rul_transformer() -> RULTransformer:
    global _default
    if _default is None:
        _default = RULTransformer()
    return _default


__all__ = ["RULTransformer", "get_rul_transformer", "build_rul_transformer",
           "ModelUnavailableError", "RUL_FEATURES"]
