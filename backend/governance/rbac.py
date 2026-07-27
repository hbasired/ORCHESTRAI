"""Stage 23 (G-029) — agent-hierarchy + function-scoped RBAC. Research §33.4; composes with NIST SP 800-207 (Stage 17).

The agent hierarchy (KB_18): L3 embodied (the physical-asset agent) → L2 heads (domain coordinators) → L1 workers
(task agents) → L0 peers (external A2A agents). Access to a FUNCTION CATEGORY is granted by tier (higher tiers inherit
lower-tier functions) PLUS an explicit per-agent grant set (least privilege — an agent only gets the categories it needs).
An L0 external peer gets the narrowest set regardless of any claimed tier (assume-breach). Every allow/deny is best-effort
audited to `audit_chain`. Pure/deterministic; DB-independent decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class AgentTier(IntEnum):
    L0_PEER = 0       # external A2A peer — narrowest, never inherits
    L1_WORKER = 1     # task agent
    L2_HEAD = 2       # domain coordinator
    L3_EMBODIED = 3   # the embodied/physical-asset agent


# Function categories an agent may be granted. The minimum tier that may EVER hold each (least privilege).
FUNCTION_MIN_TIER = {
    "observe": AgentTier.L1_WORKER,        # read telemetry / KPIs
    "diagnose": AgentTier.L1_WORKER,       # run the analytical loop
    "recommend": AgentTier.L2_HEAD,        # produce a coordinator decision
    "memory_write": AgentTier.L2_HEAD,     # write episodic/semantic memory
    "actuate": AgentTier.L3_EMBODIED,      # actuator-bound action (also gated by the SIL validator, Stage 17)
    "safety_override": AgentTier.L3_EMBODIED,
    "a2a_capability": AgentTier.L0_PEER,   # the deliberate external capability subset (read-only forecast)
}


@dataclass(frozen=True)
class RbacDecision:
    allow: bool
    reason: str
    audited: bool = False

    def __bool__(self) -> bool:
        return self.allow


def _audit(agent_id: str, tier: "AgentTier", function: str, allow: bool) -> bool:
    try:
        from memory.audit_chain import append
        append(agent_id or "governance:rbac", "rbac.check",
               {"tier": int(tier), "function": function, "allow": bool(allow)})
        return True
    except Exception:  # noqa: BLE001 - honest: decision stands, audited=False
        return False


def check_function_access(agent_id: str, tier: AgentTier, granted: set[str], function: str,
                          *, audit: bool = True) -> RbacDecision:
    """Allow iff: the function is known, the agent's TIER is >= the function's minimum tier, AND the function is in the
    agent's explicit grant set (least privilege). L0 peers are confined to `a2a_capability` regardless of grants."""
    min_tier = FUNCTION_MIN_TIER.get(function)
    if min_tier is None:
        d = RbacDecision(False, f"unknown function category '{function}'")
    elif tier == AgentTier.L0_PEER and function != "a2a_capability":
        d = RbacDecision(False, f"L0 external peer confined to a2a_capability; '{function}' refused (assume-breach)")
    elif tier < min_tier:
        d = RbacDecision(False, f"tier {tier.name} below minimum {min_tier.name} for '{function}'")
    elif function not in granted:
        d = RbacDecision(False, f"'{function}' not in agent's least-privilege grant set {sorted(granted)}")
    else:
        d = RbacDecision(True, f"{tier.name} granted '{function}'")
    audited = _audit(agent_id, tier, function, d.allow) if audit else False
    return RbacDecision(d.allow, d.reason, audited)


def require_function(agent_id: str, tier: AgentTier, granted: set[str], function: str) -> None:
    d = check_function_access(agent_id, tier, granted, function)
    if not d.allow:
        raise RbacViolation(d.reason)


class RbacViolation(PermissionError):
    """Raised on a denied function-scoped access — never swallowed, never faked."""


__all__ = ["AgentTier", "RbacDecision", "RbacViolation", "FUNCTION_MIN_TIER",
           "check_function_access", "require_function"]
