"""Stage 5 — demand forecaster (supply-chain head; LSTM).

Loads the trained brain from `models/demand_forecaster.*` and forecasts next-step demand from a window of
recent hourly readings. Honest by design: raises `ModelUnavailableError` if PyTorch or the brain is missing —
it NEVER fabricates a forecast (no `random.*`).

Brain provenance: `notebooks/stage05_demand_forecasting_v2_colab.ipynb` (UCI Bike Sharing #275, CC BY 4.0;
leakage-free chronological split; cyclical features + log1p target + grid search). Metrics in
`models/demand_forecaster.metrics.json` (MAE 32.9 / MAPE 21.0%, +59% vs persistence). First-cut PROXY (bike
demand) for the supply-chain head — re-fit on real order data before pilot (gap G-035).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional, Sequence

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


class ModelUnavailableError(RuntimeError):
    """Raised when the trained brain or PyTorch is missing. We report this; we never invent a forecast."""


def _row_features(row: dict, use_log: bool) -> list[float]:
    """Build the 15-feature vector for one hourly reading, in the brain's feature order."""
    cnt = float(row.get("cnt", 0.0))
    hr = float(row.get("hr", 0)); wd = float(row.get("weekday", 0)); mo = float(row.get("mnth", row.get("month", 1)))
    return [
        math.log1p(cnt) if use_log else cnt,          # target (col 0)
        float(row.get("temp", 0.0)),
        float(row.get("atemp", 0.0)),
        float(row.get("hum", 0.0)),
        float(row.get("windspeed", 0.0)),
        math.sin(2 * math.pi * hr / 24.0), math.cos(2 * math.pi * hr / 24.0),
        math.sin(2 * math.pi * wd / 7.0), math.cos(2 * math.pi * wd / 7.0),
        math.sin(2 * math.pi * mo / 12.0), math.cos(2 * math.pi * mo / 12.0),
        float(row.get("workingday", 0)),
        float(row.get("holiday", 0)),
        float(row.get("weathersit", 1)),
        float(row.get("season", 1)),
    ]


class DemandForecaster:
    """Next-step demand forecaster (LSTM over a window of recent readings)."""

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self._dir = Path(models_dir) if models_dir else _MODELS_DIR
        self._model = None
        self._meta: Optional[dict] = None
        self._torch = None

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
            import torch
            import torch.nn as nn
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"PyTorch not available: {e}")
        meta_path = self._dir / "demand_forecaster.meta.json"
        pt_path = self._dir / "demand_forecaster.pt"
        if not meta_path.exists() or not pt_path.exists():
            raise ModelUnavailableError(
                f"demand brain not found in {self._dir} — run notebooks/stage05_demand_forecasting_v2_colab.ipynb"
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        class DemandLSTM(nn.Module):
            def __init__(self, d: int, hidden: int, layers: int, dropout: float) -> None:
                super().__init__()
                self.lstm = nn.LSTM(d, hidden, num_layers=layers, batch_first=True,
                                    dropout=dropout if layers > 1 else 0.0)
                self.head = nn.Linear(hidden, 1)

            def forward(self, x):
                h, _ = self.lstm(x)
                return self.head(h[:, -1, :]).squeeze(-1)

        model = DemandLSTM(meta["input_dim"], meta["hidden"], meta["layers"], meta.get("dropout", 0.2))
        model.load_state_dict(torch.load(pt_path, map_location="cpu"))
        model.eval()
        self._model, self._meta, self._torch = model, meta, torch

    def forecast(self, history: Sequence[dict]) -> dict:
        """Forecast next-step demand from the last ``window`` hourly readings.

        ``history``: list of dicts with keys cnt, temp, atemp, hum, windspeed, hr, weekday, mnth/month,
        workingday, holiday, weathersit, season. Returns ``{forecast, window, model}``. Raises
        ``ModelUnavailableError`` if the brain is absent; raises ``ValueError`` if too little history.
        """
        self._load()
        m = self._meta
        w = int(m["window"])
        if len(history) < w:
            raise ValueError(f"need >= {w} readings, got {len(history)}")
        use_log = bool(m.get("use_log", False))
        rows = [_row_features(r, use_log) for r in list(history)[-w:]]
        mean, scale = m["scaler_mean"], m["scaler_scale"]
        scaled = [[(v - mean[i]) / scale[i] for i, v in enumerate(r)] for r in rows]
        t = self._torch.tensor([scaled], dtype=self._torch.float32)  # (1, w, F)
        with self._torch.no_grad():
            out = float(self._model(t).item())
        target = out * scale[0] + mean[0]                 # un-scale col 0
        demand = math.expm1(target) if use_log else target
        return {"forecast": max(0.0, demand), "window": w, "model": "demand_forecaster (LSTM, Bike-Sharing proxy)"}


_default: Optional[DemandForecaster] = None


def get_demand_forecaster() -> DemandForecaster:
    """Process-wide singleton."""
    global _default
    if _default is None:
        _default = DemandForecaster()
    return _default
