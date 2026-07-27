"""Stage 30 (G-005) — A/B: repair-robot DISPATCH vs passive MTTR recovery (HONEST SimWorld study, research §41.1).

Paired, seeded replicates (same seed → identical breakdown pattern per arm) over the SAME horizon with the SAME
injected cracks. The ONLY difference between arms is the recovery policy:

  A control  — passive: a broken machine waits out its full (stochastic) MTTR, unchanged legacy behaviour.
  B dispatch — on each NEW breakdown the coordinator dispatches the best available repair robot via the deterministic
               Contract-Net (`agents.repair.dispatch`), safety-gated; the robot travels (real bid cost) and applies
               `repair_assist`, cutting the REMAINING downtime.

Metric per run: total_downtime_seconds = sum over stages of `time_broken_seconds` at the horizon (lower is better),
plus repair_dispatches (arm B only). Output: paired per-seed rows + mean difference + 95% CI (t-based, n-1 dof).

HONESTY: SimWorld, not a real fleet (real-data validation = G-035, buyer-blocked). Robots have no physical position
in this model, so the dispatch cost uses real availability/battery/queue, not a fabricated distance. If dispatch does
NOT help on a seed, that is the reported result.

    python scripts/run_repair_ab.py --seeds 10 --hours 6 --out training/evals/results/repair_ab.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TICK_S = 300.0
CRACK_STAGES = [1, 3, 5, 7]          # force guaranteed early breakdowns (natural MTBF adds more)
CRACK_AT_TICK = 3
CRACK_ETA_S = 480.0


def _run(seed: int, ticks: int, *, dispatch: bool) -> dict:
    from simulation.sim_world import SimWorld
    world = SimWorld(seed=seed)
    dispatched_at: dict[int, int] = {}     # stage_id -> breakdown_count last dispatched (once per episode)
    n_dispatch = 0

    for i in range(ticks):
        world.env.run(until=(i + 1) * TICK_S)
        if i == CRACK_AT_TICK:
            for sid in CRACK_STAGES:
                if sid in world.stages:
                    world.stages[sid].schedule_crack(CRACK_ETA_S)
        if dispatch:
            for sid, stage in world.stages.items():
                snap = stage.snapshot()
                if snap.get("status") == "broken":
                    bc = int(snap.get("breakdown_count", 0))
                    if dispatched_at.get(sid) != bc:      # a NEW breakdown episode
                        from agents.repair.dispatch import dispatch_repair
                        aw = dispatch_repair(world, sid)
                        if aw.allowed and aw.robot_id is not None:
                            dispatched_at[sid] = bc
                            n_dispatch += 1
    world.env.run(until=ticks * TICK_S + 1.0)
    total_downtime = sum(s.snapshot().get("time_broken_seconds", 0.0) for s in world.stages.values())
    total_breakdowns = sum(int(s.snapshot().get("breakdown_count", 0)) for s in world.stages.values())
    return {"total_downtime_seconds": round(total_downtime, 1), "breakdowns": total_breakdowns,
            "repair_dispatches": n_dispatch}


# two-sided t_{0.975, dof} critical values (dof = n-1); covers the seed counts this harness is run with.
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
         9: 2.262, 10: 2.228, 14: 2.145, 19: 2.093, 29: 2.045}


def _t975(dof: int) -> float:
    if dof in _T975:
        return _T975[dof]
    # nearest available dof <= requested (conservative), else the largest tabulated.
    lowers = [k for k in _T975 if k <= dof]
    return _T975[max(lowers)] if lowers else 1.96


def _ci95(diffs: list[float]) -> tuple[float, float, float]:
    n = len(diffs)
    m = mean(diffs)
    if n < 2:
        return m, m, m
    sd = math.sqrt(sum((d - m) ** 2 for d in diffs) / (n - 1))
    se = sd / math.sqrt(n)
    t = _t975(n - 1)                # correct two-sided 95% t critical value for this sample size
    return m, m - t * se, m + t * se


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--out", default="training/evals/results/repair_ab.json")
    args = ap.parse_args()
    ticks = int(args.hours * 3600 / TICK_S)

    rows = []
    diffs = []
    for s in range(42, 42 + args.seeds):
        control = _run(s, ticks, dispatch=False)
        disp = _run(s, ticks, dispatch=True)
        diff = control["total_downtime_seconds"] - disp["total_downtime_seconds"]  # >0 = dispatch saved downtime
        rows.append({"seed": s, "control": control, "dispatch": disp, "downtime_saved_seconds": round(diff, 1)})
        diffs.append(diff)
        print(f"seed {s}: control {control['total_downtime_seconds']:.0f}s  dispatch {disp['total_downtime_seconds']:.0f}s"
              f"  saved {diff:.0f}s  ({disp['repair_dispatches']} dispatches)")

    m, lo, hi = _ci95(diffs)
    ctrl_mean = mean(r["control"]["total_downtime_seconds"] for r in rows)
    pct = 100.0 * m / ctrl_mean if ctrl_mean else 0.0
    out = {
        "design": "paired seeds, identical cracks; only difference = repair-dispatch vs passive MTTR",
        "seeds": args.seeds, "hours": args.hours,
        "control_mean_downtime_seconds": round(ctrl_mean, 1),
        "mean_downtime_saved_seconds": round(m, 1),
        "downtime_saved_pct": round(pct, 1),
        "ci95_saved_seconds": [round(lo, 1), round(hi, 1)],
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "honest_label": "SimWorld study (not a real fleet); real-data validation = G-035 (buyer-blocked)",
        "rows": rows,
    }
    out_path = BACKEND / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nmean downtime saved {m:.0f}s ({pct:.1f}%), 95% CI [{lo:.0f}, {hi:.0f}]"
          f"  (excludes 0: {out['ci_excludes_zero']}) -> {out_path}")


if __name__ == "__main__":
    main()
