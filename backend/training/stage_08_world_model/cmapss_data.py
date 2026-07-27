"""Stage 8 depth-hardening — real C-MAPSS FD001 RUL benchmark loader + preprocessing.

C-MAPSS (NASA Turbofan Engine Degradation Simulation, Saxena & Goebel 2008) is the canonical
remaining-useful-life (RUL) benchmark. FD001 = single operating condition, single fault mode:
100 train engines run to failure, 100 test engines truncated before failure, with a ground-truth
RUL for each test engine's final cycle (`RUL_FD001.txt`).

This module downloads FD001 on first use (free, ~3 MB, cached under repo-root `data/datasets/cmapss/`,
which is git-ignored — "real dataset binaries live behind DVC, not git") and applies the STANDARD
preprocessing the literature uses so our reported RMSE/score is comparable:
  - keep the 14 informative sensors (drop the 7 constant ones + the 3 near-constant op-settings),
  - min-max normalise per sensor (fit on TRAIN only — no leakage),
  - **piecewise-linear RUL with cap Rc=125** (the standard early-life clip; without it RMSE is not
    comparable across papers),
  - sliding windows of length `window` (default 30); each window labelled with the (capped) RUL at
    its last cycle. Test = the LAST window of each test engine vs `RUL_FD001.txt`.

Honesty: if the dataset cannot be downloaded (offline) the loader raises `DatasetUnavailableError`
— it never fabricates data. Provenance + the two mirror URLs are recorded in the metrics/model card.
"""
from __future__ import annotations

import io
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

# repo-root/data/datasets/cmapss/  (git-ignored dataset cache; DVC territory)
_CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "datasets" / "cmapss"

# Two independent public mirrors of the unmodified NASA CMAPSSData files (tried in order).
_MIRRORS = (
    "https://raw.githubusercontent.com/jiaxiang-cheng/PyTorch-Transformer-for-RUL-Prediction/main/CMAPSSData",
    "https://raw.githubusercontent.com/LahiruJayasinghe/RUL-Net/master/CMAPSSData",
)
_FILES = ("train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt")

# Column layout of the raw files: unit, cycle, 3 operational settings, 21 sensors.
_RAW_COLS = ["unit", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]
# The 14 sensors that carry degradation information on FD001 (the other 7 are constant). This is
# the standard FD001 feature set used across the RUL literature.
_INFORMATIVE_SENSORS = ["s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"]
RUL_CAP = 125.0  # piecewise-linear RUL clip (canonical)
N_FEATURES = len(_INFORMATIVE_SENSORS)


class DatasetUnavailableError(RuntimeError):
    """Raised when C-MAPSS FD001 cannot be obtained — we never fabricate the benchmark."""


@dataclass
class CmapssConfig:
    window: int = 30
    rul_cap: float = RUL_CAP


# ---- download (cached) ------------------------------------------------------

