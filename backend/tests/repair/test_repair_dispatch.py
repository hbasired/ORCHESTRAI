"""Stage 30 (G-005) — repair-dispatch tests: real-cost bidding, min-cost award, safety gate, honest no-award,
and the interruptible-repair mechanism genuinely shortening downtime (a 1-seed paired A/B)."""
from __future__ import annotations

from agents.repair.dispatch import RepairDispatcher, dispatch_repair


def _robots(spec):
    return [{"id": i, "status": st, "battery": b, "queue_len": q} for i, (st, b, q) in enumerate(spec, start=1)]


def test_only_available_robots_bid_and_min_cost_wins():
    d = RepairDispatcher(reduction_frac=0.6)
    robots = _robots([("idle", 0.9, 0), ("idle", 0.5, 2), ("charging", 0.2, 0), ("fault", 0.0, 0)])
    aw = d.award(stage_id=3, stage_status="broken", robots=robots)
    assert {b.robot_id for b in aw.bids} == {1, 2}          # only the two idle robots bid
    assert aw.robot_id == 1                                  # robot 1 is cheaper (fuller battery, empty queue)
    assert aw.allowed is True


def test_gate_blocks_dispatch_to_a_healthy_machine():
    d = RepairDispatcher()
    aw = d.award(stage_id=3, stage_status="nominal", robots=_robots([("idle", 0.9, 0)]))
    assert aw.allowed is False
    assert "stage_is_broken" in aw.gate_reason


def test_honest_no_award_when_no_robot_available():
    d = RepairDispatcher()
    aw = d.award(stage_id=3, stage_status="broken", robots=_robots([("fault", 0.0, 0), ("charging", 0.1, 0)]))
    assert aw.robot_id is None
    assert "no available repair robot" in aw.gate_reason


def test_flat_battery_robot_cannot_bid():
    d = RepairDispatcher()
    aw = d.award(stage_id=3, stage_status="broken", robots=_robots([("idle", 0.05, 0)]))  # below min battery
    assert aw.robot_id is None


def test_repair_assist_shortens_downtime_vs_passive_recovery():
    """1-seed paired A/B: dispatch cuts total downtime vs. passive MTTR (the real mechanism, not a claim)."""
    from simulation.sim_world import SimWorld

    def run(dispatch: bool) -> float:
        world = SimWorld(seed=42)
        dispatched: set = set()
        for i in range(48):                          # 48 * 300s = 4h
            world.env.run(until=(i + 1) * 300.0)
            if i == 3:
                for sid in (1, 3, 5):
                    world.stages[sid].schedule_crack(480.0)
            if dispatch:
                for sid, stage in world.stages.items():
                    snap = stage.snapshot()
                    if snap["status"] == "broken":
                        key = (sid, snap["breakdown_count"])
                        if key not in dispatched:
                            aw = dispatch_repair(world, sid)
                            if aw.allowed and aw.robot_id is not None:
                                dispatched.add(key)
        world.env.run(until=48 * 300.0 + 1.0)
        return sum(s.snapshot()["time_broken_seconds"] for s in world.stages.values())

    passive = run(dispatch=False)
    active = run(dispatch=True)
    assert passive > 0.0                              # breakdowns did occur (control had downtime)
    assert active < passive                           # dispatch genuinely reduced total downtime
    assert (passive - active) / passive > 0.10        # a material reduction (>10%), same seed / same breakdowns


def test_repair_assist_is_noop_on_a_recovered_stage():
    """repair_assist must not fabricate a benefit on a machine that is not in a broken repair wait."""
    from simulation.sim_world import SimWorld
    world = SimWorld(seed=1)
    world.env.run(until=10.0)
    stage = next(iter(world.stages.values()))
    assert stage.snapshot()["status"] in ("nominal", "degraded")   # not broken
    assert stage.repair_assist(0.6) is False                       # honest no-op
