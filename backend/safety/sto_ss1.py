"""Stage 17 — emergency safe-motion paths STO / SS1 (KB_17 §"STO / SS1 paths"; IEC 61800-5-2).

`trigger_sto()` — **Safe Torque Off**: motor torque removed immediately. `trigger_ss1(profile)` — **Safe Stop 1**:
a controlled deceleration, THEN STO. In a real deployment these are HARDWIRED safety circuits (the software here is the
trigger + the evidence record, not the safety function itself). Both ALWAYS write a signed `audit_chain` row (actor
`safety.sto`/`safety.ss1`, full world state at trigger) — EU AI Act Art-12 evidence (KB_17). The audit write is
best-effort (a DB outage must never PREVENT a safety stop), but its success/failure is reported honestly.
"""
from __future__ import annotations

import time
from typing import Any, Optional


def _audit(actor: str, action: str, payload: dict[str, Any]) -> Optional[int]:
    """Append a signed audit_chain row (ML-DSA-65 via the Stage-13.5 signer). Best-effort: safety is never blocked by
    an audit-store outage — returns the seq, or None if the store was unavailable (reported, never faked)."""
    try:
        from observability.evidence_sink import record
        return record(actor, action, payload)
    except Exception:  # noqa: BLE001 - safety first; the audit is best-effort
        return None


def trigger_sto(world_state: Optional[dict] = None, *, reason: str = "") -> dict[str, Any]:
    """Safe Torque Off. Records the trigger + a signed audit row. Returns the trigger result (incl. audit status)."""
    from observability.otel_init import traced_span
    ts = time.time()
    with traced_span("safety.sto", **{"safety.function": "STO", "safety.reason": reason}):
        payload = {"function": "STO", "reason": reason, "triggered_at": ts, "world_state": world_state or {}}
        seq = _audit("safety.sto", "trigger", payload)
        return {"function": "STO", "triggered": True, "reason": reason, "triggered_at": ts,
                "audit_seq": seq, "audit_recorded": seq is not None}


def trigger_ss1(deceleration_profile: dict[str, Any], world_state: Optional[dict] = None, *,
                reason: str = "") -> dict[str, Any]:
    """Safe Stop 1: a controlled deceleration (per `deceleration_profile`), then STO. Records a signed audit row for
    the SS1 trigger AND the terminating STO."""
    from observability.otel_init import traced_span
    ts = time.time()
    with traced_span("safety.ss1", **{"safety.function": "SS1", "safety.reason": reason}):
        ss1_seq = _audit("safety.ss1", "trigger",
                         {"function": "SS1", "deceleration_profile": deceleration_profile, "reason": reason,
                          "triggered_at": ts, "world_state": world_state or {}})
        # SS1 terminates in STO once decelerated.
        sto = trigger_sto(world_state, reason=f"SS1 terminal STO ({reason})")
        return {"function": "SS1", "triggered": True, "reason": reason, "triggered_at": ts,
                "deceleration_profile": deceleration_profile, "audit_seq": ss1_seq,
                "audit_recorded": ss1_seq is not None, "terminal_sto": sto}


__all__ = ["trigger_sto", "trigger_ss1"]
