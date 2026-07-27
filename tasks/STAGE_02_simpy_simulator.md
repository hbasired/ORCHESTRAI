# Task: Stage 2 — SimPy Discrete-Event Simulator

**Status**: done (closed 2026-05-24)
**KB files this stage updates**: KB_01, KB_04, KB_05, KB_07, KB_TASK_LOG
**Pre-requisites**:
- Stage 1 closed: `KB_TASK_LOG.md` shows the 2026-05-11 Stage-1 entry; `.audit-baseline` reads **439**.
- Alembic migration `0001_init` applied (creates `incidents` + `decision_logs`).
- Docker compose stack running (`postgres` healthy with `wal_level=logical`).
- Backend pinned deps installed; `pytest` runs against `tests/test_health.py` + `tests/test_websocket_smoke.py`.
- Frontend on LTS stack (Next 15 / React 18.3 / Tailwind 3).
- ADR `compliance/decision-logs/2026-05-11_stage_01_close.md` reviewed — Supabase Realtime / Studio / Meta / REST are still deferred; this stage may either pick them up or write a fresh ADR continuing the deferral.

## Goal of this stage

Replace the random-tick problem injector at
`backend/simulation/engine.py:268-310` with a real
[SimPy](https://simpy.readthedocs.io) discrete-event simulator. The
simulator is the only environment the agents see in v1; every Stage 4–10
training pipeline trains against it. If the simulator lies, every model
trained on it inherits the lie.

This is a **load-bearing stage** — once it ships, the agent's view of
reality is grounded in deterministic, reproducible processes (Poisson
arrivals, MTBF/MTTR distributions, capacity constraints). The numeric
audit reduction is large because most of the surviving `random.uniform`
/ `random.choice` hits live in the simulator path.

**No new ML training in this stage.** Stage 4 onward consumes the
simulator; Stage 2 builds it.

## Acceptance criteria

Each is independently testable.

- [ ] `backend/simulation/sim_world.py` exists and exports a `SimWorld`
      class that runs a SimPy `Environment` containing: 10 stages with
      cycle-time + MTBF/MTTR distributions, 20 AMRs with battery and
      task queues, 2 charging stations (limited capacity), conveyor
      segments, supplier processes. Deterministic seeding supported via
      constructor argument.
- [ ] `backend/simulation/engine.py:_apply_problem_behavior` is **gone**.
      All event firing routes through SimPy processes. The `random.*`
      hits inside the simulator path drop by ≥ 80 % (measured via the
      audit script).
- [ ] Every event the simulator fires writes a row to the `incidents`
      table (Postgres) using the six allowed `type` values from KB_05's
      event catalog. Verified by:
      `pytest backend/tests/test_simpy_incidents.py -q`.
- [ ] `POST /api/simulation/inject` accepts the KB_05 payload shape,
      calls `SimWorld.inject(...)`, and the simulator produces the
      corresponding event on the WebSocket `incident` envelope within
      **250 ms p95** (latency budget from KB_10). Verified by a new
      Playwright test against a docker-compose-up backend.
- [ ] Baseline "normal" run (no injected events) yields **~500 units/hr
      throughput**, **stable queues** (no monotonic growth over a
      30-minute simulated observation), and **AMR utilization ≥ 60 %**.
      Calibration spec lives in `backend/simulation/sim_world.py`'s
      docstring; assertions in `tests/test_sim_calibration.py`.
- [ ] Operator-injected conflicting events are **serialized**: the
      simulator queues a second event of the same `type` against the
      same `target_id` until the first finishes. Verified by
      `tests/test_simpy_conflict_serialization.py`.
- [ ] Malformed `/inject` payload returns **400 with a Pydantic error
      body** — no partial state mutation. Verified by
      `tests/test_inject_validation.py`.
- [ ] Postgres write failure mid-event does not crash the simulator;
      the event is durable in Redis (`pubsub:simulator:events`) and
      retried on next tick. Verified by `tests/test_persistence_retry.py`
      using a fault-injected mock Postgres client.
- [ ] `bash scripts/audit.sh` reports **TOTAL < 439** (the new Stage-1
      baseline). Expected drop: 60–120 from removing `random.uniform`
      and `random.choice` in `engine.py:268-310` and surrounding helper
      methods.
- [ ] Frontend Disruption Console (existing UI surface) successfully
      injects all six event types via the live backend and renders the
      resulting `incident` WebSocket frame. Manual screenshot evidence
      in `compliance/decision-logs/<date>_stage_02_close.md`.
- [ ] `KB_05_Simulation_Spec.md` updated: §"Current state" → "Live as
      of Stage 2"; SimPy entity model section now exact (resource
      counts, capacity, lambda, MTBF/MTTR distributions).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/simulation/sim_world.py` | The SimPy `Environment` + entity processes. **Source of truth for plant dynamics.** |
| `backend/simulation/entities/__init__.py` | empty |
| `backend/simulation/entities/robot.py` | `Robot` SimPy process: battery decay, task queue, charging cycle |
| `backend/simulation/entities/stage.py` | `Stage` process: cycle-time sampling, MTBF/MTTR, defect generation |
| `backend/simulation/entities/supplier.py` | `Supplier` process: lead-time distribution, reliability roll |
| `backend/simulation/entities/incident.py` | `Incident` dataclass + the six concrete subclass behaviours (machine_crack, robot_down, late_delivery, demand_spike, defect_surge, power_dip) |
| `backend/simulation/persistence.py` | Async write path: SimPy event → Redis pubsub → Postgres `incidents` insert; retry-on-fail logic |
| `backend/api/simulation_routes.py` (if not already present) | `POST /api/simulation/inject` route — validates payload, calls `SimWorld.inject` |
| `backend/tests/test_simpy_incidents.py` | Every event type writes an `incidents` row |
| `backend/tests/test_sim_calibration.py` | Throughput / queue stability / AMR utilization assertions |
| `backend/tests/test_simpy_conflict_serialization.py` | Two-event same-target ordering |
| `backend/tests/test_inject_validation.py` | Pydantic 400 on bad payload |
| `backend/tests/test_persistence_retry.py` | Postgres fault → Redis durability → retry on next tick |
| `frontend-nextjs/e2e/disruption_console.spec.ts` | Playwright: click each of 6 inject buttons; assert WS frame arrives |
| `backend/training/simulator_dataset_export.ipynb.gitkeep` | placeholder; Stage 8 (world model) uses this to dump 100K-step SimPy trajectories for LSTM training |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/simulation/engine.py` | Replace `_apply_problem_behavior` with calls into `SimWorld.tick()`. Keep the public surface (`StateManager` callers, broadcast envelopes) unchanged. Delete `random.uniform` / `random.choice` / `random.sample` usage in the simulator path. |
| `backend/main.py` | Wire the new SimPy lifecycle into `lifespan(...)`: start the SimPy environment loop, register the shutdown handler. |
| `backend/data/supabase_service.py` | Add `insert_incident(payload: dict) -> str` returning the inserted `incident_id`. Reuses the existing connection. |
| `database/schema.sql` | Add deprecation banner pointing at `backend/alembic/versions/0001_init.py`. (KB_04 already says this; the SQL file gets a one-line comment.) |
| `backend/requirements.txt` | Add `simpy==4.1.*`. Pin exactly once the latest 4.1.x is selected. |
| `knowledge-base/KB_05_Simulation_Spec.md` | Replace "Current state (pre Stage 2)" with the live SimPy entity layout. Update `Last-updated` to Stage-2 close date. |
| `knowledge-base/KB_07_API_Contracts.md` | Document the now-real `/api/simulation/inject` request/response Pydantic schemas. |

