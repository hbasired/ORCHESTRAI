"""Stage 38 — a documented industrial Time-of-Use (ToU) + demand-charge electricity tariff (research §49).

These are a REPRESENTATIVE published-structure US-industrial ToU tariff (on/mid/off-peak $/kWh + a $/kW demand
charge), NOT a fabricated number pulled from thin air: the split and magnitudes match the tariff structure the
peak-shaving / load-shifting literature and industry sources (gridX, Wirtek, iFactory) describe — on-peak roughly
2.5-3x off-peak energy, and demand charges being ~40% of an industrial bill. A real pilot swaps this for the
customer's actual utility schedule (G-035, buyer-blocked); the OPTIMISER is tariff-agnostic.

Pure/deterministic; no I/O; no fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass

# Hourly ToU period assignment for a 24-slot day (documented representative industrial schedule).
#   off-peak: 22:00-08:00  ·  mid-peak: 08:00-12:00 & 18:00-22:00  ·  on-peak: 12:00-18:00
_ON_PEAK_HOURS = set(range(12, 18))
_MID_PEAK_HOURS = set(range(8, 12)) | set(range(18, 22))

# $/kWh energy price by period + $/kW-day demand charge (a daily proxy for the monthly $/kW peak charge).
PRICE_OFF_PEAK = 0.10
PRICE_MID_PEAK = 0.16
PRICE_ON_PEAK = 0.28
DEMAND_CHARGE_PER_KW_DAY = 0.60   # $/kW applied to the day's aggregate peak (≈ $18/kW-month / 30)


@dataclass(frozen=True)
class Tariff:
    """A ToU energy tariff + demand charge over an H-slot day (default 24 hourly slots)."""
    horizon_slots: int = 24
    slot_hours: float = 1.0
    demand_charge_per_kw: float = DEMAND_CHARGE_PER_KW_DAY

    def period(self, slot: int) -> str:
        h = slot % 24
        if h in _ON_PEAK_HOURS:
            return "on_peak"
        if h in _MID_PEAK_HOURS:
            return "mid_peak"
        return "off_peak"

    def energy_price(self, slot: int) -> float:
        """$/kWh at `slot`."""
        return {"on_peak": PRICE_ON_PEAK, "mid_peak": PRICE_MID_PEAK, "off_peak": PRICE_OFF_PEAK}[self.period(slot)]

    def prices(self) -> list[float]:
        return [self.energy_price(t) for t in range(self.horizon_slots)]

    def bill(self, load_kw_by_slot: list[float]) -> dict[str, float]:
        """The real bill for an aggregate load profile: Σ(kW·h·price) energy + demand_charge·peak_kW.

        `load_kw_by_slot[t]` is the average kW drawn during slot t. Returns energy $, demand $, total $, and peak kW.
        """
        energy = sum(kw * self.slot_hours * self.energy_price(t) for t, kw in enumerate(load_kw_by_slot))
        peak = max(load_kw_by_slot) if load_kw_by_slot else 0.0
        demand = self.demand_charge_per_kw * peak
        return {"energy_cost": round(energy, 4), "demand_cost": round(demand, 4),
                "total_cost": round(energy + demand, 4), "peak_kw": round(peak, 4)}


__all__ = ["Tariff", "PRICE_OFF_PEAK", "PRICE_MID_PEAK", "PRICE_ON_PEAK", "DEMAND_CHARGE_PER_KW_DAY"]
