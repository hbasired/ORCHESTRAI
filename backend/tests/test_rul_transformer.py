"""Stage 8A — C-MAPSS RUL Transformer tests.

The accuracy test needs the trained weights (`models/rul_transformer_cmapss.pt`) AND the FD001
dataset (downloaded/cached); it skips honestly when either is absent. The honest-unavailable +
shape-validation tests need neither.
"""
from __future__ import annotations

import numpy as np
import pytest

from ml.rul_transformer import RULTransformer, RUL_FEATURES, ModelUnavailableError, get_rul_transformer


def _available() -> bool:
    return get_rul_transformer().is_available()


needs_weights = pytest.mark.skipif(not _available(), reason="trained RUL transformer unavailable (honest skip)")


# ---- honest unavailability / validation (no weights needed) -----------------

def test_honest_unavailable(tmp_path):
    m = RULTransformer(weights_path=tmp_path / "missing.pt")
    assert m.is_available() is False
    with pytest.raises(ModelUnavailableError):
        m.predict_rul(np.zeros((30, len(RUL_FEATURES)), dtype=np.float32))


@needs_weights
def test_window_validation():
    m = get_rul_transformer()
    with pytest.raises(ValueError):
        m.predict_rul(np.zeros((30, 3), dtype=np.float32))  # wrong feature count


# ---- real benchmark accuracy (needs weights + dataset) ----------------------

@needs_weights
def test_fd001_rmse_beats_baseline_and_is_competitive():
    try:
        from training.stage_08_world_model.cmapss_data import load_fd001, CmapssConfig
        d = load_fd001(CmapssConfig(window=30))
    except Exception as e:
        pytest.skip(f"C-MAPSS dataset unavailable (offline): {e}")
    m = get_rul_transformer()
    span = d["feat_max"] - d["feat_min"]
    preds = np.array([m.predict_rul(d["Xte"][i] * span + d["feat_min"])["rul_cycles"]
                      for i in range(len(d["Xte"]))], dtype=np.float64)
    yte = d["yte"].astype(np.float64)
    rmse = float(np.sqrt(np.mean((preds - yte) ** 2)))
    base_rmse = float(np.sqrt(np.mean((yte - yte.mean()) ** 2)))
    assert rmse < base_rmse, f"RUL RMSE {rmse:.2f} must beat naive baseline {base_rmse:.2f}"
    # SOTA-competitive: well under the classic CNN (18.45) / LSTM (16.14) literature baselines.
    assert rmse < 16.0, f"RUL RMSE should be SOTA-competitive (<16), got {rmse:.2f}"


@needs_weights
def test_predict_rul_is_capped_and_nonnegative():
    m = get_rul_transformer()
    out = m.predict_rul(np.zeros((30, len(RUL_FEATURES)), dtype=np.float32))
    assert out["rul_cycles"] >= 0.0
    assert out["rul_cycles"] <= out["capped_at"] + 1e-6
    assert out["window"] == 30 and len(out["sensors"]) == len(RUL_FEATURES)