## Files to DELETE

| Path | Why |
|---|---|
| `backend/simulation/engine.py:268-310` (lines, not file) | Random-tick injector — replaced by SimPy processes. The file stays. |

## Verification commands

Run from repo root:

```bash
# 1. Bring stack up; Alembic migration applies; simulator starts.
docker compose -f docker/docker-compose.yml --env-file .env.local up -d
docker compose -f docker/docker-compose.yml ps             # all healthy

# 2. Backend unit + integration tests.
cd backend && pytest -q

# 3. Smoke the inject endpoint.
curl -X POST http://localhost:8000/api/simulation/inject \
     -H 'Content-Type: application/json' \
     -d '{"type":"machine_crack","target_id":4,"details":{"eta_minutes":12}}'

# 4. Assert incident landed in Postgres.
docker compose -f docker/docker-compose.yml exec postgres \
    psql -U $POSTGRES_USER $POSTGRES_DB -c "SELECT type, severity, started_at FROM incidents ORDER BY started_at DESC LIMIT 5;"

# 5. Calibration: run a 30-minute simulated session, assert stable.
cd backend && python -m simulation.calibrate --duration 1800 --seed 42

# 6. Frontend disruption-console e2e.
cd frontend-nextjs && npx playwright test e2e/disruption_console.spec.ts

# 7. Audit must drop further.
cd .. && bash scripts/audit.sh    # TOTAL < 439

# 8. Re-lock baseline at the close of the stage.
bash scripts/audit.sh --baseline
```

