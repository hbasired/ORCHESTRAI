"""Stage 4 — machine failure-risk predictor (PREDICT step of the self-healing engine, KB_25 step 1).

Loads the trained brain from `models/pdm_failure_predictor.*` and returns a per-snapshot failure probability.
Supports two brain architectures (chosen by `model_meta.json["arch"]`):
  - **XGBoost** (current best — PR-AUC 0.847): loads `models/pdm_failure_predictor.xgb.json`, RAW features.
  - **MLP** (prior — PR-AUC 0.679): loads `models/pdm_failure_predictor.pt`, StandardScaler-scaled features.

Honest by design: if the trained brain or the required library is unavailable it raises
`ModelUnavailableError` — it NEVER fabricates a probability (no `random.*`, no theatrical fallback).
The at-risk threshold prefers the **recall-tuned** value (catch more failures) when present.

Brain provenance: AI4I 2020 (UCI, CC BY 4.0), clean stratified split, no leakage (see model card). First-cut
proxy on CNC-machine signals — must be re-fit on real plant/robot telemetry before pilot (gap G-035).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_FEATURE_ORDER_DEFAULT = [
    "Type_ord", "Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]",
    "Torque [Nm]", "Tool wear [min]", "temp_diff", "power_w",
]


class ModelUnavailableError(RuntimeError):
    """Raised when the trained brain or its library is missing. We report this; we never invent a prediction."""


class FailurePredictor:
    """Per-snapshot failure-risk classifier (XGBoost or MLP, per the brain's meta)."""

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self._dir = Path(models_dir) if models_dir else _MODELS_DIR
        self._kind: Optional[str] = None   # 'xgb' | 'mlp'
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
        meta_path = self._dir / "pdm_failure_predictor.meta.json"
        if not meta_path.exists():
            raise ModelUnavailableError(
                f"trained brain meta not found in {self._dir} — run a Stage-4 notebook in notebooks/"
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        arch = str(meta.get("arch", "MLP")).upper()

        if arch == "XGBOOST":
            try:
                import xgboost as xgb
            except Exception as e:  # pragma: no cover - environment dependent
                raise ModelUnavailableError(f"xgboost not available: {e}")
            xgb_path = self._dir / "pdm_failure_predictor.xgb.json"
            if not xgb_path.exists():
                raise ModelUnavailableError(f"XGBoost brain not found: {xgb_path}")
            model = xgb.XGBClassifier()
            model.load_model(str(xgb_path))
            self._kind, self._model, self._meta = "xgb", model, meta
            return

        # MLP path
        try:
            import torch
            import torch.nn as nn
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"PyTorch not available: {e}")
        pt_path = self._dir / "pdm_failure_predictor.pt"
        if not pt_path.exists():
            raise ModelUnavailableError(f"MLP brain not found: {pt_path}")

        class FailureMLP(nn.Module):
            def __init__(self, d: int, h1: int, h2: int, dropout: float) -> None:
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(d, h1), nn.ReLU(), nn.Dropout(dropout),
                    nn.Linear(h1, h2), nn.ReLU(), nn.Dropout(dropout), nn.Linear(h2, 1),
                )

            def forward(self, x):
                return self.net(x).squeeze(-1)

        model = FailureMLP(meta["input_dim"], meta["h1"], meta["h2"], meta["dropout"])
        model.load_state_dict(torch.load(pt_path, map_location="cpu"))
        model.eval()
        self._kind, self._model, self._meta, self._torch = "mlp", model, meta, torch

    def _raw_vector(self, *, type_: str, air_temp_k: float, process_temp_k: float,
                    rot_speed_rpm: float, torque_nm: float, tool_wear_min: float) -> list[float]:
        m = self._meta
        raw = {
            "Type_ord": float(m.get("type_encoding", {"L": 0, "M": 1, "H": 2}).get(str(type_).upper(), 1)),
            "Air temperature [K]": float(air_temp_k),
            "Process temperature [K]": float(process_temp_k),
            "Rotational speed [rpm]": float(rot_speed_rpm),
            "Torque [Nm]": float(torque_nm),
            "Tool wear [min]": float(tool_wear_min),
            "temp_diff": float(process_temp_k) - float(air_temp_k),
            "power_w": float(torque_nm) * float(rot_speed_rpm) * 2.0 * math.pi / 60.0,
        }
        order = m.get("features", _FEATURE_ORDER_DEFAULT)
        return [raw[f] for f in order]

    def _threshold(self) -> float:
        m = self._meta
        # Prefer the recall-tuned threshold (catch more failures); fall back to F1 / single threshold.
        for key in ("threshold_recall80", "threshold_f1", "threshold"):
            if key in m and m[key] is not None:
                return float(m[key])
        return 0.5

    def predict_failure(self, *, type_: str = "M", air_temp_k: float, process_temp_k: float,
                        rot_speed_rpm: float, torque_nm: float, tool_wear_min: float) -> dict:
        """Return ``{p_fail, at_risk, threshold, arch, dataset}``. Raises ``ModelUnavailableError`` if no brain."""
        self._load()
        vec = self._raw_vector(type_=type_, air_temp_k=air_temp_k, process_temp_k=process_temp_k,
                               rot_speed_rpm=rot_speed_rpm, torque_nm=torque_nm, tool_wear_min=tool_wear_min)
        if self._kind == "xgb":
            # XGBoost trained on RAW features (no scaling).
            p = float(self._model.predict_proba([vec])[0, 1])
        else:
            # MLP trained on StandardScaler-scaled features.
            mean, scale = self._meta["scaler_mean"], self._meta["scaler_scale"]
            x = [(v - mean[i]) / scale[i] for i, v in enumerate(vec)]
            t = self._torch.tensor([x], dtype=self._torch.float32)
            with self._torch.no_grad():
                p = float(self._torch.sigmoid(self._model(t)).item())
        thr = self._threshold()
        return {
            "p_fail": p,
            "at_risk": p >= thr,
            "threshold": thr,
            "arch": self._meta.get("arch", "MLP"),
            "dataset": str(self._meta.get("task", "AI4I 2020")),
        }

    # ---- explainability support (Stage 10) ---------------------------------

    def feature_names(self) -> list[str]:
        """Ordered raw feature names the model consumes (for SHAP labelling)."""
        self._load()
        return list(self._meta.get("features", _FEATURE_ORDER_DEFAULT))

    def raw_vector(self, *, type_: str = "M", air_temp_k: float, process_temp_k: float,
                   rot_speed_rpm: float, torque_nm: float, tool_wear_min: float) -> list[float]:
        """Public wrapper of the canonical raw-feature build (reused by the explainer)."""
        self._load()
        return self._raw_vector(type_=type_, air_temp_k=air_temp_k, process_temp_k=process_temp_k,
                                rot_speed_rpm=rot_speed_rpm, torque_nm=torque_nm, tool_wear_min=tool_wear_min)

    def shap_contribs(self, vec: list[float]) -> list[float]:
        """Exact per-feature TreeSHAP contributions (margin space) for one raw vector,
        via XGBoost's native `pred_contribs` — no extra dependency. The returned list has
        len(features)+1 (last element is the bias/base value). Raises ``ModelUnavailableError``
        if the active brain is not XGBoost (only the tree model supports exact TreeSHAP here)."""
        self._load()
        if self._kind != "xgb":
            raise ModelUnavailableError(
                "exact TreeSHAP requires the XGBoost brain (active arch is "
                f"{self._meta.get('arch')!r}); no fabricated attributions."
            )
        import numpy as np
        import xgboost as xgb
        booster = self._model.get_booster()
        # Build the DMatrix exactly as XGBClassifier.predict_proba does (positional, the booster's
        # own trained feature_names) so the contributions sum to the SAME raw margin sigmoid'd into p_fail.
        dm = xgb.DMatrix(np.asarray([vec], dtype=float), feature_names=booster.feature_names)
        contribs = booster.predict(dm, pred_contribs=True)
        return [float(c) for c in contribs[0]]


_default: Optional[FailurePredictor] = None


def get_failure_predictor() -> FailurePredictor:
    """Process-wide singleton."""
    global _default
    if _default is None:
        _default = FailurePredictor()
    return _default
