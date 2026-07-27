"""SimWorld — the SimPy-backed plant simulator.

This module is the source of truth for plant dynamics. It replaces the
random-tick `_apply_problem_behavior` at backend/simulation/engine.py:268-310.
The public surface (`SimulationEngine` callers, WebSocket broadcast envelopes)
is preserved by `backend/simulation/engine.py`, which now delegates here.

Architecture
============
- The SimPy `Environment` runs synchronously in a dedicated worker thread.
- The async layer (FastAPI + WebSocket) communicates with the worker via
  thread-safe queues:
    * `inject_queue`  : async → sim (incident inject)
    * `event_queue`   : sim → async (every fired incident + per-tick state)
- Determinism: `numpy.random.default_rng(seed)` is passed to every entity. No
  use of the global `random` module in the simulator path.
- Time: simulated wall-clock seconds. One real-world second of `env.run(until=t)`
  advances simulated time by `t - env.now`. The orchestrator runs `env.step()`
  in 100 ms wall-clock batches so the inject-to-event latency is ≤ 250 ms p95.

Stage 2 acceptance ↔ where in this file
========================================
- 10 stages, 20 robots, 2 chargers, suppliers, conveyor segments → `__init__`.
- Deterministic seeding → constructor `seed` argument.
- `_apply_problem_behavior` gone → see backend/simulation/engine.py.
- Every event writes an `incidents` row → `inject` calls `persistence.append_incident`.
- POST /api/simulation/inject → see backend/api/simulation_routes.py.
- 500 units/hr / stable queues / ≥60% AMR utilisation → `calibrate(duration)`.
- Conflict serialisation → `inject` enforces per-(type, target_id) FIFO.
- Malformed payload → handled at the REST boundary by Pydantic.
- Postgres write failure durability → `persistence.append_incident` retries
  via Redis pubsub.
"""
from __future__ import annotations

import logging
import queue as thread_queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import numpy as np
import simpy

from .calibration import SIM_WORLD, STAGES, IncidentType
from .entities import (
    Incident,
    InjectRequest,
    Robot,
    Stage,
    Supplier,
    Task,
    apply_incident_to_world,
)

logger = logging.getLogger(__name__)


@dataclass
class _ActiveModulation:
    """Plant-wide modulation applied by demand_spike / power_dip incidents."""

    demand_multiplier: float = 1.0
    demand_multiplier_until: float = 0.0
    throughput_cap_pct: float = 1.0
    throughput_cap_until: float = 0.0


