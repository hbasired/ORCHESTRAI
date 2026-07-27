"""Stage 23 (G-028) — total traceability: state_snapshot(pre/post) + decision → audit_chain (EU AI Act Art-12). §33.4.

The runtime already signs each decision to `audit_chain` (Stage 12). G-028 adds the PRE/POST state snapshot around an
incident/decision so the evidence trail shows not just *what* was decided but the *state it acted on and produced* — the
Art-12 record-keeping a conformity assessor expects. `record_decision_trace` captures a bounded snapshot of the relevant
state keys before + after, plus the decision, and appends one signed `audit_chain` row. Best-effort audit (honest
degradation: returns the would-be payload + `audited=False` if the DB is down — never fabricates a seq).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# State keys worth snapshotting around a self-healing decision (bounded — not the whole world).
_SNAPSHOT_KEYS = ("prediction", "ttf_forecast", "diagnosis", "verification", "hitl_required", "sil_level")


def _snapshot(state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    out: dict[str, Any] = {}
    for k in _SNAPSHOT_KEYS:
        if k in state:
            v = state[k]
            out[k] = v if isinstance(v, (int, float, bool, str)) or v is None else _summ(v)
    return out


def _summ(v: Any) -> Any:
    """Bound nested structures so the snapshot stays small + JSON-serialisable."""
    if isinstance(v, dict):
        return {k: (vv if isinstance(vv, (int, float, bool, str)) or vv is None else str(type(vv).__name__))
                for k, vv in list(v.items())[:12]}
    if isinstance(v, (list, tuple)):
        return {"_type": type(v).__name__, "len": len(v)}
    return str(type(v).__name__)


@dataclass(frozen=True)
class TraceRecord:
    incident_id: str
    decision: dict[str, Any]
    state_pre: dict[str, Any]
    state_post: dict[str, Any]
    seq: Optional[int]      # audit_chain seq if recorded, else None
    audited: bool


def record_decision_trace(incident_id: str, state_pre: dict[str, Any], state_post: dict[str, Any],
                          decision: dict[str, Any], *, actor: str = "runtime") -> TraceRecord:
    """Append one Art-12 traceability row: {incident, decision, state_pre, state_post}. Best-effort signed audit."""
    payload = {
        "incident_id": incident_id,
        "decision": {k: decision.get(k) for k in ("kind", "approved", "rationale", "hitl_required", "executed")
                     if isinstance(decision, dict) and k in decision},
        "state_pre": _snapshot(state_pre),
        "state_post": _snapshot(state_post),
    }
    seq, audited = None, False
    try:
        from memory.audit_chain import append
        seq = append(actor, "decision.trace", payload)
        audited = True
    except Exception:  # noqa: BLE001 - DB/crypto down -> honest: no fabricated seq
        pass
    return TraceRecord(incident_id, payload["decision"], payload["state_pre"], payload["state_post"], seq, audited)


__all__ = ["TraceRecord", "record_decision_trace"]
