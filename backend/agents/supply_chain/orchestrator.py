"""Stage 26 — the supply-chain orchestration loop: observe → propose → coordinate (CNP) → gate → execute.

One `tick()` per SimWorld step: the observer ingests the real snapshot, the demand/inventory agents derive needs,
each need becomes a CFP, the CNP awards deterministically, the safety gate validates, and ONLY allowed awards place
real `supplier.order()` effects back into the sim. The disruption monitor runs every tick (quarantines feed the
CNP's eligibility). Neo4j ISA-95 grounding: suppliers/SKUs are upserted as graph nodes linked to stages; when the
graph is unavailable the orchestrator uses the sim topology directly and REPORTS `graph_grounded=False` (honest).

This is the SimWorld-facing execution loop (the A/B harness drives it); the runtime-facing integration is the
disruption monitor's incident path (Stage-25 exactly-once router into the LangGraph loop).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from agents.supply_chain.consensus import Award, Cfp, ContractNetCoordinator
from agents.supply_chain.disruption_monitor import DisruptionMonitor
from agents.supply_chain.roles import DemandAgent, InventoryAgent, SchedulingAgent
from agents.supply_chain.signals import SignalObserver


@dataclass
class TickResult:
    sim_time_s: float
    demand_source: Optional[str]
    needs: int
    awards: list[Award] = field(default_factory=list)
    orders_placed: int = 0
    disruptions: list[str] = field(default_factory=list)
    graph_grounded: bool = False


class SupplyChainOrchestrator:
    """Drives the multi-agent layer against a REAL SimWorld instance."""

    def __init__(self, world: Any, *, service_z: float = 1.65, raise_incidents: bool = False):
        self.world = world
        self.observer = SignalObserver()
        self.demand = DemandAgent()
        self.inventory = InventoryAgent(service_z=service_z)
        self.scheduling = SchedulingAgent()
        self.monitor = DisruptionMonitor(self.observer,
                                         raise_incident=None if raise_incidents else (lambda inc: None))
        self.coordinator = ContractNetCoordinator(self.observer, quarantined=self.monitor.quarantined)
        self._cfp_counter = 0
        self._graph_grounded = False
        self._on_order: dict[int, int] = {}   # stage_id -> outstanding (placed - delivered/failed) units

    # -- Neo4j ISA-95 grounding (once, idempotent; honest degradation) ----

    def ground_in_graph(self) -> bool:
        """Upsert supplier→SKU→stage topology into the ISA-95 graph. False (and says so) if Neo4j is down."""
        try:
            import asyncio
            from memory.graph_isa95 import upsert_node
            async def _run():
                for sid, sup in sorted(self.world.suppliers.items()):
                    await upsert_node("Enterprise", f"supplier_{sid}", f"Supplier {sid}",
                                      attributes={"role": "external_supplier", "sku": sup.sku})
                    await upsert_node("MaterialClass", f"sku_{sup.sku}", f"SKU {sup.sku}",
                                      parent_id=f"supplier_{sid}", parent_class="Enterprise",
                                      attributes={"source_supplier": sid})
            asyncio.run(_run())
            self._graph_grounded = True
        except Exception:  # noqa: BLE001 — Neo4j down: sim topology used directly, reported honestly
            self._graph_grounded = False
        return self._graph_grounded

    # -- one orchestration tick -------------------------------------------

    def tick(self, forecaster_history: Optional[list[dict]] = None) -> TickResult:
        snap = self.world.snapshot()
        self.observer.observe(snap)
        self.reconcile_failed_orders()

        result = TickResult(sim_time_s=float(snap["sim_time_seconds"]), demand_source=None, needs=0,
                            graph_grounded=self._graph_grounded)

        disruptions = self.monitor.check()
        result.disruptions = [f"{d.kind}@{d.subject}" for d in disruptions]

        est = self.demand.estimate(self.observer, forecaster_history)
        if est is None:
            return result  # honest abstention: not enough signal to order anything yet
        result.demand_source = est.source

        capacities = {int(st.get("stage_id", st.get("id"))): int(st.get("capacity", 0) or 0)
                      for st in snap["stages"]}
        # SimWorld snapshots may omit capacity; fall back to the entity's real config (still the sim's truth).
        for sid_, stage in getattr(self.world, "stages", {}).items():
            cap = getattr(getattr(stage, "cfg", None), "capacity", None)
            if cap:
                capacities[int(sid_)] = int(cap)

        needs = self.inventory.needs(self.observer, est, capacities, on_order=self._on_order)
        result.needs = len(needs)

        for need in needs:
            self._cfp_counter += 1
            cfp = Cfp(cfp_id=f"cfp-{self._cfp_counter}", stage_id=need.stage_id, sku="default",
                      qty=need.order_qty, buffer=need.on_hand, capacity=need.capacity)
            award = self.coordinator.award(cfp)
            result.awards.append(award)
            if award.allowed and award.supplier_id is not None:
                supplier = self.world.suppliers[award.supplier_id]
                for _ in range(cfp.qty):        # each unit is one real SimPy order process
                    placed_at = float(self.world.env.now)
                    supplier.order(sku=cfp.sku,
                                   on_fulfil=self._make_delivery(need.stage_id, award.supplier_id))
                    self._on_order[need.stage_id] = self._on_order.get(need.stage_id, 0) + 1
                    self.observer.note_outstanding(award.supplier_id, placed_at)
                    result.orders_placed += 1
        return result

    def _make_delivery(self, stage_id: int, supplier_id: int):
        """Delivery callback: a genuinely fulfilled order feeds one unit into the stage buffer (real sim effect),
        decrements the on-order position, and reports the EXACT measured lead (fulfil - placed) to the observer —
        the FIFO-attribution path smeared a delayed order's lead onto other suppliers (drill finding). Failed
        orders never fire it — their on-order units are reconciled by `reconcile_failed_orders()` each tick."""
        placed_at = float(self.world.env.now)

        def _deliver():
            self.world.deliver_material(stage_id)
            self._on_order[stage_id] = max(0, self._on_order.get(stage_id, 0) - 1)
            self.observer.note_lead(supplier_id, float(self.world.env.now) - placed_at, placed_at_s=placed_at)
            self.observer.resolve_outstanding(supplier_id, placed_at)
        return _deliver

    def reconcile_failed_orders(self) -> None:
        """Failed orders leave phantom on-order units (their callback never fires). Decrement the total observed
        failure delta round-robin across stages with outstanding on-order (conservative, deterministic), and prune
        the per-supplier outstanding registry so failures don't masquerade as overdue deliveries."""
        per_supplier_prev = getattr(self, "_last_failed_by_supplier", {})
        total_delta = 0
        for sid, st in self.observer.suppliers.items():
            d = st.failed - per_supplier_prev.get(sid, 0)
            if d > 0:
                self.observer.prune_failures(sid, d)
                total_delta += d
        self._last_failed_by_supplier = {sid: st.failed for sid, st in self.observer.suppliers.items()}
        for _ in range(max(0, total_delta)):
            open_stages = sorted(sid for sid, n in self._on_order.items() if n > 0)
            if not open_stages:
                break
            self._on_order[open_stages[0]] -= 1


__all__ = ["SupplyChainOrchestrator", "TickResult"]