def ensure_files(cache_dir: Path = _CACHE_DIR) -> Path:
    """Download the three FD001 files to `cache_dir` if absent. Returns the cache dir.

    Raises DatasetUnavailableError if no mirror is reachable (offline) — honest, never fabricates.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    for fname in _FILES:
        dest = cache_dir / fname
        if dest.exists() and dest.stat().st_size > 0:
            continue
        last_err: Optional[Exception] = None
        for base in _MIRRORS:
            url = f"{base}/{fname}"
            try:
                with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (trusted raw mirror)
                    data = r.read()
                if not data:
                    raise IOError("empty body")
                dest.write_bytes(data)
                last_err = None
                break
            except Exception as e:  # try the next mirror
                last_err = e
        if last_err is not None:
            raise DatasetUnavailableError(
                f"could not download {fname} from any mirror ({last_err}); C-MAPSS FD001 unavailable. "
                f"No fabricated data is produced."
            )
    return cache_dir


def _read_raw(path: Path) -> np.ndarray:
    """Read a whitespace-delimited CMAPSS file into a float array (rows × 26)."""
    txt = path.read_text(encoding="utf-8")
    rows = [list(map(float, line.split())) for line in txt.splitlines() if line.strip()]
    return np.asarray(rows, dtype=np.float64)


# ---- preprocessing ----------------------------------------------------------

def _piecewise_rul(n_cycles: int, cap: float) -> np.ndarray:
    """Piecewise-linear RUL for an engine with `n_cycles`: clipped at `cap`, linear to 0 at failure."""
    rul = np.arange(n_cycles - 1, -1, -1, dtype=np.float64)  # cycles remaining at each step
    return np.minimum(rul, cap)


def load_fd001(cfg: Optional[CmapssConfig] = None, cache_dir: Path = _CACHE_DIR) -> dict:
    """Load + preprocess FD001 into train windows and per-engine test windows.

    Returns a dict:
      Xtr (Ntr, window, 14), ytr (Ntr,)         — all sliding windows from the 100 train engines
      Xte (100, window, 14),  yte (100,)         — last window of each test engine vs RUL_FD001.txt
      feat_min, feat_max (14,)                   — train-fit min-max scaler params
      sensors, window, rul_cap, n_train_engines, n_test_engines
    """
    cfg = cfg or CmapssConfig()
    cache = ensure_files(cache_dir)

    train = _read_raw(cache / "train_FD001.txt")
    test = _read_raw(cache / "test_FD001.txt")
    test_rul = _read_raw(cache / "RUL_FD001.txt").reshape(-1)

    col = {c: i for i, c in enumerate(_RAW_COLS)}
    sens_idx = [col[s] for s in _INFORMATIVE_SENSORS]

    # Fit min-max on TRAIN sensors only (no leakage).
    tr_sensors = train[:, sens_idx]
    feat_min = tr_sensors.min(axis=0)
    feat_max = tr_sensors.max(axis=0)
    denom = np.where((feat_max - feat_min) < 1e-8, 1.0, feat_max - feat_min)

    def _norm(a: np.ndarray) -> np.ndarray:
        return (a[:, sens_idx] - feat_min) / denom

    w = cfg.window

    # --- train: every sliding window of every engine ---
    Xtr, ytr = [], []
    for unit in np.unique(train[:, col["unit"]]):
        rows = train[train[:, col["unit"]] == unit]
        rows = rows[rows[:, col["cycle"]].argsort()]
        feats = _norm(rows)
        rul = _piecewise_rul(len(rows), cfg.rul_cap)
        for end in range(w - 1, len(rows)):
            Xtr.append(feats[end - w + 1:end + 1])
            ytr.append(rul[end])

    # --- test: the LAST window of each engine, labelled by RUL_FD001.txt (capped consistently) ---
    Xte, yte = [], []
    units = np.unique(test[:, col["unit"]])
    for i, unit in enumerate(units):
        rows = test[test[:, col["unit"]] == unit]
        rows = rows[rows[:, col["cycle"]].argsort()]
        feats = _norm(rows)
        if len(rows) >= w:
            window = feats[-w:]
        else:  # short engine: left-pad with the earliest available frame (rare on FD001)
            pad = np.repeat(feats[:1], w - len(rows), axis=0)
            window = np.vstack([pad, feats])
        Xte.append(window)
        yte.append(min(float(test_rul[i]), cfg.rul_cap))

    return {
        "Xtr": np.asarray(Xtr, dtype=np.float32),
        "ytr": np.asarray(ytr, dtype=np.float32),
        "Xte": np.asarray(Xte, dtype=np.float32),
        "yte": np.asarray(yte, dtype=np.float32),
        "feat_min": feat_min.astype(np.float32),
        "feat_max": feat_max.astype(np.float32),
        "sensors": list(_INFORMATIVE_SENSORS),
        "window": w,
        "rul_cap": cfg.rul_cap,
        "n_train_engines": int(len(np.unique(train[:, col["unit"]]))),
        "n_test_engines": int(len(units)),
        "mirrors": list(_MIRRORS),
    }


def nasa_score(pred: np.ndarray, true: np.ndarray) -> float:
    """The asymmetric NASA C-MAPSS scoring function (penalises late predictions more). Lower = better."""
    d = np.asarray(pred, dtype=np.float64) - np.asarray(true, dtype=np.float64)
    return float(np.sum(np.where(d < 0, np.expm1(-d / 13.0), np.expm1(d / 10.0))))


__all__ = [
    "CmapssConfig", "DatasetUnavailableError", "ensure_files", "load_fd001", "nasa_score",
    "N_FEATURES", "RUL_CAP",
]
