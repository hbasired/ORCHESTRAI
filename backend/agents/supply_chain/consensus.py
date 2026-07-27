"""Stage 26 — deterministic Contract-Net coordination (research §37.1) + the supply-chain safety gate.

CNP round: ANNOUNCE a CFP (replenish stage S by qty Q) → collect SEALED BIDS (each supplier proxy bids from its
OBSERVED performance; the logistics agent's route cost cross-checks) → AWARD deterministically (min cost, stable
tie-break by supplier id) → the award is routed through `safety/validator.validate()` under the `supply_chain_order`
contract BEFORE any order effect (Hard Rule 3 at the supply-chain boundary). Every CFP and award writes a signed
`audit_chain` row (best-effort, surfaced-failure pattern — traceability precedent) + an OTel span.

Determinism: same observer state + same CFP → same award (no RNG, stable sort) — tested; preserves the project's
runtime-determinism invariant (Stage 21).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from agents.supply_chain.roles import LogisticsAgent, SupplierAgentProxy
from agents.supply_chain.signals import SignalObserver
from safety.contract import Action, Invariant, Precondition, SafetyContract

# ---------------------------------------------------------------------------
# The supply-chain order contract (static, code-defined — the LLM never edits contracts, KB_17)
# ---------------------------------------------------------------------------

SUPPLY_CHAIN_ORDER_CONTRACT = SafetyContract(
    name="supply_chain_order",
    sil=0,  # ordering material is not a safety-of-machinery function; SIL-0 routes "direct" but is still GATED
    iso_clauses=["ISA-95 Part 3 (operations management)", "EU AI Act Art-12 (record-keeping)"],
    preconditions=[
        Precondition(name="qty_positive_bounded",
                     description="order quantity is a positive integer within the stage's real free capacity",
                     check=lambda ws: 0 < int(ws.get("order_qty", 0)) <= max(0, int(ws.get("capacity", 0)) - int(ws.get("buffer", -1)))),
        Precondition(name="supplier_known",
                     description="the awarded supplier exists in the observed world",
                     check=lambda ws: ws.get("supplier_id") is not None and bool(ws.get("supplier_exists", False))),
        Precondition(name="supplier_not_quarantined",
                     description="the supplier is not quarantined by the disruption monitor",
                     check=lambda ws: not bool(ws.get("supplier_quarantined", False))),
    ],
    invariants=[
        Invariant(name="buffer_capacity_sane",
                  description="stage buffer/capacity readings are self-consistent",
                  check=lambda ws: 0 <= int(ws.get("buffer", -1)) <= int(ws.get("capacity", 0))),
    ],
    fail_safe_path="no_action",
)


@dataclass(frozen=True)
class Cfp:
    """Call-for-proposals: replenish `stage_id` by `qty` of `sku`."""
    cfp_id: str
    stage_id: int
    sku: str
    qty: int
    buffer: int
    capacity: int


@dataclass(frozen=True)
class Bid:
    supplier_id: int
    cost: float
    basis: str  # human-readable, real basis of the bid (observed lead/reliability or labelled exploration)


@dataclass
class Award:
    cfp: Cfp
    supplier_id: Optional[int]          # None = no eligible bid (honest no-award)
    cost: Optional[float]
    allowed: bool = False               # set by the safety gate
    gate_reason: str = ""
    exploration: bool = False           # True when this round was a deterministic exploration award
    audit_seq: Optional[int] = None
    audited: bool = False
    bids: list[Bid] = field(default_factory=list)


def _audit(action: str, payload: dict[str, Any]) -> tuple[Optional[int], bool]:
    """Best-effort signed audit row; failure SURFACED via (None, False), never hidden, never fabricated."""
    try:
        from memory.audit_chain import append
        return append("agent:supply_chain", action, payload), True
    except Exception:  # noqa: BLE001 — DB/crypto down: the plan proceeds but is marked un-audited
        return None, False


class ContractNetCoordinator:
    """Deterministic CNP manager over the supplier proxies + logistics cross-check.

    Every `exploration_every`-th round is an EXPLORATION award to the least-observed eligible supplier (counter-
    based, no RNG — determinism preserved): without it the first observed supplier wins every award forever
    (monoculture found in the first smoke run), reliability estimates never form for alternates, and a single
    supplier failure would have no measured fallback. Deterministic exploration = the anti-fragility answer."""

    def __init__(self, observer: SignalObserver, quarantined: Optional[set[int]] = None,
                 exploration_every: int = 10):
        self.observer = observer
        self.quarantined = quarantined if quarantined is not None else set()
        self.exploration_every = max(2, exploration_every)
        self._round_counter = 0
        self._supplier_proxy = SupplierAgentProxy()
        self._logistics = LogisticsAgent()

    # -- ANNOUNCE + BID --------------------------------------------------

    def collect_bids(self, cfp: Cfp) -> list[Bid]:
        bids: list[Bid] = []
        for sid in sorted(self.observer.suppliers.keys()):
            if sid in self.quarantined:
                continue
            cost = self._supplier_proxy.bid_cost(self.observer, sid)
            if cost is None or cost == float("inf"):
                continue  # abstain / observed-always-failing: no bid
            route = self._logistics.route_cost(self.observer, sid)
            # Cross-check: when both views exist, take the WORSE (conservative) of the two real estimates.
            eff = max(cost, route) if route not in (None, float("inf")) else cost
            stats = self.observer.suppliers[sid]
            basis = (f"observed lead_median={stats.lead_median_s and round(stats.lead_median_s, 1)}s "
                     f"reliability={stats.reliability and round(stats.reliability, 3)} (n={stats.observations})"
                     if stats.lead_median_s is not None else "exploration bid (no observations yet)")
            bids.append(Bid(supplier_id=sid, cost=eff, basis=basis))
        return bids

    # -- AWARD (deterministic) + SAFETY GATE ------------------------------

    def award(self, cfp: Cfp, supplier_exists: Any = None) -> Award:
        from observability.otel_init import traced_span

        with traced_span("supply_chain.cnp.round", **{"cnp.cfp": cfp.cfp_id, "cnp.stage": cfp.stage_id}):
            seq, audited = _audit("supply_chain.cfp",
                                  {"cfp_id": cfp.cfp_id, "stage_id": cfp.stage_id, "sku": cfp.sku, "qty": cfp.qty})
            bids = self.collect_bids(cfp)
            if not bids:
                aw = Award(cfp=cfp, supplier_id=None, cost=None, allowed=False,
                           gate_reason="no eligible bids (honest no-award)", bids=[])
                aw.audit_seq, aw.audited = _audit("supply_chain.award",
                                                  {"cfp_id": cfp.cfp_id, "awarded": None, "reason": aw.gate_reason})
                return aw
            self._round_counter += 1
            exploration = self._round_counter % self.exploration_every == 0
            if exploration:
                # Deterministic exploration: least-observed eligible supplier (ties → lowest id).
                best = min(bids, key=lambda b: (self.observer.suppliers[b.supplier_id].observations, b.supplier_id))
            else:
                best = min(bids, key=lambda b: (b.cost, b.supplier_id))  # min cost, stable tie-break by id
            # SAFETY GATE (Hard Rule 3): validate BEFORE any order effect.
            from safety.validator import validate
            world_state = {
                "order_qty": cfp.qty, "buffer": cfp.buffer, "capacity": cfp.capacity,
                "supplier_id": best.supplier_id,
                "supplier_exists": (best.supplier_id in self.observer.suppliers
                                    if supplier_exists is None else bool(supplier_exists)),
                "supplier_quarantined": best.supplier_id in self.quarantined,
            }
            action = Action(contract=SUPPLY_CHAIN_ORDER_CONTRACT.name, actuator="supply_chain.order",
                            params={"cfp_id": cfp.cfp_id, "qty": cfp.qty, "sku": cfp.sku},
                            target=f"supplier:{best.supplier_id}")
            decision = validate(action, world_state, SUPPLY_CHAIN_ORDER_CONTRACT)
            aw = Award(cfp=cfp, supplier_id=best.supplier_id, cost=best.cost,
                       allowed=decision.allow, gate_reason=decision.reason,
                       exploration=exploration, bids=bids)
            aw.audit_seq, aw.audited = _audit("supply_chain.award", {
                "cfp_id": cfp.cfp_id, "awarded": best.supplier_id, "cost": round(best.cost, 3),
                "n_bids": len(bids), "exploration": exploration, "gate_allow": decision.allow, "gate_reason": decision.reason,
            })
            return aw


__all__ = ["Cfp", "Bid", "Award", "ContractNetCoordinator", "SUPPLY_CHAIN_ORDER_CONTRACT"]
