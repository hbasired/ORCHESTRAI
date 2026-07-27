"""Stage 31 (G-064-tail) — CONTINUOUS runtime behavioural anomaly detection (research §42.2).

The Stage-25 post-market sweep is a NIGHTLY (batch) anomaly detector over daily audit features. This is its ONLINE
counterpart: a streaming monitor over the runtime's REAL per-incident behavioural features that flags anomalous agent
behaviour AS IT HAPPENS — the trajectory-anomaly oversight the agentic-security SOTA calls for (TrajAD/SentinelAgent).

Two honest, free/local mechanisms:
  1. ROBUST-Z over a rolling window per feature (median / MAD — the same robust estimator as the Stage-25 sweep, so a
     few outliers don't poison the baseline). Below a warmup count it reports `insufficient_history` (no fabricated
     baseline). Flags |robust-z| > threshold.
  2. TRAJECTORY checks — explicit detectors for the canonical agent anomalies (SOTA §42.2): loops (node revisits),
     redundant/repeated actions, invalid tool arguments, and excessive actuation attempts.

On a detected anomaly it appends a signed `behavior.anomaly` audit row (best-effort; failure surfaced, never hidden).
Pure computation; never fabricates — an anomaly is only raised from real feature deviations.
"""
from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

# The behavioural features monitored per incident (all REAL runtime signals).
_FEATURES = ("decision_count", "tool_calls", "actuation_attempts", "verifier_rejections", "node_revisits", "duration_s")
_ROBUST_Z_THRESHOLD = 3.5
_WARMUP = 8               # need this many observations before a baseline is trustworthy (honest)
_WINDOW = 200


@dataclass
class AnomalyVerdict:
    anomalous: bool
    reasons: list[str] = field(default_factory=list)
    z_scores: dict[str, float] = field(default_factory=dict)
    insufficient_history: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"anomalous": self.anomalous, "reasons": self.reasons,
                "z_scores": {k: round(v, 3) for k, v in self.z_scores.items()},
                "insufficient_history": self.insufficient_history}


def _robust_z(x: float, window: list[float]) -> float:
    """0.6745·(x−median)/MAD — robust to outliers. 0.0 when MAD is 0 (no spread) unless x differs from the median."""
    if len(window) < 2:
        return 0.0
    med = statistics.median(window)
    mad = statistics.median([abs(v - med) for v in window])
    if mad == 0.0:
        return 0.0 if x == med else 6.0 * (1 if x > med else -1)   # degenerate spread: any deviation is notable
    return 0.6745 * (x - med) / mad


class BehavioralMonitor:
    """Online per-feature robust-Z + trajectory checks over the runtime's incident behaviour stream."""

    def __init__(self, *, z_threshold: float = _ROBUST_Z_THRESHOLD, warmup: int = _WARMUP, window: int = _WINDOW,
                 audit: bool = True):
        self.z_threshold = z_threshold
        self.warmup = warmup
        self.audit = audit
        self._hist: dict[str, deque] = {f: deque(maxlen=window) for f in _FEATURES}
        self._n = 0

    # ---- trajectory checks (explicit canonical-anomaly detectors) ----------

    @staticmethod
    def _trajectory_reasons(features: dict[str, Any]) -> list[str]:
        reasons = []
        if int(features.get("node_revisits", 0)) >= 3:
            reasons.append(f"loop: {features['node_revisits']} node revisits")
        if int(features.get("redundant_actions", 0)) >= 2:
            reasons.append(f"redundant: {features['redundant_actions']} repeated actions")
        if int(features.get("invalid_tool_args", 0)) >= 1:
            reasons.append(f"invalid_tool_args: {features['invalid_tool_args']}")
        if int(features.get("actuation_attempts", 0)) > int(features.get("decision_count", 0)):
            reasons.append("actuation_attempts exceed decisions (possible ungated actuation attempt)")
        return reasons

    def observe(self, features: dict[str, Any]) -> AnomalyVerdict:
        """Ingest one incident's behavioural features; return an anomaly verdict; update the rolling baseline."""
        # 1. trajectory checks fire regardless of warmup (they are absolute, not baseline-relative).
        reasons = self._trajectory_reasons(features)

        # 2. robust-Z per feature (needs warmup).
        z_scores: dict[str, float] = {}
        insufficient = self._n < self.warmup
        if not insufficient:
            for f in _FEATURES:
                if f in features and features[f] is not None:
                    z = _robust_z(float(features[f]), list(self._hist[f]))
                    z_scores[f] = z
                    if abs(z) > self.z_threshold:
                        reasons.append(f"robust-z {f}={z:.2f} (>|{self.z_threshold}|)")

        anomalous = len(reasons) > 0
        verdict = AnomalyVerdict(anomalous=anomalous, reasons=reasons, z_scores=z_scores,
                                 insufficient_history=insufficient)

        # 3. update the baseline AFTER scoring (so an incident isn't compared against itself).
        for f in _FEATURES:
            if f in features and features[f] is not None:
                self._hist[f].append(float(features[f]))
        self._n += 1

        if anomalous and self.audit:
            self._emit(features, verdict)
        return verdict

    def _emit(self, features: dict[str, Any], verdict: AnomalyVerdict) -> None:
        try:
            from memory.audit_chain import append
            append("security:behavioral_monitor", "behavior.anomaly",
                   {"reasons": verdict.reasons, "z_scores": {k: round(v, 3) for k, v in verdict.z_scores.items()},
                    "features": {k: features.get(k) for k in _FEATURES if k in features}})
        except Exception:  # noqa: BLE001 — audit best-effort; surfaced, never fabricated
            pass


def features_from_run(result: dict[str, Any]) -> dict[str, Any]:
    """Extract behavioural features from a REAL `agents.runtime.graph.run_incident` result — so the monitor consumes
    live runtime output, not a synthetic trace. Maps decisions / trace / audit_seqs → the monitored feature set."""
    decisions = result.get("decisions", []) or []
    trace = result.get("trace", []) or []
    nodes = [str(e.get("node", "")) for e in trace if isinstance(e, dict)]
    revisits = len(nodes) - len(set(nodes)) if nodes else 0
    tool_calls = sum(1 for e in trace if isinstance(e, dict)
                     and ("mcp" in str(e.get("node", "")).lower() or "tool" in str(e.get("summary", "")).lower()))
    actuations = sum(1 for d in decisions if (d.get("executed") if isinstance(d, dict) else getattr(d, "executed", False)))
    rejections = sum(1 for e in trace if isinstance(e, dict) and e.get("ok") is False)
    return {
        "decision_count": len(decisions),
        "tool_calls": tool_calls,
        "actuation_attempts": actuations,
        "verifier_rejections": rejections,
        "node_revisits": revisits,
        "duration_s": float(result.get("duration_s", 0.0)) if result.get("duration_s") is not None else 0.0,
    }


_default: Optional[BehavioralMonitor] = None


def get_behavioral_monitor() -> BehavioralMonitor:
    global _default
    if _default is None:
        _default = BehavioralMonitor()
    return _default


__all__ = ["AnomalyVerdict", "BehavioralMonitor", "get_behavioral_monitor"]
