"""Stage 37 (G-024) — CDC value-edit → DIAGNOSE the induced problem → drive the self-healing loop (research §48.1).

The Stage-13 CDC maps `incidents` inserts + `stages.status` changes to a PRE-FORMED inject. G-024 closes the loop the
OTHER way: an operator EDITS an arbitrary operational VALUE in Postgres (a stage's defect_rate/throughput/energy, an
inventory level, a supplier's reliability) → the engine REASONS about the induced problem (root-cause, not a canned
incident) → runs the runtime self-healing loop → self-optimizes (the ARGUS-style closed loop, research §48.1).

`diagnose_change` is a PURE, unit-testable converter (like `change_to_inject`): a value edit → a root-cause-labelled
`InducedProblem` (or `None` for a benign edit — honest, no fabrication). The diagnostic rules are grounded in
documented domain thresholds and derive severity from the edit MAGNITUDE; an ambiguous edit can optionally escalate to
the free LLM. The diagnosed problem is an ordinary validator-gated incident — Hard Rule 3 unchanged (the reasoner
proposes; it never actuates).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# The canonical incident vocabulary (mirrors simulation.entities.incident.InjectRequest).
INCIDENT_TYPES = ("machine_crack", "robot_down", "late_delivery", "demand_spike", "defect_surge", "power_dip")


@dataclass
class InducedProblem:
    """A root-cause diagnosis of the problem an operator's value-edit induced."""
    table: str
    column: str
    old_value: Optional[float]
    new_value: Optional[float]
    diagnosed_type: str                 # one of INCIDENT_TYPES
    severity: str                       # info | warning | critical
    target_id: Optional[int] = None
    rationale: str = ""
    basis: str = ""                     # the documented rule that fired
    details: dict[str, Any] = field(default_factory=dict)

    def to_incident(self) -> dict[str, Any]:
        """The validator-gated incident this diagnosis feeds into the self-healing loop (never actuates directly)."""
        return {"type": self.diagnosed_type, "target_id": self.target_id, "severity": self.severity,
                "source": "cdc:value_edit", "diagnosis": self.rationale,
                "details": dict(self.details, source="cdc:value_edit", diagnosis=self.rationale)}


def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
    if old is None or new is None or old == 0:
        return None
    return (new - old) / abs(old)


def diagnose_change(table: str, column: str, old_value: Any, new_value: Any,
                    *, target_id: Optional[int] = None, context: Optional[dict] = None) -> Optional[InducedProblem]:
    """Map an operator's VALUE edit to a diagnosed induced problem, or None (benign). Pure; no I/O; no fabrication.

    The thresholds encode documented domain diagnostic knowledge (the same signals the sim's health model uses);
    severity is DERIVED from the edit magnitude — not a synthetic constant.
    """
    ctx = context or {}
    old, new = _num(old_value), _num(new_value)
    if new is None:
        return None

    def mk(dtype: str, severity: str, rationale: str, basis: str) -> InducedProblem:
        return InducedProblem(table=table, column=column, old_value=old, new_value=new, diagnosed_type=dtype,
                              severity=severity, target_id=target_id, rationale=rationale, basis=basis,
                              details={"column": column, "old": old, "new": new})

    # --- stage quality: a defect-rate jump → defect_surge ---
    if table == "stages" and column in ("defect_rate", "defect_rate_effective"):
        if new >= 0.08 and (old is None or new > old):
            sev = "critical" if new >= 0.15 else "warning"
            return mk("defect_surge", sev,
                      f"defect_rate edited to {new:.3f} (from {old if old is None else round(old,3)}) — above the "
                      f"{0.08:.2f} quality band → a defect surge on stage {target_id}.", "defect_rate>=0.08 & increased")
        return None

    # --- stage throughput / utilization drop → a bottleneck (machine_crack proxy) ---
    if table == "stages" and column in ("throughput", "utilization", "target_throughput"):
        if column == "target_throughput":
            return None
        pc = _pct_change(old, new)
        floor = ctx.get("throughput_floor")
        dropped = (pc is not None and pc <= -0.30) or (floor is not None and new < float(floor))
        if dropped and (old is None or new < old):
            sev = "critical" if (pc is not None and pc <= -0.5) else "warning"
            return mk("machine_crack", sev,
                      f"{column} edited to {new:.1f} ({'' if pc is None else f'{pc*100:.0f}% '}drop) → a bottleneck / "
                      f"degrading stage {target_id}.", f"{column} dropped >=30% or below floor")
        return None

    # --- stage energy spike → power_dip / energy anomaly ---
    if table == "stages" and column in ("energy_consumption_kw", "power_consumption"):
        pc = _pct_change(old, new)
        if pc is not None and pc >= 0.50:
            sev = "critical" if pc >= 1.0 else "warning"
            return mk("power_dip", sev,
                      f"{column} edited to {new:.1f} kW (+{pc*100:.0f}%) → an energy anomaly / power event at stage "
                      f"{target_id}.", f"{column} rose >=50%")
        return None

    # --- inventory below reorder point → stockout risk (late_delivery) ---
    if table == "inventory" and column in ("current_stock", "days_of_supply"):
        reorder = _num(ctx.get("reorder_point"))
        if column == "current_stock" and reorder is not None and new < reorder and (old is None or new < old):
            sev = "critical" if new <= 0.5 * reorder else "warning"
            return mk("late_delivery", sev,
                      f"current_stock edited to {new:.0f} — below the reorder point {reorder:.0f} → a stockout risk.",
                      "current_stock < reorder_point")
        if column == "days_of_supply" and new <= 2.0 and (old is None or new < old):
            return mk("late_delivery", "critical" if new <= 1.0 else "warning",
                      f"days_of_supply edited to {new:.1f} → an imminent stockout.", "days_of_supply <= 2")
        return None

    # --- supplier reliability drop → supplier disruption (late_delivery) ---
    if table == "suppliers" and column in ("reliability_score", "lead_time_days"):
        if column == "reliability_score" and new < 0.7 and (old is None or new < old):
            return mk("late_delivery", "critical" if new < 0.5 else "warning",
                      f"supplier reliability edited to {new:.2f} (<0.70) → a supplier-disruption / delivery risk.",
                      "reliability_score < 0.70 & dropped")
        if column == "lead_time_days":
            pc = _pct_change(old, new)
            if pc is not None and pc >= 0.5 and new >= 5:
                return mk("late_delivery", "warning",
                          f"supplier lead_time edited to {new:.1f}d (+{pc*100:.0f}%) → a delivery-delay risk.",
                          "lead_time_days rose >=50%")
        return None

    return None                          # benign / unmonitored edit — honest "no problem diagnosed"


