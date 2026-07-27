"""Stage 17 — per-joint joint-torque anomaly detection (KB_17 §"Self-Healing" layer 1; research §27.3).

A **robust rolling-Z** detector: over a rolling window per joint, an incoming torque sample is anomalous when its
**robust Z-score** (median / MAD, with the 1.4826 normal-consistency factor) exceeds a threshold (default 3σ). Robust
stats (median/MAD) beat mean/std here because a developing fault is exactly the kind of outlier that would corrupt a
mean/std estimate. Deterministic + dependency-free + CPU-trivial (honest over a heavy on-edge model for this signal).
An optional IsolationForest detector is provided for multivariate windows when scikit-learn is present.
"""
from __future__ import annotations

import statistics
from collections import deque
from typing import Optional

_MAD_TO_SIGMA = 1.4826  # makes MAD a consistent estimator of σ for normally-distributed data


class RollingZTorqueDetector:
    """Per-joint robust rolling-Z anomaly detector."""

    def __init__(self, window: int = 50, z_threshold: float = 3.0, min_samples: int = 10) -> None:
        self.window = window
        self.z_threshold = z_threshold
        self.min_samples = min_samples
        self._buffers: dict[str, deque] = {}

    def update(self, joint_id: str, torque: float) -> dict:
        """Add a sample for `joint_id`; return {anomaly, z, median, mad, n}. The sample is added AFTER scoring so a
        run of identical values doesn't make MAD=0 mask the first real deviation incorrectly."""
        buf = self._buffers.setdefault(joint_id, deque(maxlen=self.window))
        n = len(buf)
        if n < self.min_samples:
            buf.append(float(torque))
            return {"joint_id": joint_id, "anomaly": False, "z": 0.0, "n": n, "reason": "warming up"}
        med = statistics.median(buf)
        mad = statistics.median([abs(x - med) for x in buf])
        sigma = mad * _MAD_TO_SIGMA
        if sigma <= 1e-9:
            # zero spread in the window: any departure from the constant is anomalous
            z = 0.0 if abs(torque - med) <= 1e-9 else float("inf")
        else:
            z = abs(float(torque) - med) / sigma
        buf.append(float(torque))
        return {"joint_id": joint_id, "anomaly": z > self.z_threshold, "z": (z if z != float("inf") else 1e9),
                "median": med, "mad": mad, "n": n}

    def detect_window(self, joint_id: str, torques: list[float]) -> dict:
        """Score the LAST sample of `torques` against the preceding ones (a one-shot variant for a supplied window)."""
        if len(torques) <= self.min_samples:
            return {"joint_id": joint_id, "anomaly": False, "z": 0.0, "n": len(torques), "reason": "warming up"}
        hist, x = torques[:-1], torques[-1]
        med = statistics.median(hist)
        mad = statistics.median([abs(h - med) for h in hist]) * _MAD_TO_SIGMA
        z = (abs(x - med) / mad) if mad > 1e-9 else (0.0 if abs(x - med) <= 1e-9 else 1e9)
        return {"joint_id": joint_id, "anomaly": z > self.z_threshold, "z": z, "median": med, "n": len(hist)}

    def reset(self, joint_id: Optional[str] = None) -> None:
        if joint_id is None:
            self._buffers.clear()
        else:
            self._buffers.pop(joint_id, None)


def isolation_forest_window(windows: list[list[float]], contamination: float = 0.05) -> list[bool]:
    """Optional multivariate detector (scikit-learn IsolationForest). Returns per-row anomaly flags. Raises if
    scikit-learn is unavailable — caller falls back to RollingZTorqueDetector (honest, no fake)."""
    from sklearn.ensemble import IsolationForest  # noqa: F401
    import numpy as np
    X = np.asarray(windows, dtype=float)
    model = IsolationForest(contamination=contamination, random_state=0).fit(X)
    return [bool(p == -1) for p in model.predict(X)]


__all__ = ["RollingZTorqueDetector", "isolation_forest_window"]
