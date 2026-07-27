"""Stage 38 — the Facilities / Energy head-agent: the KB_25 predict→diagnose→verify→intervene loop for energy (G-018).

A new embodiment domain (mirrors `agents/supply_chain/`): observe the facility's REAL per-stage energy signals →
PREDICT the demand curve → DIAGNOSE an approaching demand-charge breach / energy anomaly → REASON (the MILP
peak-shaving / load-shifting optimiser) → VERIFY the resulting load-shift through `safety/validator.validate()` under
the code-defined `energy_load_shift` contract (Hard Rule 3 — the agent proposes; `master.dispatch_order` stays the sole
actuator emitter; the LLM never edits contracts, KB_17) → INTERVENE by emitting the gated plan + a signed `audit_chain`
row (`energy.load_shift`, EU-AI-Act Art-12) + an OTel span.

Honest degradation: no DB/crypto → the plan proceeds but is marked un-audited (surfaced, never hidden, never faked).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from safety.contract import Action, Invariant, Precondition, SafetyContract
from agents.facilities.optimizer import EnergyPlan, baseline_plan, optimize_energy
from agents.facilities.signals import FacilityProfile, observe_from_calibration
from agents.facilities.tariff import Tariff

# ---------------------------------------------------------------------------
# The energy load-shift contract (static, code-defined — never LLM-edited, KB_17).
# ---------------------------------------------------------------------------

ENERGY_LOAD_SHIFT_CONTRACT = SafetyContract(
    name="energy_load_shift",
    sil=0,  # energy management is not a safety-of-machinery function; SIL-0 routes "direct" but is STILL gated.
    iso_clauses=["ISO 50001 (energy management)", "ISA-95 Part 3 (operations)", "EU AI Act Art-12 (record-keeping)"],
    preconditions=[
        Precondition(name="production_floor_met",
                     description="the shifted schedule still delivers every stage's required run-hours",
                     check=lambda ws: bool(ws.get("production_floor_met", False))),
        Precondition(name="windows_respected",
                     description="every shifted load stays inside its allowed time window",
                     check=lambda ws: bool(ws.get("windows_respected", False))),
        Precondition(name="peak_not_increased",
                     description="the optimised peak does not EXCEED the baseline peak (never makes demand worse)",
                     check=lambda ws: float(ws.get("optimized_peak_kw", 1e9)) <= float(ws.get("baseline_peak_kw", 0.0)) + 1e-6),
    ],
    invariants=[
        Invariant(name="energy_conserved",
                  description="total delivered energy is unchanged (shifting moves load in time, never drops it)",
                  check=lambda ws: abs(float(ws.get("optimized_kwh", 0.0)) - float(ws.get("required_kwh", -1.0))) <= 1e-3),
    ],
    fail_safe_path="no_action",
)


@dataclass
class EnergyCycleResult:
    plan: EnergyPlan
    baseline: EnergyPlan
    peak_reduction_pct: float
    cost_reduction_pct: float
    diagnosed: Optional[str]              # e.g. "demand_charge_breach" | "energy_anomaly" | None
    allowed: bool = False                # the validator gate
    gate_reason: str = ""
    committed: bool = False              # allowed AND a real reduction → the intervention is applied
    audit_seq: Optional[int] = None
    audited: bool = False
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.plan.method,
            "baseline_peak_kw": self.baseline.bill["peak_kw"], "optimized_peak_kw": self.plan.bill["peak_kw"],
            "baseline_cost": self.baseline.bill["total_cost"], "optimized_cost": self.plan.bill["total_cost"],
            "peak_reduction_pct": round(self.peak_reduction_pct, 2), "cost_reduction_pct": round(self.cost_reduction_pct, 2),
            "diagnosed": self.diagnosed, "allowed": self.allowed, "gate_reason": self.gate_reason,
            "committed": self.committed, "audit_seq": self.audit_seq, "audited": self.audited,
            "schedule": self.plan.schedule, "meta": self.meta,
        }


def _audit(action: str, payload: dict[str, Any]) -> tuple[Optional[int], bool]:
    """Best-effort signed audit row; failure SURFACED via (None, False), never hidden, never fabricated."""
    try:
        from memory.audit_chain import append
        return append("facilities:energy", action, payload), True
    except Exception:  # noqa: BLE001 — DB/crypto down: the plan proceeds but is marked un-audited
        return None, False


class EnergyOrchestrator:
    """The facilities/energy head-agent. `run_cycle` executes the full KB_25 loop for one facility day."""

    def __init__(self, *, demand_cap_kw: Optional[float] = None) -> None:
        self.demand_cap_kw = demand_cap_kw

    def run_cycle(self, profile: Optional[FacilityProfile] = None, tariff: Optional[Tariff] = None,
                  *, required_slots: int = 6) -> EnergyCycleResult:
        # OBSERVE (real per-stage nominal_kw) ------------------------------------------------------------------
        if profile is None:
            profile = observe_from_calibration(required_slots=required_slots)
        tariff = tariff or Tariff(horizon_slots=profile.horizon_slots)

        # PREDICT the demand curve of the naive schedule + DIAGNOSE ---------------------------------------------
        base = baseline_plan(profile, tariff)
        diagnosed: Optional[str] = None
        cap = self.demand_cap_kw
        if cap is not None and base.bill["peak_kw"] > cap:
            diagnosed = "demand_charge_breach"     # the naive schedule's peak would breach the contracted demand cap
        # (No cap ⇒ no breach to diagnose; the loop still runs PROACTIVELY to shave the peak. We do NOT invent an
        #  "anomaly" from peak > process_kw — that is true of ANY overlapping naive schedule, so it would be theatre.)

        # REASON — the MILP peak-shaving / load-shifting optimiser --------------------------------------------
        plan = optimize_energy(profile, tariff, prefer="milp")

        peak_red = (100.0 * (base.bill["peak_kw"] - plan.bill["peak_kw"]) / base.bill["peak_kw"]
                    if base.bill["peak_kw"] > 0 else 0.0)
        cost_red = (100.0 * (base.bill["total_cost"] - plan.bill["total_cost"]) / base.bill["total_cost"]
                    if base.bill["total_cost"] > 0 else 0.0)

        # VERIFY — route the load-shift through the safety validator (Hard Rule 3) -----------------------------
        required_kwh = profile.total_required_kwh()
        by_id = {l.stage_id: l for l in profile.loads}
        optimized_kwh = sum(by_id[sid].kw * len(slots) for sid, slots in plan.schedule.items())
        windows_ok = all(set(slots).issubset(set(next(l for l in profile.loads if l.stage_id == sid).window(profile.horizon_slots)))
                         for sid, slots in plan.schedule.items())
        floor_ok = all(len(plan.schedule.get(l.stage_id, [])) == l.required_slots for l in profile.loads)
        world_state = {
            "production_floor_met": floor_ok, "windows_respected": windows_ok,
            "baseline_peak_kw": base.bill["peak_kw"], "optimized_peak_kw": plan.bill["peak_kw"],
            "optimized_kwh": round(optimized_kwh, 4), "required_kwh": round(required_kwh, 4),
        }
        from safety.validator import validate
        action = Action(contract=ENERGY_LOAD_SHIFT_CONTRACT.name, actuator="energy.load_shift",
                        params={"method": plan.method, "peak_kw": plan.bill["peak_kw"]}, target="facility")
        decision = validate(action, world_state, ENERGY_LOAD_SHIFT_CONTRACT)

        committed = bool(decision.allow and plan.bill["peak_kw"] < base.bill["peak_kw"] - 1e-6)

        # INTERVENE — signed audit row (Art-12) ---------------------------------------------------------------
        seq, audited = _audit("energy.load_shift", {
            "method": plan.method, "diagnosed": diagnosed,
            "baseline_peak_kw": round(base.bill["peak_kw"], 3), "optimized_peak_kw": round(plan.bill["peak_kw"], 3),
            "baseline_cost": base.bill["total_cost"], "optimized_cost": plan.bill["total_cost"],
            "peak_reduction_pct": round(peak_red, 2), "cost_reduction_pct": round(cost_red, 2),
            "gate_allow": decision.allow, "gate_reason": decision.reason, "committed": committed,
        })

        return EnergyCycleResult(
            plan=plan, baseline=base, peak_reduction_pct=peak_red, cost_reduction_pct=cost_red,
            diagnosed=diagnosed, allowed=decision.allow, gate_reason=decision.reason, committed=committed,
            audit_seq=seq, audited=audited,
            meta={"n_stages": profile.meta.get("n_stages"), "base_kw": profile.base_kw,
                  "demand_cap_kw": cap, "horizon_slots": profile.horizon_slots})


__all__ = ["EnergyOrchestrator", "EnergyCycleResult", "ENERGY_LOAD_SHIFT_CONTRACT"]
