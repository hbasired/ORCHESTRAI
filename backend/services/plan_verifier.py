"""Stage 8 depth-hardening — neuro-symbolic plan verifier (VERIFY step of KB_25, step 3).

KB_25's self-healing loop is predict -> causally-reason -> **verify** -> intervene. The VERIFY step
was PLANNED-only: "neuro-symbolic grounding (the neural planner proposes ⟂ a formal constraint/logic
engine disposes): enforce pre/post-conditions + safety contracts; reject unsafe plans."

This module is the **symbolic half** of that neuro-symbolic architecture. The *neural* proposer is
the existing stack (the world model / causal diagnosis / RL chooser) that PROPOSES an intervention
plan; this verifier is a deterministic **formal constraint engine** that CHECKS the proposed plan
against declarative pre/post-conditions and safety contracts, and **rejects** any plan that violates
them — before a single actuator moves. No LLM, no randomness, no learning here: it is the auditable,
formally-grounded gate that a learned proposer must pass.

Honest scope: the constraints are an explicit, documented contract over a CAPACITY-fraction throughput
proxy (the real throughput is the SimPy line; the proxy is stated, not hidden). This is the dependency-
light, verifiable core of neuro-symbolic verification — not a full SMT/temporal-logic engine (a future
deepening). It composes with the Stage-17 functional-safety actuator wrapper (KB_17), which it predates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from services.intervention_policy import PREVENTIVE_MAINTENANCE, MONITOR, WAIT_EXTERNAL

# Severities.
HARD = "hard"   # a HARD violation rejects the plan
SOFT = "soft"   # a SOFT violation is recorded as a warning but does not reject


@dataclass(frozen=True)
class PlannedAction:
    """One proposed action in an intervention plan."""

    kind: str               # PREVENTIVE_MAINTENANCE | WAIT_EXTERNAL | MONITOR (intervention_policy vocab)
    stage_id: int
    detail: str = ""

    @property
    def takes_offline(self) -> bool:
        """Does this action take a stage offline (consuming a maintenance crew + line capacity)?"""
        return self.kind == PREVENTIVE_MAINTENANCE


@dataclass
class PlantState:
    """The plant facts the verifier reasons over (a snapshot at the coordination instant)."""

    # per stage_id: {"status": str, "at_risk": bool, "crack_proximity": float}
    stages: dict[int, dict[str, Any]]
    available_crew: int = 1                       # simultaneous maintenance crews (KB_25: "one crew")
    throughput_floor_frac: float = 0.6            # min fraction of stages that must stay ONLINE
    critical_proximity: float = 0.85             # crack_proximity at/above which a machine is "critical"
    max_concurrent_critical_offline: int = 1      # SIL contract: don't down >1 critical machine at once

    def n_stages(self) -> int:
        return len(self.stages)

    def is_online(self, sid: int) -> bool:
        return self.stages.get(sid, {}).get("status") in ("nominal", "degraded")


@dataclass(frozen=True)
class Violation:
    constraint: str
    severity: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"constraint": self.constraint, "severity": self.severity, "detail": self.detail}


@dataclass(frozen=True)
class VerificationResult:
    approved: bool
    violations: tuple[Violation, ...] = ()
    satisfied: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "violations": [v.to_dict() for v in self.violations],
            "satisfied": list(self.satisfied),
            "summary": ("APPROVED — all safety/throughput contracts satisfied" if self.approved
                        else f"REJECTED — {sum(v.severity == HARD for v in self.violations)} hard violation(s)"),
        }


# ---- the declarative constraint contract -----------------------------------
# Each constraint is a pure predicate (plan, state) -> list[Violation] (empty == satisfied).

def _c_target_validity(plan, state) -> list[Violation]:
    out = []
    for a in plan:
        if a.stage_id not in state.stages:
            out.append(Violation("target_validity", HARD, f"action targets unknown stage {a.stage_id}"))
    return out


def _c_maintenance_precondition(plan, state) -> list[Violation]:
    """Can only maintain a machine that is online (not already broken / in maintenance)."""
    out = []
    for a in plan:
        if a.takes_offline:
            st = state.stages.get(a.stage_id, {}).get("status")
            if st in ("broken", "maintenance"):
                out.append(Violation("maintenance_precondition", HARD,
                                     f"stage {a.stage_id} is '{st}' — cannot start planned maintenance"))
    return out


def _c_act_on_risk_only(plan, state) -> list[Violation]:
    """Maintenance is for at-risk machines only; downing a healthy machine wastes capacity (soft)."""
    out = []
    for a in plan:
        if a.takes_offline and not state.stages.get(a.stage_id, {}).get("at_risk", False):
            out.append(Violation("act_on_risk_only", SOFT,
                                 f"stage {a.stage_id} is not at-risk — maintenance may be premature"))
    return out


def _c_crew_capacity(plan, state) -> list[Violation]:
    """No more simultaneous maintenance actions than crews available (KB_25: one crew)."""
    n_maint = sum(1 for a in plan if a.takes_offline)
    if n_maint > state.available_crew:
        return [Violation("crew_capacity", HARD,
                          f"{n_maint} simultaneous maintenance actions but only {state.available_crew} crew available")]
    return []


def _c_throughput_floor(plan, state) -> list[Violation]:
    """Post-condition: the plan must keep at least `floor` fraction of stages online.

    Capacity-fraction proxy (documented): each maintenance action takes one online stage offline;
    projected_online_frac = (online_now - taken_offline) / n_stages must be >= throughput_floor_frac.
    """
    n = state.n_stages()
    if n == 0:
        return []
    online_now = sum(1 for sid in state.stages if state.is_online(sid))
    taken = sum(1 for a in plan if a.takes_offline and state.is_online(a.stage_id))
    projected = (online_now - taken) / n
    if projected < state.throughput_floor_frac - 1e-9:
        need = math.ceil(state.throughput_floor_frac * n)
        return [Violation("throughput_floor", HARD,
                          f"plan leaves {online_now - taken}/{n} stages online "
                          f"({projected:.2f} < floor {state.throughput_floor_frac:.2f}; need >= {need})")]
    return []


def _c_critical_redundancy(plan, state) -> list[Violation]:
    """SIL safety contract: do not take more than `max_concurrent_critical_offline` CRITICAL machines
    offline at once, and do not down a critical machine if a critical one is already broken.
    """
    out = []
    already_critical_down = sum(
        1 for sid, s in state.stages.items()
        if s.get("status") in ("broken", "maintenance") and s.get("crack_proximity", 0.0) >= state.critical_proximity)
    downing_critical = [a.stage_id for a in plan if a.takes_offline
                        and state.stages.get(a.stage_id, {}).get("crack_proximity", 0.0) >= state.critical_proximity]
    total_critical_down = already_critical_down + len(downing_critical)
    if total_critical_down > state.max_concurrent_critical_offline:
        out.append(Violation("critical_redundancy", HARD,
                             f"plan would have {total_critical_down} critical machines offline at once "
                             f"(max {state.max_concurrent_critical_offline}); stages downing-critical={downing_critical}"))
    return out


# Constraint registry (ordered; all evaluated so the report lists every issue).
_CONSTRAINTS: tuple[tuple[str, Callable], ...] = (
    ("target_validity", _c_target_validity),
    ("maintenance_precondition", _c_maintenance_precondition),
    ("crew_capacity", _c_crew_capacity),
    ("throughput_floor", _c_throughput_floor),
    ("critical_redundancy", _c_critical_redundancy),
    ("act_on_risk_only", _c_act_on_risk_only),
)


def from_decisions(decisions) -> list[PlannedAction]:
    """Adapt a list of `InterventionDecision` (intervention_policy) into a plan the verifier checks."""
    plan = []
    for d in decisions:
        kind = getattr(d, "kind", None) or (d.get("kind") if isinstance(d, dict) else None)
        sid = getattr(d, "stage_id", None) if not isinstance(d, dict) else d.get("stage_id")
        plan.append(PlannedAction(kind=kind, stage_id=int(sid), detail=getattr(d, "rationale", "") or ""))
    return plan


def verify(plan, state: PlantState) -> VerificationResult:
    """Verify an intervention plan against the symbolic safety/throughput contract.

    `plan`: list[PlannedAction] (or pass InterventionDecision list through `from_decisions`).
    Returns a VerificationResult; `approved` is False iff any HARD constraint is violated.
    """
    plan = list(plan)
    violations: list[Violation] = []
    satisfied: list[str] = []
    for name, fn in _CONSTRAINTS:
        vs = fn(plan, state)
        violations.extend(vs)
        if not any(v.severity == HARD for v in vs):
            satisfied.append(name)
    approved = not any(v.severity == HARD for v in violations)
    return VerificationResult(approved=approved, violations=tuple(violations), satisfied=tuple(satisfied))


__all__ = [
    "PlannedAction", "PlantState", "Violation", "VerificationResult",
    "verify", "from_decisions", "HARD", "SOFT",
    "PREVENTIVE_MAINTENANCE", "MONITOR", "WAIT_EXTERNAL",
]
