---
name: Simulation Spec
description: SimPy entity definitions, scenario catalog, problem catalog driving the embodied agent
type: spec
last-updated: 2026-06-12-stage6
---

> **Stage 2 close (2026-05-24)** — the random-tick injector at
> `backend/simulation/engine.py:268-310` is REMOVED. Plant dynamics now come
> from a SimPy `Environment` orchestrated by `backend/simulation/sim_world.py`.
> Pydantic-validated `POST /api/simulation/inject` is the canonical event
> source. See §"Live state (Stage 2)" below.

# KB_05 — Simulation Spec

## Purpose
The simulator is the only environment the agents see in v1. Its event catalog defines the problem space; its tick rate sets the latency budget. This file is the contract between Stage 2 (build the simulator) and Stage 7 (PPO trains against it) / Stage 13 (DB-driven CDC injects into it).

## Source of truth
- `backend/simulation/engine.py` (post Stage 2: SimPy-backed)
- The Gymnasium env wrapper `backend/training/rl_env/factory_env.py` (post Stage 7)

## ~~Current state (pre Stage 2)~~ — superseded 2026-05-24

~~`backend/simulation/engine.py` is a real state machine but **events are random-tick-injected** at `:268-300`:~~
~~- Collisions: `tick_count % 10` + `random.random() < 0.3`~~
~~- Bottlenecks: `tick_count % 15` + `random.random() < 0.25`~~

**Stage 2 replaced this with a real SimPy DES. See §"Live state (Stage 2)" below.**

## Live state (Stage 2)

The simulator is now driven by `backend/simulation/sim_world.py:SimWorld`,
which owns a `simpy.Environment` running in a dedicated worker thread. The
async FastAPI app communicates via thread-safe queues.

### Files (Stage 2)

| Path | Role |
|---|---|
| `backend/simulation/calibration.py` | All tunable plant constants (stage cycle-time mu/sigma, MTBF/MTTR, robot kinematics, supplier lead distributions, event-impact constants). Single point of retune. |
| `backend/simulation/entities/incident.py` | `InjectRequest` (Pydantic — REST contract); `Incident` (in-process record); `apply_incident_to_world(...)` (per-type behaviour dispatch). |
| `backend/simulation/entities/robot.py` | `Robot` SimPy process: battery decay, task queue, charging via shared `simpy.Resource(2)` charging stations. |
| `backend/simulation/entities/stage.py` | `Stage` SimPy process: log-normal cycle time, MTBF/MTTR exponential, defect roll, downstream consumer wiring. |
| `backend/simulation/entities/supplier.py` | `Supplier` SimPy process: stochastic lead time, reliability. |
| `backend/simulation/sim_world.py` | `SimWorld` orchestrator: builds 10 stages + 20 AMRs + 6 suppliers + 2 charging stations; Poisson order-arrival loop; worker thread; thread-safe `inject()` and `snapshot()`. |
| `backend/simulation/persistence.py` | Async path: incident → Redis pubsub publish → Postgres `incidents` insert → retry queue on failure. |
| `backend/api/simulation_routes.py` | `POST /api/simulation/inject` (Pydantic-validated); `GET /api/simulation/snapshot`. |
| `backend/tests/test_inject_validation.py` | Pydantic schema tests (all 6 types accept; malformed reject with 400). |
| `backend/tests/test_sim_world_smoke.py` | Construction / determinism / snapshot / all-6-event-types inject smoke. |

### Calibration (acceptance targets)

- **Throughput target**: ~500 units/hr at full utilization. Stage cycle-time mu chosen so 10-stage mean ≈ 72 s/unit/stage → 0.83 units/min/stage → 500/hr at no bottleneck.
- **AMR utilization**: ≥ 60%. Achieved by the 8 orders/hr × Poisson arrivals × inter-stage transport task assignment.
- **Stable queues**: log-normal cycle distribution prevents monotonic queue growth absent active incidents.
- **Inject-to-WS-delta latency**: ≤ 250 ms p95. Worker tick pacing is 100 ms wall-clock.
- **Deterministic seed**: `numpy.random.default_rng(seed)` threaded through every entity. No `import random` in the simulator path (verified by `scripts/audit.sh`).

### Random-tick removal (audit impact)

`scripts/audit.sh` Stage-1 baseline = **439**. Stage 2 removes:
- `random.uniform(...)` calls inside `_apply_problem_behavior` and `_generate_mock_state` (≈ 4 hits).
- `random.choice` / `random.sample` calls in same methods (≈ 3 hits).
- `random.randint` calls in `_generate_mock_state` and `_apply_solution_behavior` (≈ 3 hits).
- `import random` line itself (1 hit).
Expected post-Stage-2 baseline: **≤ 430** (~10 hits removed from the engine path; many surviving `random.*` hits live in `backend/ml/` and are replaced by Stages 4–10).

