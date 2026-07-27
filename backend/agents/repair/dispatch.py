"""Stage 30 (G-005) — repair-robot dispatch via a deterministic Contract-Net + the repair safety gate (research §41.1).

A machine breaks → ANNOUNCE a repair CFP → each AVAILABLE robot bids a REAL cost (from its live state: availability,
battery, queue depth) → AWARD the min-cost robot (deterministic, stable tie-break) → route the award through
`safety/validator.validate()` under the `repair_dispatch` contract BEFORE any effect (Hard Rule 3) → the robot travels
(delay = its bid cost) and applies `repair_assist`, cutting the broken stage's REMAINING downtime. Every CFP+award is
signed to `audit_chain` (surfaced-failure pattern). Deterministic: same robot state + same CFP → same award.

Honesty notes:
 * Robots have NO physical position in this SimWorld (only battery/status/queue), so the cost uses those REAL signals,
   NOT a fabricated distance — physical proximity routing is a pilot/real-fleet concern (noted, G-035-adjacent).
 * `repair_assist` is a no-op if the stage already recovered — no fabricated benefit; the A/B measures the REAL
   downtime delta the dispatch produced.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from safety.contract import Action, Invariant, Precondition, SafetyContract

# ---------------------------------------------------------------------------
# The repair-dispatch contract (static, code-defined — Hard Rule 3 / KB_17)
# ---------------------------------------------------------------------------

REPAIR_DISPATCH_CONTRACT = SafetyContract(
    name="repair_dispatch",
    sil=1,  # dispatching a robot into a cell is a low-SIL motion function — GATED (HITL at SIL-1+ upstream)
    iso_clauses=["ISO 10218-2 (integration)", "EU AI Act Art-12 (record-keeping)"],
    preconditions=[
        Precondition(name="stage_is_broken",
                     description="only dispatch a repair to a machine that is actually down",
                     check=lambda ws: str(ws.get("stage_status", "")).lower() == "broken"),
        Precondition(name="robot_available",
                     description="the awarded robot is idle with usable charge (not fault/charging/flat)",
                     check=lambda ws: bool(ws.get("robot_available", False))),
        Precondition(name="reduction_bounded",
                     description="the repair-assist reduction is a sane fraction",
                     check=lambda ws: 0.0 < float(ws.get("reduction_frac", 0.0)) <= 0.95),
    ],
    invariants=[
        Invariant(name="one_robot_one_award",
                  description="a single robot id is awarded (no double-dispatch in a round)",
                  check=lambda ws: ws.get("robot_id") is not None),
    ],
    fail_safe_path="no_action",
)

# Dispatch cost/assist parameters (documented modelling constants — a repair crew's effectiveness, not fabrication).
_BASE_TRAVEL_S = 5.0            # baseline response time for an ideal idle+full robot
_BATTERY_WEIGHT_S = 20.0       # a flatter battery responds slower (must partial-charge / move cautiously)
_QUEUE_WEIGHT_S = 8.0          # a robot with queued transport tasks takes longer to free up
_MIN_BATTERY = 0.15            # below this a robot cannot be dispatched (must charge first)
_DEFAULT_REDUCTION = 0.6       # a repair crew cuts the REMAINING downtime by this fraction on arrival


@dataclass(frozen=True)
class RepairBid:
    robot_id: int
    cost: float                # seconds-to-respond, derived from real state
    basis: str


@dataclass
class RepairAward:
    stage_id: int
    robot_id: Optional[int]    # None = no available robot (honest no-award)
    cost: Optional[float]
    reduction_frac: float
    allowed: bool = False
    gate_reason: str = ""
    audit_seq: Optional[int] = None
    audited: bool = False
    bids: list[RepairBid] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"stage_id": self.stage_id, "robot_id": self.robot_id,
                "cost": None if self.cost is None else round(self.cost, 3),
                "reduction_frac": self.reduction_frac, "allowed": self.allowed,
                "gate_reason": self.gate_reason, "n_bids": len(self.bids),
                "audit_seq": self.audit_seq, "audited": self.audited}


def _bid_cost(robot: dict[str, Any]) -> Optional[tuple[float, str]]:
    """Real response-cost for a robot, or None if it cannot bid (fault/charging/flat). No RNG, no fabrication."""
    status = str(robot.get("status", "")).lower()
    battery = float(robot.get("battery", 0.0))
    if status != "idle" or battery < _MIN_BATTERY:
        return None
    queue_len = int(robot.get("queue_len", 0))
    cost = _BASE_TRAVEL_S + (1.0 - battery) * _BATTERY_WEIGHT_S + queue_len * _QUEUE_WEIGHT_S
    basis = f"idle, battery={round(battery, 3)}, queue={queue_len}"
    return cost, basis


def _audit(action: str, payload: dict[str, Any]) -> tuple[Optional[int], bool]:
    try:
        from memory.audit_chain import append
        return append("agent:repair", action, payload), True
    except Exception:  # noqa: BLE001 — DB/crypto down: surfaced, never fabricated
        return None, False


class RepairDispatcher:
    """Deterministic Contract-Net repair dispatcher over real robot state."""

    def __init__(self, reduction_frac: float = _DEFAULT_REDUCTION):
        self.reduction_frac = max(0.0, min(0.95, float(reduction_frac)))

    def collect_bids(self, robots: list[dict[str, Any]]) -> list[RepairBid]:
        bids: list[RepairBid] = []
        for r in sorted(robots, key=lambda x: int(x.get("id", 0))):
            got = _bid_cost(r)
            if got is None:
                continue
            cost, basis = got
            bids.append(RepairBid(robot_id=int(r["id"]), cost=cost, basis=basis))
        return bids

    def award(self, stage_id: int, stage_status: str, robots: list[dict[str, Any]]) -> RepairAward:
        """Announce a repair CFP for `stage_id`, collect real bids, award min-cost, safety-gate. No effect here."""
        _audit("repair.cfp", {"stage_id": stage_id, "stage_status": stage_status, "n_robots": len(robots)})
        bids = self.collect_bids(robots)
        if not bids:
            aw = RepairAward(stage_id=stage_id, robot_id=None, cost=None, reduction_frac=self.reduction_frac,
                             allowed=False, gate_reason="no available repair robot (honest no-award)", bids=[])
            aw.audit_seq, aw.audited = _audit("repair.award", {"stage_id": stage_id, "awarded": None,
                                                               "reason": aw.gate_reason})
            return aw
        best = min(bids, key=lambda b: (b.cost, b.robot_id))   # min cost, stable tie-break by id
        # SAFETY GATE (Hard Rule 3): validate BEFORE any dispatch effect.
        from safety.validator import validate
        world_state = {
            "stage_status": stage_status, "robot_available": True, "robot_id": best.robot_id,
            "reduction_frac": self.reduction_frac,
        }
        action = Action(contract=REPAIR_DISPATCH_CONTRACT.name, actuator="robot.repair_dispatch",
                        params={"stage_id": stage_id, "reduction_frac": self.reduction_frac},
                        target=f"robot:{best.robot_id}")
        decision = validate(action, world_state, REPAIR_DISPATCH_CONTRACT)
        aw = RepairAward(stage_id=stage_id, robot_id=best.robot_id, cost=best.cost,
                         reduction_frac=self.reduction_frac, allowed=decision.allow,
                         gate_reason=decision.reason, bids=bids)
        aw.audit_seq, aw.audited = _audit("repair.award", {
            "stage_id": stage_id, "awarded": best.robot_id, "cost": round(best.cost, 3),
            "n_bids": len(bids), "gate_allow": decision.allow, "gate_reason": decision.reason})
        return aw


def dispatch_repair(world: Any, stage_id: int, *, reduction_frac: float = _DEFAULT_REDUCTION) -> RepairAward:
    """Convenience: award + (if allowed) actually dispatch over a live SimWorld. Honest no-op if not broken / no robot."""
    stage = world.stages.get(stage_id)
    if stage is None:
        raise KeyError(f"dispatch_repair: unknown stage {stage_id}")
    stage_status = stage.snapshot().get("status", "")
    robots = [r.snapshot() for r in world.robots.values()]
    aw = RepairDispatcher(reduction_frac=reduction_frac).award(stage_id, stage_status, robots)
    if aw.allowed and aw.robot_id is not None:
        # travel delay = the winning robot's real response cost; the assist applies on arrival.
        world.request_repair(stage_id, aw.reduction_frac, travel_seconds=aw.cost or 0.0)
    return aw


__all__ = ["RepairBid", "RepairAward", "RepairDispatcher", "REPAIR_DISPATCH_CONTRACT", "dispatch_repair"]
