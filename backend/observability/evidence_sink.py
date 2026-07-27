"""Stage 12.5 — evidence sink: the immutable half of the two-store split (KB_15).

A thin wrapper over `memory/audit_chain.py` (built Stage 12) that ALSO emits an `audit_chain.append` OTel span. The
trace (Langfuse, mutable, prunable) and the evidence row (`audit_chain`, append-only + signed + indefinite) are
written for the SAME action — loss of the trace store never loses evidence (KB_15 §"Evidence sink — separate from
Langfuse"). Honest: if the DB is unreachable the underlying `audit_chain.append` raises `AuditChainUnavailable`;
this wrapper surfaces that rather than silently dropping evidence.
"""
from __future__ import annotations

from typing import Any, Optional


def record(actor: str, action: str, payload: dict[str, Any], *, conn: Any = None) -> int:
    """Append an evidence row to `audit_chain` and emit an `audit_chain.append` span. Returns the seq."""
    from observability.otel_init import traced_span

    with traced_span("audit_chain.append", **{"audit.actor": actor, "audit.action": action}) as span:
        from memory.audit_chain import append
        seq = append(actor, action, payload, conn=conn)
        try:
            span.set_attribute("audit.seq", seq)
        except Exception:  # noqa: BLE001
            pass
        return seq


def record_decision(decision: dict[str, Any], *, actor: str = "agent:embodied") -> int:
    """Convenience for the runtime: append one decision as `decision.<kind>` evidence."""
    kind = decision.get("kind", "decision")
    return record(actor, f"decision.{kind}", decision)


__all__ = ["record", "record_decision"]