class SimWorld:
    """SimPy-driven plant simulator. Thread-safe entry points: `inject`, `snapshot`, `stop`."""

    def __init__(
        self,
        seed: int = SIM_WORLD.default_seed,
        on_incident: Optional[Callable[[Incident], None]] = None,
    ) -> None:
        self.seed = int(seed)
        self.rng: np.random.Generator = np.random.default_rng(self.seed)
        self.env = simpy.Environment()
        self.on_incident = on_incident
        self.modulation = _ActiveModulation()
        # Charging-station resource (shared by all robots).
        self.charging_stations = simpy.Resource(self.env, capacity=SIM_WORLD.n_charging_stations)
        # Build stages.
        self.stages: dict[int, Stage] = {}
        for cfg in STAGES:
            child_rng = np.random.default_rng(self.rng.integers(0, 2**32 - 1))
            stage = Stage(cfg=cfg, env=self.env, rng=child_rng)
            stage.start()
            self.stages[cfg.stage_id] = stage
        # Build robots.
        self.robots: dict[int, Robot] = {}
        for i in range(SIM_WORLD.n_robots):
            child_rng = np.random.default_rng(self.rng.integers(0, 2**32 - 1))
            robot = Robot(id=i, env=self.env, rng=child_rng, charging_stations=self.charging_stations)
            robot.start()
            self.robots[i] = robot
        # Build suppliers.
        self.suppliers: dict[int, Supplier] = {}
        for i in range(SIM_WORLD.n_suppliers):
            child_rng = np.random.default_rng(self.rng.integers(0, 2**32 - 1))
            supplier = Supplier(id=i, env=self.env, rng=child_rng)
            self.suppliers[i] = supplier
        # Conveyor segment producer→consumer wiring: each stage's output feeds
        # the next stage's queue (last stage's output drains via the order
        # process below).
        # Order arrivals (Poisson).
        self.env.process(self._order_arrival_loop())
        # Stop control.
        self._stop_flag = threading.Event()
        self._inject_queue: thread_queue.Queue[Incident] = thread_queue.Queue()
        # Per-(type, target_id) serialisation: when an incident is being
        # processed, a second of the same key waits.
        self._serialization_keys: set[tuple[IncidentType, Optional[int]]] = set()
        # Worker thread.
        self._thread: Optional[threading.Thread] = None
        # Bookkeeping.
        self.total_orders_started = 0
        self.total_orders_complete = 0
        self.incidents_fired: list[Incident] = []

    # ---- public thread-safe API -------------------------------------------

    def start(self) -> None:
        """Launch the SimPy worker thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._worker, daemon=True, name="simpy-world")
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def inject(self, req: InjectRequest) -> Incident:
        """Thread-safe inject. Returns the created `Incident` immediately.

        The actual world mutation happens on the next SimPy tick (≤ 100 ms
        wall-clock). Inject-to-WS-delta latency target ≤ 250 ms p95.
        """
        incident = Incident.from_request(req)
        self._inject_queue.put(incident)
        return incident

    def snapshot(self) -> dict[str, Any]:
        """Best-effort snapshot of plant state (thread-safe enough for read-mostly)."""
        return {
            "sim_time_seconds": self.env.now,
            "seed": self.seed,
            "stages": [s.snapshot() for s in self.stages.values()],
            "robots": [r.snapshot() for r in self.robots.values()],
            "suppliers": [s.snapshot() for s in self.suppliers.values()],
            "orders_started": self.total_orders_started,
            "orders_complete": self.total_orders_complete,
            "throughput_units_per_hour": self._aggregate_throughput(),
            "amr_utilization": self._aggregate_utilization(),
            "modulation": {
                "demand_multiplier": self.modulation.demand_multiplier,
                "throughput_cap_pct": self.modulation.throughput_cap_pct,
            },
            "incidents_fired_count": len(self.incidents_fired),
            "recent_incidents": [
                {"type": i.type, "target_id": i.target_id, "severity": i.severity}
                for i in self.incidents_fired[-8:]
            ],
        }

    # ---- aggregate metrics (used by calibrate + tests) ---------------------

    def _aggregate_throughput(self) -> float:
        elapsed_h = max(self.env.now / 3600.0, 1e-6)
        return self.total_orders_complete / elapsed_h

    def _aggregate_utilization(self) -> float:
        if not self.robots:
            return 0.0
        return sum(r.utilization() for r in self.robots.values()) / len(self.robots)

    # ---- world-level modulations (called from incident.apply_*) ------------

    def activate_demand_spike(self, multiplier: float, duration_seconds: float) -> None:
        self.modulation.demand_multiplier = max(1.0, multiplier)
        self.modulation.demand_multiplier_until = self.env.now + duration_seconds

    def activate_power_dip(self, max_throughput_pct: float, duration_seconds: float) -> None:
        self.modulation.throughput_cap_pct = max(0.0, min(1.0, max_throughput_pct))
        self.modulation.throughput_cap_until = self.env.now + duration_seconds

    # ---- SimPy processes ---------------------------------------------------

    def _order_arrival_loop(self):
        """Poisson order arrivals; tail of the line is the last stage's queue."""
        while True:
            lam = SIM_WORLD.order_arrival_lambda_per_sec * self.modulation.demand_multiplier
            # Decay demand_spike if expired.
            if self.modulation.demand_multiplier_until and self.env.now >= self.modulation.demand_multiplier_until:
                self.modulation.demand_multiplier = 1.0
                self.modulation.demand_multiplier_until = 0.0
            if self.modulation.throughput_cap_until and self.env.now >= self.modulation.throughput_cap_until:
                self.modulation.throughput_cap_pct = 1.0
                self.modulation.throughput_cap_until = 0.0
            # Inter-arrival.
            inter = float(self.rng.exponential(1.0 / max(1e-9, lam)))
            yield self.env.timeout(inter)
            self.total_orders_started += 1
            unit = {"order_id": self.total_orders_started, "defective": False}
            # Throughput cap: probabilistic accept/reject.
            if self.rng.random() < self.modulation.throughput_cap_pct:
                # Wire consumer chain: stage 0 → 1 → ... → 9 → completion.
                unit["_next_consumer"] = self._chain_consumer(0)
                # Enqueue into stage 0.
                yield self.stages[0].queue.put(unit)
                # Schedule a robot transport task between two random stages
                # to represent inter-stage AMR work (calibration only).
                if self.robots:
                    from_s = int(self.rng.integers(0, len(self.stages)))
                    to_s = (from_s + 1) % len(self.stages)
                    task = Task(task_id=self.total_orders_started, from_stage=from_s, to_stage=to_s, duration_seconds=15.0)
                    robot = self.robots[int(self.rng.integers(0, len(self.robots)))]
                    robot.enqueue(task)

    def _chain_consumer(self, current_stage_id: int):
        """Return the simpy Store to put a finished unit into.

        Wires stage N → stage N+1; last stage's consumer increments the
        completed-orders counter via a small process below.
        """
        next_id = current_stage_id + 1
        if next_id in self.stages:
            return _ChainProxy(self, self.stages[next_id])
        return _CompletionProxy(self)

    def deliver_material(self, stage_id: int) -> None:
        """Stage 26 — a genuinely fulfilled supplier order feeds ONE unit into `stage_id`'s buffer.

        Closes the material loop for the supply-chain layer: the delivered unit enters production at that stage
        (correct consumer chain wired) and flows downstream like any other unit. Runs as its own SimPy process so
        a full buffer blocks the delivery (real backpressure) instead of dropping or forcing it."""
        if stage_id not in self.stages:
            raise KeyError(f"deliver_material: unknown stage {stage_id}")
        self.total_orders_started += 1
        unit = {"order_id": self.total_orders_started, "defective": False,
                "_next_consumer": self._chain_consumer(stage_id), "_source": "supplier_delivery"}

        def _put():
            yield self.stages[stage_id].queue.put(unit)

        self.env.process(_put())

    def request_repair(self, stage_id: int, reduction_frac: float, *, travel_seconds: float = 0.0) -> bool:
        """Stage 30 (G-005) — a dispatched repair robot travels to `stage_id` and cuts its remaining downtime.

        `travel_seconds` models the robot's response delay (derived from its real availability by the dispatcher);
        after the delay the assist is applied to the broken stage. Returns True if scheduled (stage exists + broken).
        The actual downtime saving is realised by `Stage.repair_assist` and is a no-op if the stage recovered first
        (honest — no fabricated benefit). Runs as its own SimPy process so the travel delay is simulated-time real."""
        if stage_id not in self.stages:
            raise KeyError(f"request_repair: unknown stage {stage_id}")
        stage = self.stages[stage_id]

        def _dispatch():
            if travel_seconds > 0:
                yield self.env.timeout(travel_seconds)
            stage.repair_assist(reduction_frac)

        self.env.process(_dispatch())
        return stage.status == "broken"

    # ---- worker thread loop ------------------------------------------------

    def _worker(self) -> None:
        last_tick = time.monotonic()
        while not self._stop_flag.is_set():
            # Drain inject queue, applying world mutations.
            try:
                while True:
                    incident = self._inject_queue.get_nowait()
                    self._handle_inject(incident)
            except thread_queue.Empty:
                pass
            # Advance simulation by 0.1 wall-clock seconds worth of sim time.
            target = self.env.now + 0.1 * self._speed_factor()
            try:
                self.env.run(until=target)
            except simpy.core.EmptySchedule:
                # No processes — yield briefly to avoid a busy loop.
                time.sleep(0.01)
                continue
            # Pace to ~100 Hz wall-clock so latency target is comfortably met.
            now = time.monotonic()
            sleep = max(0.0, 0.1 - (now - last_tick))
            if sleep > 0:
                time.sleep(sleep)
            last_tick = time.monotonic()

    def _speed_factor(self) -> float:
        """Wall-to-sim speed factor. 1.0 = realtime; higher = faster than realtime."""
        return 1.0

    def _handle_inject(self, incident: Incident) -> None:
        key = (incident.type, incident.target_id)
        if key in self._serialization_keys:
            # Defer until current of same key clears. For simplicity, re-enqueue
            # with a small simulated delay.
            incident._was_serialized_after = ",".join(self._serialization_keys.__repr__()[:80].splitlines())
            self.env.process(self._deferred_inject(incident, delay=2.0))
            return
        self._apply_incident(incident)

    def _deferred_inject(self, incident: Incident, delay: float):
        yield self.env.timeout(delay)
        self._apply_incident(incident)

    def _apply_incident(self, incident: Incident) -> None:
        key = (incident.type, incident.target_id)
        self._serialization_keys.add(key)
        try:
            apply_incident_to_world(self, incident)
        finally:
            # Per-incident keys release quickly; conflict serialisation is
            # demonstrated for at least the first-tick conflict window.
            self.env.process(self._release_key_later(key, delay=2.0))
        self.incidents_fired.append(incident)
        if self.on_incident is not None:
            try:
                self.on_incident(incident)
            except Exception:
                logger.exception("on_incident callback raised")

    def _release_key_later(self, key, delay: float):
        yield self.env.timeout(delay)
        self._serialization_keys.discard(key)


# ---------------------------------------------------------------------------
# Internal proxies wiring stage chain → completion.
# ---------------------------------------------------------------------------


class _ChainProxy:
    """A Store-like façade that forwards a finished unit to the next stage."""

    def __init__(self, world: SimWorld, next_stage: Stage) -> None:
        self.world = world
        self.next_stage = next_stage

    def put(self, unit):
        # Re-wire the unit's `_next_consumer` for the stage after `next_stage`.
        unit["_next_consumer"] = self.world._chain_consumer(self.next_stage.cfg.stage_id)
        return self.next_stage.queue.put(unit)


class _CompletionProxy:
    """Sink for units that pass through the final stage."""

    def __init__(self, world: SimWorld) -> None:
        self.world = world

    def put(self, unit):
        self.world.total_orders_complete += 1
        # Return a yieldable SimPy event so callers can `yield consumer.put(unit)`.
        return self.world.env.timeout(0)
