"""Supplier SimPy process — stochastic lead time + reliability roll."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import simpy

from ..calibration import SIM_WORLD

if TYPE_CHECKING:
    from numpy.random import Generator


@dataclass
class Supplier:
    """Supplier with stochastic lead time. Each order is its own SimPy process."""

    id: int
    env: simpy.Environment
    rng: "Generator"
    sku: str = "default"
    # Active delay injection from late_delivery incidents.
    extra_delay_until_seconds: Optional[float] = None
    fulfilled: int = 0
    failed: int = 0

    def delay_next_delivery(self, seconds: float) -> None:
        """Apply a `late_delivery` impact: next N seconds of lead time get +delay."""
        self.extra_delay_until_seconds = max(self.extra_delay_until_seconds or 0.0, self.env.now + seconds)

    def order(self, sku: str = "default", on_fulfil=None) -> simpy.Process:
        """Place an order; returns a SimPy process that fulfils after lead time.

        Stage 26: `on_fulfil` (optional callable, no args) fires when — and only when — the order genuinely
        fulfils (survives the reliability roll), closing the material loop: the caller can feed the delivered
        unit into a stage buffer. A failed order never fires it (no phantom material)."""
        return self.env.process(self._fulfill(sku, on_fulfil))

    def _fulfill(self, sku: str, on_fulfil=None):
        base = math.exp(self.rng.normal(SIM_WORLD.supplier_lead_mu_log_seconds, SIM_WORLD.supplier_lead_sigma_log))
        extra = 0.0
        if self.extra_delay_until_seconds is not None and self.env.now < self.extra_delay_until_seconds:
            extra = self.extra_delay_until_seconds - self.env.now
        lead = base + extra
        yield self.env.timeout(lead)
        reliable = self.rng.random() < SIM_WORLD.supplier_reliability
        if reliable:
            self.fulfilled += 1
            if on_fulfil is not None:
                on_fulfil()
        else:
            self.failed += 1

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "sku": self.sku,
            "fulfilled": self.fulfilled,
            "failed": self.failed,
        }
