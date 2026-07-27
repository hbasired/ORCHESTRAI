"""Stage 26 — CONTROLLED disruption drill (injection arm vs no-injection control, same seed).

Methodology adopted from the Stage-26 independent review (2026-07-03), which refuted the first drill's causal
claim by showing a no-injection control produced the same "detection" (a natural lognormal tail draw). A detection
claim is only honest when: (a) the INJECTION arm detects a latency spike for the DELAYED supplier, and (b) the
CONTROL arm (identical seed, no injection) detects NO latency spike anywhere in the same window.

Design: warm the loop; pick the supplier winning awards AT injection time and delay its deliveries by
`--factor` x its observed median for a LONG window (multiple delayed orders get observed); run both arms the same
total ticks; compare event streams.

    python scripts/run_supply_drill.py --seed 42 --warm 60 --post 80 --factor 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TICK_S = 300.0


def run_arm(seed: int, warm: int, post: int, factor: float, inject: bool) -> dict:
    from simulation.sim_world import SimWorld
    from agents.supply_chain import SupplyChainOrchestrator

    world = SimWorld(seed=seed)
    orch = SupplyChainOrchestrator(world)
    last_winner = None
    for i in range(warm):
        world.env.run(until=(i + 1) * TICK_S)
        r = orch.tick()
        for a in r.awards:
            if a.allowed and a.supplier_id is not None:
                last_winner = a.supplier_id
    target = last_winner
    injected_median = None
    if inject and target is not None:
        stats = orch.observer.suppliers.get(target)
        injected_median = stats.lead_median_s if stats and stats.lead_median_s else 3600.0
        # The sim's delay API sets extra = (until - placement): an order placed right after injection gets ~the
        # full window as EXTRA lead. Window = factor x median => early post-window orders arrive ~factor x median
        # late (the structural delay we want observed INSIDE the drill; the first drill's over-long window pushed
        # every delayed fulfilment past the observation horizon — that is why nothing was detected).
        world.suppliers[target].delay_next_delivery(factor * injected_median)
    events: list[dict] = []
    for i in range(warm, warm + post):
        world.env.run(until=(i + 1) * TICK_S)
        r = orch.tick()
        for d in r.disruptions:
            events.append({"tick": i, "event": d})
    return {"arm": "injection" if inject else "control", "target_supplier": target,
            "injected_median_s": injected_median, "events": events,
            "latency_events": [e for e in events if e["event"].startswith("latency_spike")]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--warm", type=int, default=60)
    ap.add_argument("--post", type=int, default=80)
    ap.add_argument("--factor", type=float, default=6.0)
    ap.add_argument("--out", type=str, default=str(BACKEND / "training/evals/results/supply_drill.json"))
    args = ap.parse_args()

    control = run_arm(args.seed, args.warm, args.post, args.factor, inject=False)
    injection = run_arm(args.seed, args.warm, args.post, args.factor, inject=True)

    target = injection["target_supplier"]
    detected_target = any(e["event"] == f"latency_spike@supplier:{target}" for e in injection["latency_events"])
    control_clean = len(control["latency_events"]) == 0
    verdict = "PASS" if (detected_target and control_clean) else "FAIL"

    result = {
        "design": f"seed {args.seed}, warm {args.warm} + post {args.post} ticks x {TICK_S}s, "
                  f"{args.factor}x-median delay on the award-winning supplier for the whole post window; "
                  "control arm = same seed, no injection (independent-review methodology)",
        "control": control, "injection": injection,
        "checks": {"injected_supplier_detected": detected_target,
                   "control_has_no_latency_events": control_clean},
        "verdict": verdict,
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"target=supplier:{target} | injection latency events: "
          f"{[e['event'] for e in injection['latency_events']]} | control latency events: "
          f"{[e['event'] for e in control['latency_events']]}")
    print(f"VERDICT: {verdict}  (written: {out})")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