## KB updates expected (filled out at stage close)

- `KB_01_System_Architecture.md` — flip the §"Backend services
  (theatrical — random fallbacks)" entry for the simulator from
  "Replaced in Stage 2" to "Real (Stage 2)". Update the Mermaid diagram
  if the simulator gains a sidecar process.
- `KB_04_Data_Schema.md` — confirm the `incidents` table is in use;
  document any new JSONB shape conventions chosen for `details`.
- `KB_05_Simulation_Spec.md` — major rewrite of §"Target state"; promote
  it to §"Live state" with the exact distribution choices made (e.g.
  Poisson λ=8/hr for orders, log-normal cycle times, MTBF from
  fitted-to-AI4I-data distributions).
- `KB_07_API_Contracts.md` — add the `/api/simulation/inject` request /
  response schemas verbatim.
- `KB_TASK_LOG.md` — Stage-2 entry: Shipped / Skipped / Learned /
  Next-stage adjustments. The "Next-stage adjustments" line writes the
  input for `tasks/STAGE_03_websocket_broker.md`.

## Closure ritual (run before declaring Stage 2 done)

1. `bash scripts/audit.sh` — count strictly less than **439**.
2. `bash scripts/audit.sh --baseline` — overwrite the baseline at the
   new lower number so Stage 3 has a stricter bar.
3. Bump KB files listed above.
4. Append `KB_TASK_LOG.md` Stage-2 entry.
5. Write `compliance/decision-logs/<date>_stage_02_close.md` if any
   non-trivial decisions were made (e.g. picked a particular cycle-time
   distribution after empirical comparison).
6. Write `tasks/STAGE_03_websocket_broker.md` using the template in
   `tasks/TASKS_README.md`. Pre-requisites reference Stage-2 KB updates.
7. Open the PR. CI gate enforces every check above.

## Risks / unknowns

- **Calibration drift vs. real factory data.** We have no
  paying-pilot data yet. The 500-units/hr baseline is plausible but
  unproven; expect to retune in Stage 14 once the first pilot delivers
  ground-truth telemetry. Mitigation: keep calibration constants in a
  single `backend/simulation/calibration.py` module so retuning is a
  one-PR change.
- **SimPy + asyncio interop.** SimPy is sync by default; the FastAPI
  app is async. Mitigation: run the SimPy `env.run()` in a dedicated
  worker thread; the async layer reads/writes via `asyncio.Queue`.
  Alternative considered (`simpy.rt.RealtimeEnvironment` in the same
  event loop) rejected because it ties simulation time to wall clock,
  breaking deterministic seeding for tests.
- **Determinism under parallel test runs.** Same seed must give the
  same trajectory. Mitigation: pass `numpy.random.default_rng(seed)`
  through every entity rather than relying on global `random.seed()`.
- **Postgres backpressure under event storms.** A demand_spike +
  defect_surge double-injection can fire dozens of events per second.
  Mitigation: batch incident inserts in 100 ms windows; cap at 200
  events/sec, drop with `429`-style backpressure logged to Redis.
- **Frontend Disruption Console**. The UI was theatrical pre-Stage-1;
  the LTS downgrade landed in Stage 1, but the page itself may still
  use mock state. Stage 2 may need to also rewrite that page's data
  source to call the real `/inject` endpoint. If so, scope it
  explicitly in this stage's PR description.

## Hand-off to Stage 3

When Stage 2 closes, Stage 3 (WebSocket broker) starts with:

- A real simulator firing real events into real Postgres rows.
- A `delta` / `incident` envelope shape locked in KB_04 — Stage 3 only
  needs to scale the fanout, not redesign it.
- A stricter audit baseline (well under 439) so Stage 3 can focus on
  multi-worker WebSocket fanout (Redis pub/sub-backed broker) without
  also chasing fakery.
- A real `incidents` table that Stage 13 will hook CDC into; Stage 3
  needs to keep the Postgres connection pool stable under the
  fanout load.

## Stage 2 success looks like

The disruption-console clicker can press "fire machine_crack" on the
operator dashboard, see a row land in `incidents`, see the embodied
agent's response logged in `decision_logs` (even if the response itself
is still rough — Stage 11 polishes the agent), and the throughput KPI
on the dashboard dips and recovers in a plausible curve. **No
`random.uniform` calls in the path from inject to dashboard.**