## Target state (Stage 2 onward)

### Resources
- **10 production stages** (machines, each with cycle-time distribution + MTBF/MTTR + capacity)
- **Conveyor segments** between stages (limited throughput; can jam)
- **2 charging stations** (limited concurrent slots)

### Processes
- **Order arrivals** — Poisson with configurable rate
- **Product flow** stage-by-stage with stochastic cycle times
- **Robot fleet (20 AMRs)** servicing inter-stage transport, charge cycles, idle parking
- **Supplier orders** with stochastic lead time and reliability

### Event catalog (Problem types — agents must respond to all six)

| Type | Trigger payload | Plant impact | Agent expected response |
|---|---|---|---|
| `machine_crack` | `{stage_id, eta_minutes}` | Stage degrades, fails after eta | Manufacturing agent re-routes flow; Robotics agent pre-stages spare parts; Supply Chain agent expedites replacement |
| `robot_down` | `{robot_id}` | Robot battery drops to 0 or fault state | Robotics agent redistributes tasks; Manufacturing agent adjusts stage feed rate |
| `late_delivery` | `{supplier_id, sku, delay_minutes}` | Supply gap | Supply Chain agent reorders from backup supplier; Manufacturing agent throttles upstream stages |
| `demand_spike` | `{sku, multiplier, duration_minutes}` | Sudden order surge | Supply Chain agent advances orders; Manufacturing agent boosts throughput; Robotics agent prioritizes flow |
| `defect_surge` | `{stage_id, rate_increase}` | Defect rate climbs | Manufacturing agent flags QC; Supply Chain agent reorders input materials; Robotics agent re-routes |
| `power_dip` | `{duration_minutes, max_throughput_pct}` | Plant-wide capacity reduction | All agents coordinate to keep critical SKUs flowing within the cap |

### Triggers (how an event reaches the simulator)

1. **REST**: `POST /api/simulation/inject` with `{type, ...payload}` — used by the Disruption Console UI (Stage 12) and tests.
2. **WS** (inbound): not used for injection; only for ping/pong + operator overrides.
3. **DB-driven (Stage 13 — BUILT 2026-06-15)**: an `INSERT` into `incidents` (or a trouble-status `UPDATE` to `stages.status` — the real table; "production_stages" was aspirational) fires the `cdc_emit()` trigger → durable `cdc_outbox` row + `pg_notify('cdc_events')` → `backend/ingestion/cdc_listener.py` (sync-psycopg background thread: `LISTEN` + drain-on-connect) → `change_to_inject()` → `SimWorld.inject()`. **Transactional outbox + LISTEN/NOTIFY + drain-on-connect** (research §22), NOT Supabase Realtime (heavy Elixir) — the research-endorsed robust self-hosted CDC for our single-PG free-cost constraint. Durable (catches offline-written rows), ordered, low-latency. pgoutput WAL logical replication for non-PG sinks at scale = G-068. Needs `wal_level=logical`.
4. **Chat (Stage 12)**: operator types natural language → LLM translates to structured `inject` payload → confirm → fire.

### Calibration target (Stage 2 acceptance)

- Baseline "normal" run yields ~500 units/hr throughput.
- Stable queues (no monotonic growth over 30-minute observation).
- Latency from `inject` POST to first state delta on WS: ≤ 250 ms p95 (well inside the cross-cutting budget).

## Stage 6 additions (2026-06-12) — machine telemetry + intervention API

**Machine telemetry (AI4I units).** Every `Stage` derives `telemetry()` from REAL sim state so the Stage-4
failure brain judges actual simulator behaviour (no fabricated signals): tool wear accumulates per unit produced
(`TELEMETRY.tool_wear_min_per_unit`); a cracking machine drifts toward the AI4I failure regimes — rpm sinks
toward the HDF band, torque climbs toward OSF, wear jumps toward TWF, and the process−air temperature gap
collapses (`TelemetryCalibration` in `calibration.py`). Sensor noise = seeded numpy rng (deterministic per world
seed — same pattern as the rest of the sim). Mapping is physics-motivated; thresholds come from the AI4I
dataset's published failure-mode definitions; the sim was NOT tuned to flatter the model.

