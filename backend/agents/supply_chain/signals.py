"""Stage 26 — supply-chain signal extraction from REAL SimWorld snapshots (no fabrication).

All downstream agents bid from these observed signals only. Semantics (documented, not invented):
  * a stage's material BUFFER is its SimPy queue (`queue_depth` / `capacity`) — SimWorld's real inventory;
  * DEMAND rate is the observed `throughput_units_per_hour` series (the sim's real output rate);
  * SUPPLIER reliability/lead statistics come from observed `fulfilled`/`failed` counters and measured
    order→fulfil intervals recorded by the observer (never from the sim's hidden config constants —
    the agents must not "know" `SIM_WORLD.supplier_reliability`; they estimate it like a real operator would).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2.0


@dataclass
class SupplierStats:
    """Observed (not configured) per-supplier statistics."""
    supplier_id: int
    fulfilled: int = 0
    failed: int = 0
    lead_times_s: deque = field(default_factory=lambda: deque(maxlen=64))
    lead_placed_at_s: deque = field(default_factory=lambda: deque(maxlen=64))  # placement time per lead (or None)
    lead_total: int = 0   # total leads EVER observed (deque may have dropped old ones)

    @property
    def observations(self) -> int:
        return self.fulfilled + self.failed

    @property
    def reliability(self) -> Optional[float]:
        """Observed fulfilment rate; None (honest-unknown) below 3 observations."""
        n = self.observations
        return (self.fulfilled / n) if n >= 3 else None

    @property
    def lead_median_s(self) -> Optional[float]:
        return _median(list(self.lead_times_s)) if len(self.lead_times_s) >= 3 else None

    @property
    def lead_std_s(self) -> Optional[float]:
        xs = list(self.lead_times_s)
        if len(xs) < 3:
            return None
        mu = sum(xs) / len(xs)
        return (sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


class SignalObserver:
    """Accumulates observed supply-chain signals across SimWorld snapshots (one `observe()` per tick)."""

    def __init__(self, history_len: int = 128):
        self.suppliers: dict[int, SupplierStats] = {}
        self.throughput_history: deque = deque(maxlen=history_len)     # units/hour series
        self.queue_history: dict[int, deque] = {}                      # stage_id -> queue_depth series
        self.last_time_s: float = 0.0                                  # sim time of the latest snapshot
        self._last_counts: dict[int, tuple[int, int]] = {}             # supplier -> (fulfilled, failed)
        self._pending_orders: dict[int, deque] = {}                    # supplier -> order-placed sim-times
        # Overdue-detection registry: outstanding (not yet fulfilled) order placements per supplier.
        # A FAILED order never reports back either — `prune_failures()` removes the oldest entries when the
        # observed failure counter advances (conservative: slightly reduces overdue sensitivity, documented).
        self.outstanding: dict[int, list[float]] = {}

    def note_order_placed(self, supplier_id: int, sim_time_s: float) -> None:
        """FIFO-attribution path (snapshot-only observers). LIMITATION, found in the Stage-26 disruption drill:
        FIFO attribution SMEARS a delayed order's lead onto faster later orders — use `note_lead()` (exact,
        callback-measured) whenever the caller can wire delivery callbacks; do not mix both for one supplier."""
        self._pending_orders.setdefault(supplier_id, deque(maxlen=64)).append(sim_time_s)

    def note_outstanding(self, supplier_id: int, placed_at_s: float) -> None:
        """Register a placed order awaiting fulfilment (the overdue detector's input)."""
        self.outstanding.setdefault(supplier_id, []).append(float(placed_at_s))

    def resolve_outstanding(self, supplier_id: int, placed_at_s: float) -> None:
        """A fulfilment arrived for this placement — remove one matching outstanding entry.

        Exact-match with OLDEST-entry fallback: failures are random among in-flight orders but `prune_failures`
        removes the oldest entries, so a young order's failure can consume an old ALIVE entry; when that old order
        later fulfils, its exact match is gone and the young DEAD entry would leak as a permanently-aging phantom
        (found by the Stage-26 drill: leaked entries aged 6-7h drove persistent false overdue events). Falling back
        to removing the oldest keeps the COUNT exactly = alive pendings, which is what the >=3-overdue rule needs."""
        lst = self.outstanding.get(supplier_id, [])
        try:
            lst.remove(float(placed_at_s))
        except ValueError:
            if lst:
                lst.remove(min(lst))  # consume the oldest — one callback always retires exactly one entry

    def prune_failures(self, supplier_id: int, n: int) -> None:
        """The observed failure counter advanced by n — drop the n OLDEST outstanding entries (a failed order
        never reports back; oldest-first is conservative for overdue detection)."""
        lst = sorted(self.outstanding.get(supplier_id, []))
        self.outstanding[supplier_id] = lst[n:] if n < len(lst) else []

    def note_lead(self, supplier_id: int, lead_s: float, placed_at_s: Optional[float] = None) -> None:
        """EXACT per-order lead observation (measured by the delivery callback: fulfil_time - placed_time).

        `placed_at_s` matters for shift detection: leads are OBSERVED in fulfilment order, so a same-placement
        batch always fulfils shortest-first — an artificial 'ramp' in observation order (Stage-26 drill finding).
        Windowing by PLACEMENT time removes that artifact."""
        stats = self.suppliers.setdefault(supplier_id, SupplierStats(supplier_id=supplier_id))
        stats.lead_times_s.append(max(0.0, float(lead_s)))
        stats.lead_placed_at_s.append(float(placed_at_s) if placed_at_s is not None else None)
        stats.lead_total += 1

    def observe(self, snapshot: dict[str, Any]) -> None:
        """Consume one real SimWorld snapshot; update observed stats. Raises KeyError on a malformed snapshot
        (honest: a bad snapshot is an error, not something to paper over)."""
        now = float(snapshot["sim_time_seconds"])
        self.last_time_s = now
        self.throughput_history.append(float(snapshot["throughput_units_per_hour"]))
        for st in snapshot["stages"]:
            sid = int(st["stage_id"]) if "stage_id" in st else int(st["id"])
            self.queue_history.setdefault(sid, deque(maxlen=128)).append(int(st["queue_depth"]))
        for sup in snapshot["suppliers"]:
            sid = int(sup["id"])
            stats = self.suppliers.setdefault(sid, SupplierStats(supplier_id=sid))
            prev_f, prev_x = self._last_counts.get(sid, (0, 0))
            new_f, new_x = int(sup["fulfilled"]), int(sup["failed"])
            completed = (new_f - prev_f) + (new_x - prev_x)
            # Attribute completions to the oldest pending orders → measured lead times (FIFO approximation,
            # documented: SimWorld fulfils orders independently so FIFO is the honest observable estimate).
            pending = self._pending_orders.get(sid, deque())
            for _ in range(min(completed, len(pending))):
                placed = pending.popleft()
                stats.lead_times_s.append(max(0.0, now - placed))
                stats.lead_placed_at_s.append(placed)
                stats.lead_total += 1
            stats.fulfilled, stats.failed = new_f, new_x
            self._last_counts[sid] = (new_f, new_x)

    # ---- derived signals (None = honest-unknown, never a guess) ----

    def demand_rate_per_hour(self) -> Optional[float]:
        xs = list(self.throughput_history)
        return (sum(xs[-12:]) / len(xs[-12:])) if len(xs) >= 3 else None

    def demand_std_per_hour(self) -> Optional[float]:
        xs = list(self.throughput_history)[-24:]
        if len(xs) < 3:
            return None
        mu = sum(xs) / len(xs)
        return (sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5

    def stage_buffer(self, stage_id: int) -> Optional[int]:
        h = self.queue_history.get(stage_id)
        return int(h[-1]) if h else None

    def stockout_ticks(self, stage_id: int) -> int:
        return sum(1 for q in self.queue_history.get(stage_id, []) if q == 0)


__all__ = ["SignalObserver", "SupplierStats"]
