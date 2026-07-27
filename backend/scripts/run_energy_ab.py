"""Stage 38 — A/B: MILP peak-shaving / load-shifting energy optimiser vs the naive run-early baseline.

HONEST SimWorld study over the sim's REAL per-stage `nominal_kw` (research §49). The optimiser is DETERMINISTIC (a MILP
over a fixed demand profile needs no RNG), so the "population" here is a PARAMETRIC SWEEP of facility scenarios — not
random seeds — and the aggregate is summarised as mean / std / min / max across the sweep (a t-CI would misrepresent a
non-random sample). Each scenario is a paired comparison on the SAME facility:

  A baseline  — every stage runs its required hours in the EARLIEST allowed slots (no shifting, no peak awareness).
  B optimised — `optimize_energy` (the scipy/HiGHS MILP): minimise ToU energy cost + demand charge, subject to the
                production floor (each stage delivers its full required run-hours) and each load's window.

Metrics per scenario:
  peak_kw          the facility's aggregate demand peak (drives the $/kW demand charge)
  total_cost       the true bill: Σ(kW·h·ToU_price) energy + demand_charge·peak
  peak_reduction   100·(baseline_peak − optimised_peak)/baseline_peak
  cost_reduction   100·(baseline_cost − optimised_cost)/baseline_cost
  floor_ok         every stage still delivers its required run-hours (the optimiser never cuts production)

    python scripts/run_energy_ab.py --out training/evals/results/energy_ab.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, pstdev

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from agents.facilities.optimizer import baseline_plan, optimize_energy   # noqa: E402
from agents.facilities.signals import observe_from_calibration           # noqa: E402
from agents.facilities.tariff import Tariff                              # noqa: E402


def _scenarios():
    """A parametric sweep: production intensity (required run-hours) × window tightness. Deterministic, labelled."""
    horizon = 24
    for req in (4, 6, 8, 10, 12):
        # full-day window (maximally shiftable) and a tighter day-shift window (08:00-20:00)
        for win, name in ((None, "full_day"), ((8, 19), "day_shift")):
            yield {"required_slots": req, "window": win, "window_name": name, "horizon_slots": horizon}


def run_scenario(sc: dict) -> dict:
    prof = observe_from_calibration(horizon_slots=sc["horizon_slots"], required_slots=sc["required_slots"],
                                    window=sc["window"])
    tar = Tariff(horizon_slots=sc["horizon_slots"])
    base = baseline_plan(prof, tar)
    opt = optimize_energy(prof, tar, prefer="milp")
    floor_ok = all(len(opt.schedule.get(l.stage_id, [])) == l.required_slots for l in prof.loads)
    bp, op = base.bill["peak_kw"], opt.bill["peak_kw"]
    bc, oc = base.bill["total_cost"], opt.bill["total_cost"]
    return {
        "scenario": {"required_slots": sc["required_slots"], "window": sc["window_name"]},
        "method": opt.method,
        "baseline_peak_kw": bp, "optimized_peak_kw": op,
        "baseline_cost": bc, "optimized_cost": oc,
        "peak_reduction_pct": round(100.0 * (bp - op) / bp, 3) if bp else 0.0,
        "cost_reduction_pct": round(100.0 * (bc - oc) / bc, 3) if bc else 0.0,
        "floor_ok": floor_ok,
    }


def _agg(vals):
    return {"mean": round(mean(vals), 3), "std": round(pstdev(vals), 3),
            "min": round(min(vals), 3), "max": round(max(vals), 3), "n": len(vals)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="training/evals/results/energy_ab.json")
    args = ap.parse_args()

    rows = [run_scenario(sc) for sc in _scenarios()]
    milp_rows = [r for r in rows if r["method"] == "milp"]
    result = {
        "honest_label": "SimWorld simulation study over the sim's real per-stage nominal_kw — NOT real-facility "
                        "evidence (real-utility tariff + metered load = G-035, buyer-blocked). Deterministic MILP: "
                        "the sweep is parametric (production intensity x window), NOT random seeds; aggregate is "
                        "mean/std/min/max across the sweep (a t-CI would misrepresent a non-random sample).",
        "tariff": {"on_peak_$kwh": 0.28, "mid_peak_$kwh": 0.16, "off_peak_$kwh": 0.10, "demand_$kw_day": 0.60},
        "solver": "scipy.optimize.milp (HiGHS)",
        "n_scenarios": len(rows),
        "all_floor_ok": all(r["floor_ok"] for r in rows),
        "aggregate_milp": {
            "peak_reduction_pct": _agg([r["peak_reduction_pct"] for r in milp_rows]),
            "cost_reduction_pct": _agg([r["cost_reduction_pct"] for r in milp_rows]),
        },
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["aggregate_milp"], indent=2))
    print(f"all production floors held: {result['all_floor_ok']}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
