"""Stage 26 — A/B: multi-agent CNP supply-chain layer vs greedy re-order baseline (HONEST SimWorld study).

Paired, seeded replicates (same seed → same SimWorld stochastics per arm) over the SAME horizon with the SAME
injected mid-run disruption (a 6x-median delivery delay on the arm's most-used supplier + a demand spike — the
Stage-26 drill design). Both arms get the SAME closed material loop (delivery callbacks feed stage buffers).

Arms:
  A greedy  — the naive policy: every tick, each stage below a fixed 20%-capacity threshold orders up to capacity
              from supplier 0 (no coordination, no inventory position, no exploration, no safety gate concept
              beyond the sim's own capacity bound).
  B agentic — `SupplyChainOrchestrator` (demand/inventory/scheduling/logistics/supplier agents + deterministic
              CNP + disruption monitor + safety gate).

Metrics per run (research §37.2):
  stockout_ticks    sum over stages of zero-buffer ticks after warmup (service failure)
  bullwhip          var(order qty per tick) / var(observed demand per tick)  (amplification; lower is better)
  orders_placed     total units ordered (cost proxy)
  units_delivered   fulfilled deliveries that fed a buffer
  mean_buffer_frac  mean buffer fill fraction after warmup (holding-cost proxy — service bought by full buffers)

Output: paired per-seed rows + mean difference + a 95% CI on the paired difference (t-based, n-1 dof).
HONESTY: SimWorld, not a real supply chain (real-data validation = G-035, buyer-blocked). If the greedy baseline
wins a metric, that is the reported result.

    python scripts/run_supply_ab.py --seeds 10 --ticks 120 --out training/evals/results/supply_ab.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean, variance

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TICK_S = 300.0
WARMUP_TICKS = 24          # metrics ignore the cold-start window
DISRUPT_AT_TICK = 60
GREEDY_THRESHOLD_FRAC = 0.2


def _stage_caps(world) -> dict[int, int]:
    return {int(sid): int(stage.cfg.capacity) for sid, stage in world.stages.items()}


def _mk_greedy_delivery(world, stage_id: int, on_order: dict[int, int]):
    def _deliver():
        world.deliver_material(stage_id)
        on_order[stage_id] = max(0, on_order.get(stage_id, 0) - 1)
    return _deliver


def run_greedy(seed: int, ticks: int) -> dict:
    from simulation.sim_world import SimWorld
    world = SimWorld(seed=seed)
    caps = _stage_caps(world)
    on_order: dict[int, int] = {}
    orders_per_tick: list[int] = []
    demand_per_tick: list[float] = []
    stockout_ticks = 0
    delivered = 0
    fill_fracs: list[float] = []

    def _count_delivery(stage_id):
        base = _mk_greedy_delivery(world, stage_id, on_order)
        def _d():
            nonlocal delivered
            base(); delivered += 1
        return _d

    for i in range(ticks):
        world.env.run(until=(i + 1) * TICK_S)
        snap = world.snapshot()
        if i == DISRUPT_AT_TICK:
            world.suppliers[0].delay_next_delivery(6 * 3600.0)  # supplier 0 IS greedy's only source
            world.activate_demand_spike(2.0, 3600.0)
        placed = 0
        for st in snap["stages"]:
            sid = int(st.get("stage_id", st.get("id")))
            depth = int(st["queue_depth"])
            cap = caps.get(sid, 0)
            if cap and depth < GREEDY_THRESHOLD_FRAC * cap:
                qty = cap - depth  # naive: order the whole gap, ignore on-order (the classic over-order)
                for _ in range(qty):
                    world.suppliers[0].order(on_fulfil=_count_delivery(sid))
                    on_order[sid] = on_order.get(sid, 0) + 1
                placed += qty
        orders_per_tick.append(placed)
        demand_per_tick.append(float(snap["throughput_units_per_hour"]))
        if i >= WARMUP_TICKS:
            stockout_ticks += sum(1 for st in snap["stages"] if int(st["queue_depth"]) == 0)
            fill_fracs += [int(st["queue_depth"]) / max(1, caps.get(int(st.get("stage_id", st.get("id"))), 1))
                           for st in snap["stages"]]
    return _metrics("greedy", orders_per_tick, demand_per_tick, stockout_ticks, delivered, fill_fracs)


def run_agentic(seed: int, ticks: int) -> dict:
    from simulation.sim_world import SimWorld
    from agents.supply_chain import SupplyChainOrchestrator
    world = SimWorld(seed=seed)
    orch = SupplyChainOrchestrator(world, service_z=2.33)
    orch.ground_in_graph()  # honest: reports False when Neo4j is down; topology comes from the sim then
    caps = _stage_caps(world)
    orders_per_tick: list[int] = []
    demand_per_tick: list[float] = []
    stockout_ticks = 0
    delivered_before = 0
    fill_fracs: list[float] = []

    last_winner = 0
    for i in range(ticks):
        world.env.run(until=(i + 1) * TICK_S)
        if i == DISRUPT_AT_TICK:
            s = orch.observer.suppliers.get(last_winner)
            med = (s.lead_median_s if s and s.lead_median_s else 3600.0)
            world.suppliers[last_winner].delay_next_delivery(6 * med)
            world.activate_demand_spike(2.0, 3600.0)
        r = orch.tick()
        for a in r.awards:
            if a.allowed and a.supplier_id is not None:
                last_winner = a.supplier_id
        orders_per_tick.append(r.orders_placed)
        snap = world.snapshot()
        demand_per_tick.append(float(snap["throughput_units_per_hour"]))
        if i >= WARMUP_TICKS:
            stockout_ticks += sum(1 for st in snap["stages"] if int(st["queue_depth"]) == 0)
            fill_fracs += [int(st["queue_depth"]) / max(1, caps.get(int(st.get("stage_id", st.get("id"))), 1))
                           for st in snap["stages"]]
    delivered = sum(s.fulfilled for s in orch.observer.suppliers.values()) - delivered_before
    return _metrics("agentic", orders_per_tick, demand_per_tick, stockout_ticks, delivered, fill_fracs)


def _metrics(arm: str, orders: list[int], demand: list[float], stockout_ticks: int, delivered: int,
             fill_fracs: list[float]) -> dict:
    o, d = orders[WARMUP_TICKS:], demand[WARMUP_TICKS:]
    var_o = variance(o) if len(set(o)) > 1 else 0.0
    var_d = variance(d) if len(set(d)) > 1 else 0.0
    return {"arm": arm, "stockout_ticks": stockout_ticks,
            "bullwhip": (var_o / var_d) if var_d > 0 else None,
            "orders_placed": sum(orders), "units_delivered": delivered,
            "mean_buffer_frac": round(mean(fill_fracs), 3) if fill_fracs else None}


def paired_ci(diffs: list[float], level_t: float = 2.262) -> dict:
    """95% CI on the mean paired difference (t distribution; default t for n=10 → dof 9 = 2.262)."""
    n = len(diffs)
    mu = mean(diffs)
    if n < 2:
        return {"mean": mu, "lo": None, "hi": None}
    sd = math.sqrt(variance(diffs))
    half = level_t * sd / math.sqrt(n)
    return {"mean": round(mu, 3), "lo": round(mu - half, 3), "hi": round(mu + half, 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--ticks", type=int, default=120)
    ap.add_argument("--out", type=str, default=str(BACKEND / "training/evals/results/supply_ab.json"))
    args = ap.parse_args()

    rows = []
    for seed in range(1, args.seeds + 1):
        g = run_greedy(seed, args.ticks)
        a = run_agentic(seed, args.ticks)
        rows.append({"seed": seed, "greedy": g, "agentic": a})
        print(f"seed {seed}: greedy stockout={g['stockout_ticks']} bullwhip={g['bullwhip'] and round(g['bullwhip'],2)} "
              f"orders={g['orders_placed']} | agentic stockout={a['stockout_ticks']} "
              f"bullwhip={a['bullwhip'] and round(a['bullwhip'],2)} orders={a['orders_placed']}")

    result = {
        "honest_label": "SimWorld simulation study — NOT real supply-chain evidence (G-035 buyer-blocked)",
        "design": f"paired seeds n={args.seeds}, {args.ticks} ticks x {TICK_S}s, warmup {WARMUP_TICKS}, "
                  f"disruption at tick {DISRUPT_AT_TICK} (6x-median delay on most-used supplier + 2x demand spike)",
        "rows": rows,
        "paired_diff_greedy_minus_agentic": {
            "stockout_ticks": paired_ci([r["greedy"]["stockout_ticks"] - r["agentic"]["stockout_ticks"] for r in rows]),
            "bullwhip": paired_ci([r["greedy"]["bullwhip"] - r["agentic"]["bullwhip"] for r in rows
                                   if r["greedy"]["bullwhip"] is not None and r["agentic"]["bullwhip"] is not None]),
            "orders_placed": paired_ci([r["greedy"]["orders_placed"] - r["agentic"]["orders_placed"] for r in rows]),
            "mean_buffer_frac": paired_ci([r["greedy"]["mean_buffer_frac"] - r["agentic"]["mean_buffer_frac"]
                                           for r in rows if r["greedy"]["mean_buffer_frac"] is not None
                                           and r["agentic"]["mean_buffer_frac"] is not None]),
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["paired_diff_greedy_minus_agentic"], indent=2))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
