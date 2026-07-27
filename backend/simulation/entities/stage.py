"""Stage SimPy process — production stage with cycle time + MTBF/MTTR + defects.

Stage 6 (vertical slice) additions:
- A machine-telemetry model in AI4I-2020 units (`telemetry()`), derived from
  REAL stage state (status, crack proximity, accumulated tool wear, load) plus
  seeded sensor noise — the Stage-4 failure brain judges actual simulator state.
- A planned-maintenance intervention API (`start_maintenance`) — the sim-only
  intervene step. Planned maintenance cancels a scheduled crack, resets wear,
  and costs `preventive_maintenance_factor × mttr`, vs. a crack-induced
  breakdown which costs `machine_crack_repair_multiplier × exponential(mttr)`.
- Downtime accounting (`time_broken_seconds`, `time_maintenance_seconds`) so
  the A/B harness reports measured numbers, not estimates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Optional

import simpy

from ..calibration import EVENT_IMPACT, TELEMETRY, StageCalibration

if TYPE_CHECKING:
    from numpy.random import Generator


StageStatus = Literal["nominal", "degraded", "broken", "maintenance"]


@dataclass
class Stage:
    """Production stage. Owned by a SimPy environment."""

    cfg: StageCalibration
    env: simpy.Environment
    rng: "Generator"
    queue: simpy.Store = field(init=False)
    status: StageStatus = "nominal"
    # Defect-surge / crack-schedule bookkeeping.
    defect_multiplier: float = 1.0
    defect_surge_until: Optional[float] = None
    crack_failure_at: Optional[float] = None
    crack_scheduled_at: Optional[float] = None
    crack_throughput_factor: float = 1.0
    # Output bookkeeping.
    units_produced: int = 0
    units_defective: int = 0
    last_mtbf_failure_at: Optional[float] = None
    # Telemetry + downtime bookkeeping (Stage 6 slice).
    tool_wear_accum_min: float = 0.0
    time_broken_seconds: float = 0.0
    time_maintenance_seconds: float = 0.0
    maintenance_count: int = 0
    breakdown_count: int = 0
    crack_breakdown_count: int = 0
    repair_dispatch_count: int = 0                 # G-005: repair-robot assists received while broken
    _maintenance_until: Optional[float] = field(default=None, init=False, repr=False)
    _awaiting_failure: bool = field(default=False, init=False, repr=False)
    _awaiting_repair: bool = field(default=False, init=False, repr=False)          # G-005: in an interruptible repair wait
    _repair_pending_reduction: float = field(default=0.0, init=False, repr=False)  # G-005: assist to apply on interrupt
    _process: Optional[simpy.Process] = field(default=None, init=False, repr=False)
    _failure_process: Optional[simpy.Process] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.queue = simpy.Store(self.env, capacity=self.cfg.capacity)

    def start(self) -> None:
        if self._process is None:
            self._process = self.env.process(self._run())
        if self._failure_process is None:
            self._failure_process = self.env.process(self._failure_loop())

    # ---- operator-injected mutations ---------------------------------------

    def schedule_crack(self, eta_seconds: float) -> None:
        self.crack_scheduled_at = self.env.now
        self.crack_failure_at = self.env.now + max(1.0, eta_seconds)
        self.status = "degraded"
        # During the degraded window, throughput slows.
        self.crack_throughput_factor = EVENT_IMPACT.machine_crack_throughput_drop_factor
        # Wake the failure clock so the crack deadline is honoured even if the
        # loop is mid-sleep on a long natural-MTBF draw (latent Stage-2 bug:
        # without this, a crack scheduled mid-sleep never fired at its ETA —
        # found by the Stage-6 intervene tests).
        if self._failure_process is not None and self._failure_process.is_alive and self._awaiting_failure:
            try:
                self._failure_process.interrupt("crack_scheduled")
            except RuntimeError:  # pragma: no cover — already-terminated edge
                pass

    def activate_defect_surge(self, multiplier: float, duration_seconds: float) -> None:
        self.defect_multiplier = max(1.0, multiplier)
        self.defect_surge_until = self.env.now + duration_seconds

    # ---- intervention API (Stage 6 slice — sim-only execute step) -----------

    def start_maintenance(self, duration_seconds: Optional[float] = None) -> bool:
        """Begin PLANNED maintenance now. Returns False if the machine is already
        broken (too late — the breakdown path owns recovery) or already in
        maintenance. Cancels any scheduled crack, resets accumulated tool wear,
        and returns the stage to nominal after the (deterministic) duration.
        """
        if self.status in ("broken", "maintenance"):
            return False
        if duration_seconds is None:
            duration_seconds = EVENT_IMPACT.preventive_maintenance_factor * self.cfg.mttr_seconds
        # Cancel the pending crack: the fault is repaired before it fails.
        self.crack_failure_at = None
        self.crack_scheduled_at = None
        self.crack_throughput_factor = 1.0
        self.status = "maintenance"
        self.maintenance_count += 1
        self._maintenance_until = self.env.now + max(1.0, float(duration_seconds))
        self.env.process(self._maintenance_process(max(1.0, float(duration_seconds))))
        return True

    def repair_assist(self, reduction_frac: float) -> bool:
        """G-005: a DISPATCHED repair robot arrives and cuts the REMAINING repair time by `reduction_frac`.

        Returns True only if the stage is currently in a broken repair wait (so a dispatch to a not-broken machine
        is honestly a no-op, not a fabricated benefit). The reduction applies to the time still remaining, so an
        earlier dispatch saves more downtime than a late one — the real value of a fast repair-fleet response.
        """
        if self.status != "broken" or not self._awaiting_repair:
            return False
        self._repair_pending_reduction = max(0.0, min(0.95, float(reduction_frac)))
        if self._failure_process is not None and self._failure_process.is_alive:
            try:
                self._failure_process.interrupt("repair_assist")
                self.repair_dispatch_count += 1
                return True
            except RuntimeError:  # pragma: no cover — already-terminated edge
                return False
        return False

    def _maintenance_process(self, duration_seconds: float):
        yield self.env.timeout(duration_seconds)
        self.time_maintenance_seconds += duration_seconds
        self.tool_wear_accum_min = 0.0
        self._maintenance_until = None
        # Only return to nominal if nothing else broke us meanwhile.
        if self.status == "maintenance":
            self.status = "nominal"

    # ---- machine telemetry (Stage 6 slice — AI4I-unit signals) --------------

    def crack_proximity(self) -> float:
        """0.0 = healthy; → 1.0 as a scheduled crack approaches its failure time.

        Derived from REAL sim state (the crack schedule), not invented.
        """
        if self.crack_failure_at is None or self.crack_scheduled_at is None:
            return 0.0
        total = max(1e-9, self.crack_failure_at - self.crack_scheduled_at)
        elapsed = self.env.now - self.crack_scheduled_at
        return float(min(1.0, max(0.0, elapsed / total)))

    def telemetry(self) -> dict:
        """Machine telemetry in AI4I-2020 units, derived from real stage state.

        Physics-motivated mapping (see calibration.TelemetryCalibration + KB_05):
        a degrading machine slows (rpm ↓ toward the HDF band), overstrains
        (torque ↑ toward OSF), wears its tool (wear → TWF band), and loses
        heat-dissipation margin (process−air gap collapses toward HDF).
        Sensor noise is seeded rng — deterministic per world seed.
        """
        t = TELEMETRY
        prox = self.crack_proximity()
        load = self.queue_depth() / max(1, self.cfg.capacity)  # 0..1 utilisation proxy
        # Per-stage nominal operating point (slight spread across the line).
        base_rpm = t.base_rot_speed_rpm + 25.0 * (self.cfg.stage_id - 4.5)
        base_torque = t.base_torque_nm + 1.5 * (self.cfg.stage_id % 3)
        rpm = base_rpm * (1.0 - t.degraded_rpm_drop_frac * prox) * max(0.5, self.crack_throughput_factor if prox > 0 else 1.0)
        torque = base_torque * (1.0 + t.degraded_torque_rise_frac * prox) * (1.0 + 0.15 * load)
        wear = self.tool_wear_accum_min + t.degraded_extra_wear_min * prox
        air = t.base_air_temp_k
        process = t.base_process_temp_k + 1.5 * load
        # Heat-dissipation margin collapses as the crack approaches.
        process = process - (t.degraded_temp_gap_collapse_k * prox) * 0.5
        air = air + (t.degraded_temp_gap_collapse_k * prox) * 0.5
        # Seeded sensor noise (same determinism pattern as the rest of the sim).
        air += float(self.rng.normal(0.0, t.noise_air_temp_k))
        process += float(self.rng.normal(0.0, t.noise_process_temp_k))
        rpm += float(self.rng.normal(0.0, t.noise_rpm))
        torque += float(self.rng.normal(0.0, t.noise_torque_nm))
        return {
            "stage_id": self.cfg.stage_id,
            "name": self.cfg.name,
            "sim_time_seconds": float(self.env.now),
            "status": self.status,
            "type_": "M",
            "air_temp_k": round(air, 3),
            "process_temp_k": round(process, 3),
            "rot_speed_rpm": round(max(0.0, rpm), 2),
            "torque_nm": round(max(0.0, torque), 3),
            "tool_wear_min": round(max(0.0, wear), 2),
            "queue_depth": self.queue_depth(),
            "crack_proximity": round(prox, 4),
        }

    # ---- queries -----------------------------------------------------------

    def queue_depth(self) -> int:
        return len(self.queue.items)

    def throughput_units_per_hour(self, window_seconds: float = 600.0) -> float:
        # Coarse approximation; tests use the units_produced counter.
        elapsed = max(1.0, self.env.now)
        return self.units_produced / elapsed * 3600.0

    # ---- SimPy processes ---------------------------------------------------

    def _run(self):
        while True:
            # If broken or in planned maintenance, sit idle until recovered.
            if self.status in ("broken", "maintenance"):
                yield self.env.timeout(1.0)
                continue
            try:
                unit = yield self.queue.get()
            except simpy.Interrupt:
                continue
            # Sample cycle time from log-normal.
            base = math.exp(self.rng.normal(self.cfg.cycle_mu_log_seconds, self.cfg.cycle_sigma_log))
            ct = base / max(0.05, self.crack_throughput_factor)
            yield self.env.timeout(ct)
            # Defect roll.
            rate = self.cfg.defect_rate * self.defect_multiplier
            if self.defect_surge_until is not None and self.env.now >= self.defect_surge_until:
                self.defect_multiplier = 1.0
                self.defect_surge_until = None
            is_defective = self.rng.random() < rate
            self.units_produced += 1
            # Real production wears the tool (telemetry input — Stage 6 slice).
            self.tool_wear_accum_min += TELEMETRY.tool_wear_min_per_unit
            if is_defective:
                self.units_defective += 1
            # Output the unit by appending to the consumer (downstream stage's
            # queue) — the orchestrator (SimWorld) holds the consumer reference.
            unit["last_stage_done"] = self.cfg.stage_id
            unit["defective"] = unit.get("defective", False) or is_defective
            yield self.env.timeout(0.0)  # cooperative yield
            consumer = unit.pop("_next_consumer", None)
            if consumer is not None:
                yield consumer.put(unit)

    def _failure_loop(self):
        """MTBF-driven failure + crack-driven failure + MTTR recovery.

        A planned-maintenance window (status == "maintenance") postpones natural
        failure checks: the machine is offline and being serviced. A
        crack-induced breakdown costs `machine_crack_repair_multiplier × draw`
        (secondary damage) — the cost the Stage-6 preventive intervention avoids.
        """
        while True:
            # While in planned maintenance, do not fail; re-check shortly after.
            if self.status == "maintenance":
                yield self.env.timeout(5.0)
                continue
            # Time to next natural failure (exponential MTBF).
            t_next = self.rng.exponential(self.cfg.mtbf_seconds)
            # If a crack is scheduled, fail at min(crack, MTBF).
            capped_by_crack = False
            if self.crack_failure_at is not None:
                crack_in = max(0.1, self.crack_failure_at - self.env.now)
                if crack_in < t_next:
                    t_next = crack_in
                    capped_by_crack = True
            self._awaiting_failure = True
            try:
                yield self.env.timeout(max(0.1, t_next))
            except simpy.Interrupt:
                # A crack was scheduled mid-sleep — re-draw with its deadline.
                self._awaiting_failure = False
                continue
            self._awaiting_failure = False
            # Maintenance may have started (and cancelled the crack) while we
            # waited — if so, skip this failure and loop back.
            if self.status == "maintenance":
                continue
            if capped_by_crack and self.crack_failure_at is None:
                # The crack that set this wake-up was repaired in time (planned
                # maintenance) — no breakdown; re-draw the natural MTBF clock.
                continue
            crack_induced = capped_by_crack and self.crack_failure_at is not None
            # Trigger failure.
            self.status = "broken"
            self.last_mtbf_failure_at = self.env.now
            self.crack_throughput_factor = 1.0
            self.crack_failure_at = None
            self.crack_scheduled_at = None
            self.breakdown_count += 1
            # Repair time: crack-induced breakdowns cause secondary damage.
            t_repair = self.rng.exponential(self.cfg.mttr_seconds)
            if crack_induced:
                self.crack_breakdown_count += 1
                t_repair *= EVENT_IMPACT.machine_crack_repair_multiplier
            # G-005: INTERRUPTIBLE repair wait — a dispatched repair robot (repair_assist) cuts the REMAINING
            # repair time. Without any dispatch this is exactly the passive MTTR (unchanged behaviour + downtime).
            remaining = t_repair
            self._repair_pending_reduction = 0.0
            while remaining > 1e-6:
                self._awaiting_repair = True
                started = self.env.now
                try:
                    yield self.env.timeout(remaining)
                    self.time_broken_seconds += (self.env.now - started)
                    remaining = 0.0
                except simpy.Interrupt:
                    elapsed = self.env.now - started
                    self.time_broken_seconds += elapsed
                    remaining = max(0.0, remaining - elapsed)
                    remaining *= (1.0 - self._repair_pending_reduction)   # repair crew cut the remaining time
                    self._repair_pending_reduction = 0.0
            self._awaiting_repair = False
            # Repair replaces the worn tooling too.
            self.tool_wear_accum_min = 0.0
            self.status = "nominal"

    # ---- snapshot ----------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "stage_id": self.cfg.stage_id,
            "name": self.cfg.name,
            "queue_depth": self.queue_depth(),
            "status": self.status,
            "units_produced": self.units_produced,
            "units_defective": self.units_defective,
            "defect_rate_effective": round(self.cfg.defect_rate * self.defect_multiplier, 5),
            "tool_wear_accum_min": round(self.tool_wear_accum_min, 2),
            "time_broken_seconds": round(self.time_broken_seconds, 1),
            "time_maintenance_seconds": round(self.time_maintenance_seconds, 1),
            "breakdown_count": self.breakdown_count,
            "crack_breakdown_count": self.crack_breakdown_count,
            "maintenance_count": self.maintenance_count,
            "repair_dispatch_count": self.repair_dispatch_count,
        }
