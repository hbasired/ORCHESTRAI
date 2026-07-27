"""Stage 38 — peak-shaving + load-shifting energy optimiser as a REAL MILP (research §49).

Given the facility's schedulable stage-loads, a ToU + demand-charge tariff, and each load's required run-hours + allowed
window, decide the schedule x[j,t] ∈ {0,1} (stage j runs in slot t) that minimises the true bill:

    minimise   Σ_t Σ_j (kw_j · slot_h · price_t) · x[j,t]        # ToU energy cost of the shiftable loads
             + demand_charge · peak                              # demand charge on the day's aggregate peak
    s.t.       Σ_t x[j,t] = required_slots[j]        ∀ j          # every stage delivers its full production (the floor)
               x[j,t] = 0   for t ∉ window[j]                     # respect each load's allowed window
               peak ≥ base_t + Σ_j kw_j · x[j,t]     ∀ t          # peak dominates every slot's aggregate kW
               x[j,t] ∈ {0,1},  peak ≥ 0

Solved with `scipy.optimize.milp` (HiGHS — free, already installed; Rule 9). This is genuine optimisation, not a
hand-coded heuristic (Hard Rule 11). Honest fallback: if `milp` is unavailable, a deterministic greedy
cheapest-slots-first load-shift, LABELLED `method="greedy"` — never a fabricated result. The equality constraint
Σ_t x[j,t] = required_slots[j] is the production-floor guarantee: shifting NEVER reduces total output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agents.facilities.signals import FacilityProfile
from agents.facilities.tariff import Tariff


@dataclass
class EnergyPlan:
    """The optimised schedule + its measured bill."""
    schedule: dict[int, list[int]]              # stage_id -> sorted list of slots it runs in
    load_kw_by_slot: list[float]                # aggregate facility kW per slot under this schedule
    bill: dict[str, float]                      # tariff.bill(...) of load_kw_by_slot
    method: str                                 # "milp" | "greedy"
    feasible: bool = True
    meta: dict = field(default_factory=dict)


def _aggregate(profile: FacilityProfile, schedule: dict[int, list[int]]) -> list[float]:
    """Aggregate facility kW per slot: baseline + every scheduled stage that is running that slot."""
    load = profile.base_by_slot()
    by_id = {l.stage_id: l for l in profile.loads}
    for sid, slots in schedule.items():
        kw = by_id[sid].kw
        for t in slots:
            load[t] += kw
    return [round(v, 6) for v in load]


def _greedy(profile: FacilityProfile, tariff: Tariff) -> EnergyPlan:
    """Deterministic fallback: place each load in its cheapest allowed slots (ties → earliest). No RNG, no fabrication.

    Loads are placed largest-kW-first (they dominate the peak); within a load, slots are chosen by ascending
    (energy_price, slot). This reduces ToU cost but does NOT co-optimise the peak the way the MILP does — hence it is
    the honest fallback, clearly labelled.
    """
    schedule: dict[int, list[int]] = {}
    for load in sorted(profile.loads, key=lambda l: (-l.kw, l.stage_id)):
        allowed = load.window(profile.horizon_slots)
        chosen = sorted(allowed, key=lambda t: (tariff.energy_price(t), t))[: load.required_slots]
        schedule[load.stage_id] = sorted(chosen)
    load_kw = _aggregate(profile, schedule)
    # feasible ⇔ every load got its full required run-hours (its window was wide enough)
    feasible = all(len(schedule[l.stage_id]) == l.required_slots for l in profile.loads)
    return EnergyPlan(schedule=schedule, load_kw_by_slot=load_kw, bill=tariff.bill(load_kw),
                      method="greedy", feasible=feasible)


def optimize_energy(profile: FacilityProfile, tariff: Optional[Tariff] = None, *, prefer: str = "milp") -> EnergyPlan:
    """Optimise the facility's schedulable loads. Returns an `EnergyPlan` (method labelled honestly)."""
    tariff = tariff or Tariff(horizon_slots=profile.horizon_slots)
    if prefer == "milp":
        try:
            return _solve_milp(profile, tariff)
        except Exception:  # noqa: BLE001 — solver unavailable / infeasible model → honest labelled fallback
            pass
    return _greedy(profile, tariff)


