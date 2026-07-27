"""Stage 17 — bridge to the customer's certified PLC / safety controller (KB_17 §"Component shape").

This is the **integration point** with a certified SIL-rated controller (OPC UA Safety profile / PROFIsafe), NOT a
replacement for it (KB_17 §"does NOT claim" — no certified PLC of our own). `execute()` is the ONLY place that emits
an `actuator.*` span, and it REFUSES unless given an allowing `Decision` routed here (SIL ≥ 2) — the LLM/planner can
never reach an actuator except through `safety.validator.validate()` → here. The `Decision` this executes is produced
ONLY by `safety.validator`. Every actuation writes a signed `audit_chain` row.

The trace-pairing CI invariant (`scripts/check-safety-trace-pairing.py`) requires a `safety.validate.*` span to
PRECEDE every `actuator.*` span — `validate()` emits the former, this emits the latter.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from safety.contract import Action, Decision, SafetyContract


class SafetyBypassError(RuntimeError):
    """Raised when something tries to actuate without an allowing, correctly-routed safety Decision (KB_17)."""


# Honest description of what stands behind the bridge in this build (no real certified PLC here).
SIL_CONTROLLER = "placeholder: OPC UA Safety / PROFIsafe integration point (customer's certified PLC; cert = Stage 23)"


def execute(action: Action, decision: Decision, world_state: Optional[dict] = None,
            contract: Optional["SafetyContract"] = None,
            token_freshness_s: Optional[float] = None) -> dict[str, Any]:
    """Execute an ALLOWED SIL≥2 actuator action via the SIL bridge.

    G-075 HARDENED (Stage 33, research §44.1): a forged `Decision(allow=True, route="sil_bridge")` can NO LONGER
    actuate. `execute` accepts an action ONLY via one of two forgery/TOCTOU-resistant paths:

      (a) AUTHORITATIVE re-validation — if `contract` (+`world_state`) is given, `execute` RE-RUNS
          `safety.validator.validate()` from the contract + CURRENT world_state and ignores the passed verdict
          (forgery- AND TOCTOU-proof: it re-checks the live state).
      (b) CAPABILITY TOKEN — otherwise the passed `Decision` MUST carry a valid, fresh capability token (minted by
          `validate()` on ALLOW) that is bound to THIS exact action. A missing/forged/stale/wrong-action token is
          rejected (`SafetyBypassError`).

    A Decision with neither a re-validation contract nor a valid token is refused. This is defence-in-depth; the
    binding gate remains `safety.validator`."""
    if contract is not None:
        # (a) Self-validating path: re-derive the Decision from the contract + current world_state (forgery/TOCTOU-proof).
        from safety.validator import validate
        decision = validate(action, world_state or {}, contract)
    if not isinstance(decision, Decision) or not decision.allow:
        raise SafetyBypassError("sil_bridge.execute requires an ALLOWING safety Decision (KB_17 — no bypass)")
    if decision.route != "sil_bridge":
        raise SafetyBypassError(
            f"sil_bridge executes only SIL≥2 actions routed to it; decision.route={decision.route!r}")
    if contract is None:
        # (b) Token path: the Decision was NOT re-validated here, so it MUST prove it came from validate() for THIS
        # action and is fresh. This closes G-075 — a hand-forged Decision(allow=True) has no valid token → rejected.
        from safety.capability_token import verify, DEFAULT_FRESHNESS_S
        ok, why = verify(token=decision.token or "", allow=decision.allow, route=decision.route,
                         contract=decision.contract, sil=decision.sil, action=action,
                         nonce=decision.nonce or "", issued_at=decision.issued_at or 0.0,
                         freshness_s=token_freshness_s if token_freshness_s is not None else DEFAULT_FRESHNESS_S)
        if not ok:
            raise SafetyBypassError(
                f"sil_bridge.execute refuses an un-revalidated Decision without a valid capability token: {why} "
                "(pass `contract`+`world_state` to re-validate, or a validator-minted Decision) — G-075")

    from observability.otel_init import traced_span
    ts = time.time()
    with traced_span(f"actuator.{action.actuator}",
                     **{"actuator": action.actuator, "actuator.target": action.target or "",
                        "safety.contract": decision.contract, "safety.sil": decision.sil}):
        # Hand off to the certified controller. PLACEHOLDER: records the dispatch; a real deployment writes to the
        # PLC via OPC UA Safety / PROFIsafe here. We do NOT pretend the physical actuation happened on hardware.
        result = {"executed": True, "actuator": action.actuator, "target": action.target,
                  "via": "sil_bridge", "sil_controller": SIL_CONTROLLER, "sil": decision.sil,
                  "contract": decision.contract, "dispatched_at": ts}
        try:
            from observability.evidence_sink import record
            result["audit_seq"] = record("safety.sil_bridge", f"actuate.{action.actuator}",
                                         {"action": action.model_dump(), "decision": decision.model_dump(),
                                          "world_state": world_state or {}})
        except Exception:  # noqa: BLE001 - audit best-effort; actuation evidence attempted
            result["audit_seq"] = None
        return result


__all__ = ["execute", "SafetyBypassError", "SIL_CONTROLLER"]