**Intervention API (sim-only intervene v0).** `Stage.start_maintenance(duration=0.5×MTTR)` — planned maintenance
cancels a scheduled crack, resets wear, idles production, returns to nominal. An UNintervened crack breakdown
costs `2.5× exponential(MTTR)` (secondary damage — `EVENT_IMPACT.machine_crack_repair_multiplier`). Downtime is
accounted per stage (`time_broken_seconds`, `time_maintenance_seconds`, breakdown/maintenance counters) so the
A/B harness reports measured numbers.

**Latent Stage-2 bug found & fixed.** A crack scheduled while `_failure_loop` slept on a long natural-MTBF draw
never fired at its ETA (machines degraded forever instead of breaking). Found by the Stage-6 intervene tests;
fixed via a SimPy interrupt from `schedule_crack` (guarded by `_awaiting_failure` so repairs/maintenance are
never interrupted).

## Persistence

Every event:
- Writes a row to `incidents` (Postgres).
- Publishes to `pubsub:simulator:events` (Redis).
- Broadcasts a `delta` envelope on the WebSocket.
- Stage-6 slice events (`prediction` / `diagnosis` / `intervention` / `ab_report`) ride the same Redis channel
  pre-enveloped (KB_04 family) via `services/slice_runner.py::LiveSliceRunner`.

**Stage 7 (2026-06-12):** the RL intervention env (`backend/training/stage_07_rl_intervention/env.py`) adds a **maintenance-crew capacity constraint** at the ENV level (default unlimited in SimWorld is unchanged — Stage-6 behaviour preserved, zero regression). The crew constraint + event-driven decision points are training/eval concerns, not core SimWorld semantics; `sim_world.py` is untouched (ADR `2026-06-12_rl_intervention_ppo.md`).

**Stage 8 (2026-06-13):** the world-model trainer (`backend/training/stage_08_world_model/rollouts.py`) generates supervised (telemetry-window → ground-truth time-to-failure) data from seeded SimWorld crack rollouts (randomised ETA 8–20 min). Labels come from the sim's own `crack_failure_at` schedule — no fabrication. `sim_world.py` and entities are read-only here (rollouts only call existing `telemetry()`/`crack_proximity()`).

The decision the embodied agent makes in response writes a row to `decision_logs` (EU AI Act Art. 12 evidence).

## Failure modes the simulator must survive

- Operator injects two conflicting events in rapid succession → agent must serialize handling; second response is conditioned on first.
- Operator injects a malformed payload → simulator rejects with 400; no partial state mutation.
- Postgres write fails mid-event → simulator continues; event is durable via Redis, retried to Postgres on next tick.

## Last verified
- 2026-05-11 — Plan-mode session. Current random-tick injection confirmed at `backend/simulation/engine.py:268-300`; SimPy port not started.
- 2026-05-24 — Stage 2 ships the SimPy port. `backend/simulation/sim_world.py` is the new source of truth. `random.*` removed from the simulator path. `POST /api/simulation/inject` is the canonical event entry point. Calibration acceptance is verified by `backend/tests/test_sim_world_smoke.py` (construction + determinism + per-event-type inject) and the new Pydantic boundary test `backend/tests/test_inject_validation.py`. Persistence (Postgres `incidents` insert + Redis retry) wired via `backend/simulation/persistence.py` + `backend/data/supabase_service.py:insert_incident`. Live-stack tests (calibration over 30 simulated minutes; Playwright Disruption-Console e2e) require Postgres+Redis+frontend running and are deferred to the operator's verification pass.
- 2026-06-12 — Stage 6 adds the telemetry model + intervention API (this file's "Stage 6 additions" section), verified by `backend/tests/test_slice_predict_live.py` (telemetry shape, determinism, degradation drift) + `test_slice_intervene.py` (maintenance mechanics, crack-cancellation, stale-wake-up edge, 2.5× crack repair) + the measured A/B (`backend/training/evals/stage06/results.json`). The crack-ETA interrupt bugfix is regression-covered by `test_unintervened_crack_costs_multiplied_repair`.
- 2026-07-12 — Stage 30 (G-005) makes the breakdown-repair wait INTERRUPTIBLE: `Stage._failure_loop` now loops the repair timeout so a dispatched repair robot (`Stage.repair_assist(reduction_frac)` → interrupt) cuts the REMAINING downtime; `SimWorld.request_repair(stage_id, reduction, travel_seconds)` schedules the dispatch after a travel delay. Passive (no-dispatch) behaviour + downtime are UNCHANGED; `repair_assist` is a no-op unless the stage is in a broken repair wait (no fabricated benefit). Paired A/B `backend/scripts/run_repair_ab.py` → `training/evals/results/repair_ab.json` (−47.9% downtime, CI excludes 0); regression-covered by `backend/tests/repair/test_repair_dispatch.py` + `test_sim_world_smoke.py`.