def _solve_milp(profile: FacilityProfile, tariff: Tariff) -> EnergyPlan:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    T = profile.horizon_slots
    loads = profile.loads
    J = len(loads)
    base = profile.base_by_slot()
    slot_h = tariff.slot_hours
    prices = tariff.prices()

    # Variable layout: x[j*T + t] for j in 0..J-1, t in 0..T-1 ; then peak at index J*T.
    n = J * T + 1
    peak_idx = J * T

    def xi(j: int, t: int) -> int:
        return j * T + t

    # Objective: Σ kw_j·slot_h·price_t·x[j,t] + demand_charge·peak   (base load is constant → omitted, added back in bill)
    c = np.zeros(n)
    for j, load in enumerate(loads):
        for t in range(T):
            c[xi(j, t)] = load.kw * slot_h * prices[t]
    c[peak_idx] = tariff.demand_charge_per_kw

    # Bounds: x ∈ [0,1] but 0 outside the load's window; peak ≥ 0.
    lb = np.zeros(n)
    ub = np.ones(n)
    for j, load in enumerate(loads):
        allowed = set(load.window(T))
        for t in range(T):
            if t not in allowed:
                ub[xi(j, t)] = 0.0
    ub[peak_idx] = np.inf
    bounds = Bounds(lb, ub)

    integrality = np.ones(n)
    integrality[peak_idx] = 0  # peak is continuous

    constraints = []
    # (1) Σ_t x[j,t] = required_slots[j]   (production floor — full output delivered).
    for j, load in enumerate(loads):
        row = np.zeros(n)
        for t in range(T):
            row[xi(j, t)] = 1.0
        constraints.append(LinearConstraint(row, load.required_slots, load.required_slots))
    # (2) peak - Σ_j kw_j·x[j,t] ≥ base_t   ∀ t   (peak dominates every slot's aggregate).
    for t in range(T):
        row = np.zeros(n)
        row[peak_idx] = 1.0
        for j, load in enumerate(loads):
            row[xi(j, t)] = -load.kw
        constraints.append(LinearConstraint(row, base[t], np.inf))

    res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)
    if not res.success or res.x is None:
        raise RuntimeError(f"MILP infeasible/failed: {getattr(res, 'message', 'no solution')}")

    x = res.x
    schedule: dict[int, list[int]] = {}
    for j, load in enumerate(loads):
        slots = [t for t in range(T) if x[xi(j, t)] > 0.5]
        schedule[load.stage_id] = sorted(slots)
    load_kw = _aggregate(profile, schedule)
    return EnergyPlan(schedule=schedule, load_kw_by_slot=load_kw, bill=tariff.bill(load_kw), method="milp",
                      feasible=True, meta={"solver": "HiGHS", "objective": round(float(res.fun), 4)})


def baseline_plan(profile: FacilityProfile, tariff: Optional[Tariff] = None) -> EnergyPlan:
    """The naive 'run everything as early as possible' schedule — the A/B baseline (no shifting, no peak awareness)."""
    tariff = tariff or Tariff(horizon_slots=profile.horizon_slots)
    schedule: dict[int, list[int]] = {}
    for load in profile.loads:
        allowed = load.window(profile.horizon_slots)
        schedule[load.stage_id] = sorted(allowed[: load.required_slots])   # earliest slots
    load_kw = _aggregate(profile, schedule)
    return EnergyPlan(schedule=schedule, load_kw_by_slot=load_kw, bill=tariff.bill(load_kw), method="baseline")


__all__ = ["EnergyPlan", "optimize_energy", "baseline_plan"]
