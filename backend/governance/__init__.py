"""Stage 23 — governance access-control layer (KB_18 wishlist G-028/G-029/G-030; research §33.4).

Composes with the Stage-17 zero-trust gateway (NIST SP 800-207) + the functional-safety wrapper:
  - `mac`         — Bell-LaPadula confidentiality MAC (no-read-up / no-write-down); the safety wrapper is the Biba dual.
  - `rbac`        — agent-hierarchy + function-scoped RBAC (L3 embodied → L2 heads → L1 workers → L0 peers).
  - `traceability`— total-traceability helper: state_snapshot(pre/post) + decision → audit_chain (EU AI Act Art-12).

Every allow/deny is audited to `audit_chain` (best-effort; the decision itself is pure + DB-independent — honest
degradation marks `audited=False` rather than failing the lattice or faking a record).
"""
from governance.mac import MacDecision, SecurityLabel, can_read, can_write, dominates  # noqa: F401
from governance.rbac import AgentTier, RbacDecision, check_function_access  # noqa: F401

__all__ = [
    "SecurityLabel", "MacDecision", "dominates", "can_read", "can_write",
    "AgentTier", "RbacDecision", "check_function_access",
]