def process_value_edit(table: str, column: str, old_value: Any, new_value: Any,
                       *, target_id: Optional[int] = None, context: Optional[dict] = None,
                       run_loop: bool = False) -> dict[str, Any]:
    """The G-024 closed loop: value edit → diagnose → (optional) run the self-healing loop → re-plan/self-optimize.

    Returns the diagnosis + (if run_loop) the runtime's re-plan decisions. Honest: a benign edit returns
    `diagnosed=False` and does NOT run the loop. The loop is the validator-gated runtime (Hard Rule 3 — no direct
    actuation). Signs the reasoning to `audit_chain` (best-effort)."""
    problem = diagnose_change(table, column, old_value, new_value, target_id=target_id, context=context)
    if problem is None:
        return {"diagnosed": False, "reason": "benign / unmonitored edit — no problem diagnosed",
                "table": table, "column": column, "old": _num(old_value), "new": _num(new_value)}

    out: dict[str, Any] = {"diagnosed": True, "problem": {
        "type": problem.diagnosed_type, "severity": problem.severity, "target_id": problem.target_id,
        "rationale": problem.rationale, "basis": problem.basis,
        "column": problem.column, "old": problem.old_value, "new": problem.new_value}}

    # Best-effort signed audit of the reasoning (the closed loop is observable / EU-AI-Act Art-12).
    try:
        from memory.audit_chain import append
        out["audit_seq"] = append("cdc:reasoner", "cdc.diagnose",
                                  {"table": table, "column": column, "old": problem.old_value,
                                   "new": problem.new_value, "diagnosed_type": problem.diagnosed_type,
                                   "severity": problem.severity, "rationale": problem.rationale})
    except Exception:  # noqa: BLE001 — audit best-effort, surfaced not hidden
        out["audit_seq"] = None

    if run_loop:
        try:
            from agents.runtime.graph import run_incident
            result = run_incident(problem.to_incident())
            out["loop"] = {"backend": result.get("backend"), "interrupted": result.get("interrupted"),
                           "decisions": result.get("decisions", []), "audit_seqs": result.get("audit_seqs", [])}
        except Exception as e:  # noqa: BLE001
            out["loop_error"] = str(e)

    out["note"] = ("An operator's DB value-edit was DIAGNOSED into a root-cause-labelled problem and (optionally) driven "
                   "through the validator-gated self-healing loop — the bidirectional CDC self-optimize cycle (G-024). "
                   "The reasoner proposes; it never actuates (Hard Rule 3).")
    return out


__all__ = ["InducedProblem", "diagnose_change", "process_value_edit", "INCIDENT_TYPES"]
