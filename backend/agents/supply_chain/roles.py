"""Stage 26 — the five supply-chain role agents (research §37.2 role decomposition).

Each agent is a small, deterministic decision unit that PROPOSES (bids into the Contract-Net round) from real
observed signals / real model outputs only. None may invent a number: an agent with insufficient signal returns
None (abstains) — the CNP layer treats abstention honestly. The demand agent wraps the REAL `demand_forecaster.pt`
when given history in its schema (a proxy model until pilot re-fit, G-035 — labelled in every output); otherwise it
uses transparent empirical statistics from the observer, and SAYS which source it used.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from agents.supply_chain.signals import SignalObserver

# Service-level factor for the safety-stock policy (research §37.3). z=1.65 ~ 95% service; configurable, sourced.
DEFAULT_SERVICE_Z = 1.65


@dataclass
class DemandEstimate:
    rate_per_hour: float
    std_per_hour: float
    source: str  # "demand_forecaster (LSTM, Bike-Sharing proxy)" | "empirical (SimWorld throughput history)"


class DemandAgent:
    """Estimates demand from the REAL forecaster (when schema-compatible history is supplied) or empirical stats."""

    name = "demand"

    def estimate(self, observer: SignalObserver,
                 forecaster_history: Optional[Sequence[dict]] = None) -> Optional[DemandEstimate]:
        if forecaster_history is not None:
            from ml.demand_forecaster import get_demand_forecaster, ModelUnavailableError
            try:
                out = get_demand_forecaster().forecast(forecaster_history)  # raises if model absent/short history
                std = observer.demand_std_per_hour() or 0.0
                return DemandEstimate(rate_per_hour=float(out["forecast"]), std_per_hour=std, source=out["model"])
            except ModelUnavailableError:
                pass  # honest fall-through to empirical — the SOURCE label will say so
        rate = observer.demand_rate_per_hour()
        std = observer.demand_std_per_hour()
        if rate is None or std is None:
            return None  # abstain: not enough observations for ANY honest estimate
        return DemandEstimate(rate_per_hour=rate, std_per_hour=std,
                              source="empirical (SimWorld throughput history)")


@dataclass
class ReplenishmentNeed:
    stage_id: int
    buffer: int          # inventory POSITION (on_hand + on_order) — the (s,S) trigger quantity
    on_hand: int         # physical units in the buffer NOW — what the capacity gate must bound
    capacity: int
    reorder_point: float
    order_qty: int
    policy: str


class InventoryAgent:
    """Continuous-review reorder-point policy (research §37.3): ROP = mu_d*L + z*sigma_d*sqrt(L)."""

    name = "inventory"

    def __init__(self, service_z: float = DEFAULT_SERVICE_Z):
        self.service_z = service_z

    def needs(self, observer: SignalObserver, demand: Optional[DemandEstimate],
              stage_capacities: dict[int, int],
              on_order: Optional[dict[int, int]] = None) -> list[ReplenishmentNeed]:
        """Stages whose INVENTORY POSITION (observed buffer + outstanding on-order units — the standard
        continuous-review quantity, research §37.3) is below the computed ROP. Abstains (empty) without a demand
        estimate; with demand but NO lead observations yet it issues small BOOTSTRAP exploration orders (labelled —
        the standard cold-start answer: you cannot estimate lead times without ever ordering), never an invented ROP."""
        if demand is None:
            return []
        on_order = on_order or {}
        leads = [s.lead_median_s for s in observer.suppliers.values() if s.lead_median_s is not None]
        if not leads:
            # Cold start: qty-1 exploration order for the lowest-position stage only (bounded, deterministic).
            candidates = [(observer.stage_buffer(sid), sid, cap) for sid, cap in sorted(stage_capacities.items())
                          if observer.stage_buffer(sid) is not None and cap > 0]
            candidates = [(b + on_order.get(sid, 0), sid, cap) for b, sid, cap in candidates
                          if b + on_order.get(sid, 0) < cap]
            if not candidates:
                return []
            pos, sid, cap = min(candidates)
            on_hand = observer.stage_buffer(sid) or 0
            return [ReplenishmentNeed(stage_id=sid, buffer=pos, on_hand=on_hand, capacity=cap,
                                      reorder_point=float(pos + 1),
                                      order_qty=1, policy="bootstrap exploration (no lead observations yet)")]
        # Full ROP under stochastic demand AND stochastic lead time (the textbook form — the lead-time-variance
        # term dominates in this plant, first A/B smoke showed the sigma_L-less form under-protects):
        #   ROP = mu_d*mu_L + z*sqrt(mu_L*sigma_d^2 + mu_d^2*sigma_L^2)
        mu_L_h = (sum(leads) / len(leads)) / 3600.0
        stds = [s.lead_std_s for s in observer.suppliers.values() if s.lead_std_s is not None]
        sigma_L_h = ((sum(stds) / len(stds)) / 3600.0) if stds else 0.0
        mu_d, sigma_d = demand.rate_per_hour, demand.std_per_hour
        rop = mu_d * mu_L_h + self.service_z * math.sqrt(
            max(mu_L_h, 1e-9) * sigma_d ** 2 + (mu_d ** 2) * sigma_L_h ** 2)
        # (s, S): trigger at position < s=ROP, order UP TO S = ROP + one lead-time of demand (prevents both
        # starvation-during-lead and order-every-tick churn).
        order_up_to = rop + mu_d * mu_L_h
        out: list[ReplenishmentNeed] = []
        for stage_id, cap in sorted(stage_capacities.items()):
            buf = observer.stage_buffer(stage_id)
            if buf is None:
                continue
            position = buf + on_order.get(stage_id, 0)  # inventory position = on-hand + on-order (§37.3)
            if position < rop:
                # Capacity bounds the PHYSICAL buffer at delivery (cap - on_hand), NOT the position — clamping
                # on position trickled 1-unit orders whenever ROP > capacity (first A/B diagnosis) and starved
                # the plant. The (s,S) trigger stays position-based; the gate stays physical.
                qty = min(math.ceil(order_up_to - position), cap - buf)
                if qty <= 0:
                    continue
                out.append(ReplenishmentNeed(stage_id=stage_id, buffer=position, on_hand=buf, capacity=cap,
                                             reorder_point=round(rop, 2), order_qty=qty,
                                             policy=(f"(s,S): s=mu*L+z*sqrt(L*sd^2+mu^2*sL^2), S=s+mu*L "
                                                     f"(z={self.service_z}, position=on_hand+on_order)")))
        return out


class SchedulingAgent:
    """Proposes production throttle/priority adjustments from real stage states (starving/overflowing buffers)."""

    name = "scheduling"

    def proposals(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for st in snapshot["stages"]:
            sid = int(st.get("stage_id", st.get("id")))
            depth, status = int(st["queue_depth"]), str(st["status"])
            if depth == 0 and status in ("nominal", "degraded"):
                out.append({"stage_id": sid, "adjustment": "prioritize_upstream_feed",
                            "reason": f"buffer starved (queue_depth=0, status={status})"})
        return out


class LogisticsAgent:
    """Scores delivery routing: expected effective lead per supplier from OBSERVED stats (lower is better)."""

    name = "logistics"

    def route_cost(self, observer: SignalObserver, supplier_id: int) -> Optional[float]:
        s = observer.suppliers.get(supplier_id)
        if s is None or s.lead_median_s is None or s.reliability is None:
            return None  # abstain: unobserved supplier
        if s.reliability <= 0.0:
            return float("inf")  # every observed order failed — do not route here
        # Expected effective lead = median lead / observed reliability (failed orders must be re-placed).
        return s.lead_median_s / s.reliability


class SupplierAgentProxy:
    """Bids on behalf of a supplier from its OBSERVED performance (the local, 'selfish' view — §37.2)."""

    name = "supplier"

    def bid_cost(self, observer: SignalObserver, supplier_id: int) -> Optional[float]:
        s = observer.suppliers.get(supplier_id)
        if s is None:
            return None
        if s.lead_median_s is None or s.reliability is None:
            # Unobserved supplier: bid at an explicit EXPLORATION cost — a labelled policy choice (encourages
            # gathering observations), not a fabricated performance claim.
            return 1e6
        if s.reliability <= 0.0:
            return float("inf")
        lead_spread = s.lead_std_s or 0.0
        return (s.lead_median_s + lead_spread) / s.reliability


__all__ = ["DemandAgent", "DemandEstimate", "InventoryAgent", "ReplenishmentNeed",
           "SchedulingAgent", "LogisticsAgent", "SupplierAgentProxy", "DEFAULT_SERVICE_Z"]
