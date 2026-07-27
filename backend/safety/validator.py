"""Stage 16/17 — actuator-command safety gate (KB_17).

Two entry points, both emitting the **`safety.validate`** span the CI trace-pairing invariant requires before any
`actuator.*` span:

- `validate_order(order, connection_fresh)` (Stage 16) — the VDA 5050 structural + connection-freshness anti-spoof gate.
- `validate(action, world_state, contract)` (Stage 17) — the **SIL-rated contract** gate (KB_17 §"Validator flow"):
  precondition + invariant checks → SIL routing (SIL≥2 → `sil_bridge`; SIL 1 → `operator_confirm`; SIL 0 → `direct`);
  a failed check BLOCKS + records a signed `audit_chain` row + names the contract's `fail_safe_path`. Postconditions are
  checked by the executor after actuation. The LLM/planner can never reach an actuator except through this gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from safety.contract import Action, Decision, SafetyContract


@dataclass
class ValidationResult:
    allowed: bool
    reason: str
    checks: dict[str, bool] = field(default_factory=dict)
    stage: str = "structural-stub(Stage16); SIL contract validator=Stage17"


class SafetyValidationError(RuntimeError):
    """Raised when a caller dispatches an actuator command without an allowing ValidationResult."""


def _as_dict(order: Any) -> dict:
    if hasattr(order, "model_dump"):
        return order.model_dump()
    if isinstance(order, dict):
        return order
    raise TypeError("order must be a VDA 5050 OrderMessage or dict")


def validate_order(order: Any, *, connection_fresh: bool) -> ValidationResult:
    """Gate a VDA 5050 order before dispatch. `connection_fresh`: the AGV's `connection` is ONLINE + recent
    (anti-spoof — a stale/offline/rogue AGV must not receive orders). Wrapped in a `safety.validate` span."""
    from observability.otel_init import traced_span

    with traced_span("safety.validate", attributes={"safety.kind": "vda5050.order"}) as span:
        o = _as_dict(order)
        checks = {
            "has_order_id": bool(o.get("orderId")),
            "has_header": o.get("headerId") is not None,
            "has_nodes": isinstance(o.get("nodes"), list) and len(o["nodes"]) > 0,
            "nodes_have_sequence_ids": all("sequenceId" in n for n in (o.get("nodes") or [])),
            "exactly_one_released_first_node": _first_node_released(o),
            "connection_fresh": bool(connection_fresh),
        }
        allowed = all(checks.values())
        reason = "ok" if allowed else "failed: " + ",".join(k for k, v in checks.items() if not v)
        if span is not None:
            try:
                span.set_attribute("safety.allowed", allowed)
                span.set_attribute("safety.reason", reason)
            except Exception:  # noqa: BLE001
                pass
        return ValidationResult(allowed=allowed, reason=reason, checks=checks)


def _first_node_released(order: dict) -> bool:
    """VDA 5050: the base of an order (the first node) must be released for the AGV to start."""
    nodes = order.get("nodes") or []
    return bool(nodes) and bool(nodes[0].get("released", False))


def require_allowed(result: ValidationResult) -> None:
    """Raise if a dispatch is attempted without an allowing result (the hard gate)."""
    if not result.allowed:
        raise SafetyValidationError(f"actuator dispatch blocked by safety gate: {result.reason}")


# ---- Stage 17: the SIL-rated contract validator (KB_17 §"Validator flow") -----------------------

def _safe_check(fn, *args) -> bool:
    """Run a contract check defensively: any exception in a check = the check FAILED (fail-safe, never crashes the gate)."""
    try:
        return bool(fn(*args))
    except Exception:  # noqa: BLE001
        return False


def validate(action: Action, world_state: dict, contract: SafetyContract) -> Decision:
    """SIL-rated pre-flight gate. Checks preconditions + invariants against `world_state`, then routes by SIL. A failed
    check BLOCKS (allow=False), records a signed `audit_chain` row, and names the contract's `fail_safe_path`. Emits a
    `safety.validate` span (the CI invariant: precedes the `actuator.*` span)."""
    from observability.otel_init import traced_span

    with traced_span("safety.validate",
                     **{"safety.kind": "contract", "safety.contract": contract.name, "safety.sil": contract.sil}) as span:
        failed = [f"precondition:{p.name}" for p in contract.preconditions if not _safe_check(p.check, world_state)]
        failed += [f"invariant:{i.name}" for i in contract.invariants if not _safe_check(i.check, world_state)]

        if failed:
            reason = "blocked: " + ",".join(failed)
            try:
                from observability.evidence_sink import record
                record("safety.validator", "precondition_fail",
                       {"action": action.model_dump(), "contract": contract.name, "failed": failed,
                        "fail_safe_path": contract.fail_safe_path})
            except Exception:  # noqa: BLE001 - audit best-effort; the block stands regardless
                pass
            _set(span, allowed=False, reason=reason)
            return Decision(allow=False, route="blocked", reason=reason, contract=contract.name,
                            sil=contract.sil, fail_safe_path=contract.fail_safe_path, failed_checks=failed)

        route = "sil_bridge" if contract.sil >= 2 else ("operator_confirm" if contract.sil == 1 else "direct")
        _set(span, allowed=True, reason=f"ok:route={route}")
        # Stage 33 (G-075): mint an unforgeable, action-bound capability token so the executor can reject a forged or
        # stale Decision (research §44.1). This is the ONLY place a token is minted (only on an ALLOW after real checks).
        from safety.capability_token import mint
        tok = mint(allow=True, route=route, contract=contract.name, sil=contract.sil, action=action)
        return Decision(allow=True, route=route, reason="ok", contract=contract.name, sil=contract.sil,
                        fail_safe_path=contract.fail_safe_path,
                        token=tok["token"], nonce=tok["nonce"], issued_at=tok["issued_at"])


def check_postconditions(contract: SafetyContract, before: dict, after: dict) -> list[str]:
    """Run after actuation. Returns the names of any VIOLATED postconditions (empty = all held)."""
    return [pc.name for pc in contract.postconditions if not _safe_check(pc.check, before, after)]


def _set(span, *, allowed: bool, reason: str) -> None:
    if span is not None:
        try:
            span.set_attribute("safety.allowed", allowed)
            span.set_attribute("safety.reason", reason)
        except Exception:  # noqa: BLE001
            pass


__all__ = ["ValidationResult", "SafetyValidationError", "validate_order", "require_allowed",
           "validate", "check_postconditions"]
