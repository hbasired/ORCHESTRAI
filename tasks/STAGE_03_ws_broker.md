---
status: done
stage: 03
slug: ws_broker
created: 2026-05-24
updated: 2026-05-31
---

# Stage 03 — WebSocket Incident Broker (Redis pub/sub fan-out)

> Stage 2 made the SimPy `SimWorld` fire real incidents and publish each to the Redis channel
> `pubsub:simulator:events` (via `backend/simulation/persistence.append_incident`). Stage 3 builds the
> **broker** that subscribes to that channel and fans every incident out to all connected WebSocket clients
> using the canonical `incident` envelope from KB_04. Decoupling the simulator (publisher) from the WS
> fan-out (subscriber) through Redis pub/sub makes the fan-out **multi-worker safe** — every uvicorn worker
> subscribes and serves its own clients. Cross-links: PRD v2.0 §13 (v1 §7 API), PRD v2.1 §v2.1.4 (operator
> dashboard rides this), KB_04 (envelope), KB_07 (API contracts), Stage 2 hand-off.

## Pre-requisites

- Stage(s) closed: Stage 2 (SimPy DES; `append_incident` publishes to `pubsub:simulator:events`; verified closed 2026-05-31).
- Decision logs honoured: `2026-05-24_stage_02_close.md` (worker-thread SimWorld; Redis-FIFO durability).
- KB files at minimum version: KB_04 (WS envelopes), KB_07 (API contracts), KB_05 (event catalog).

## Acceptance criteria

- [x] `backend/services/ws_broker.py` exists, exporting a `ConnectionManager` (register/disconnect/broadcast
      with dead-client pruning + per-send timeout) and a `SimulatorEventBroker` that subscribes to Redis
      `pubsub:simulator:events`.
- [x] `build_incident_envelope(payload)` produces the **canonical KB_04 envelope** exactly:
      `{"v":1,"type":"incident","ts":<iso8601>,"incident_id":<uuid>,"payload":<IncidentPayload>}`.
      Verified by `pytest backend/tests/test_ws_broker.py -q`.
- [x] `ConnectionManager.broadcast` sends to every connected client and **prunes dead/erroring clients**
      without raising; a slow client cannot block the loop (per-send timeout). Verified by unit test.
- [x] The broker is **resilient**: malformed Redis messages are logged and skipped (no crash); a Redis
      connection drop triggers a backoff-reconnect loop; `stop()` cancels cleanly. (reconnect/backoff coded;
      malformed-skip unit-tested.)
- [x] `backend/main.py` lifespan wires `SimWorld(on_incident=...)` → `append_incident(..., redis_client=...)`
      (sync→async bridge via `run_coroutine_threadsafe`) and starts/stops the `SimulatorEventBroker`; the
      `/ws` endpoint registers/unregisters connections with the `ConnectionManager`.
- [x] `bash scripts/audit.sh` shows **no regression** (TOTAL ≤ 436). (Broker is additive backend code with
      zero theatrical-fallback patterns.)
- [x] **Live Redis path verified (2026-05-31):** `backend/tests/test_ws_broker_redis_integration.py` runs the
      REAL `append_incident` → Redis `PUBLISH` → broker `SUBSCRIBE` → client path against the docker
      `redis:7-alpine` container — **PASSED, fan-out latency 11.6 ms** (KB_10 budget p95 ≤ 250 ms).
- [ ] **(close gate — remaining)** Full-app HTTP→WS e2e: `POST /api/simulation/inject` on the running backend
      → `incident` envelope on a connected `/ws` client (exercises the FastAPI route + WS transport + SimWorld
      worker-thread bridge end-to-end). Needs `docker compose up backend`; pair with the frontend gate below.
- [ ] **(close gate — deferred)** Frontend Disruption Console consumes the real `/ws` `incident` stream and
      calls the real `/inject`, removing enough `Math.random()` mocks to drop `.audit-baseline` **below 436**
      (the strict-decrease close requirement). Until this lands, Stage 3 stays `in-progress` (no
      `--no-baseline-drop` abuse — a feature stage must reduce the count to close).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/services/ws_broker.py` | `ConnectionManager` + `SimulatorEventBroker` + `build_incident_envelope` |
| `backend/tests/test_ws_broker.py` | Unit tests: envelope shape, broadcast pruning, malformed-skip, broker handle |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/main.py` | Wire `SimWorld.on_incident`→Redis publish; start/stop broker in lifespan; register `/ws` clients with `ConnectionManager` |

## Files to DELETE

| Path | Reason |
|---|---|
| (none this increment) | legacy `_apply_problem_behavior`/`_apply_solution_behavior` no-op stubs + frontend mocks fold in at close |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_01_System_Architecture.md` (broker layer)
- `knowledge-base/KB_07_API_Contracts.md` (WS `incident` envelope delivery contract)

## Verification commands

```bash
# Audit baseline: no regression (must stay <= 436; drops below 436 at close after frontend mock removal)
bash scripts/audit.sh

# Broker + Stage 2 tests green
cd backend && venv/Scripts/python -m pytest tests/test_ws_broker.py tests/test_inject_validation.py tests/test_sim_world_smoke.py -q

# (close-gate, deferred) live e2e against compose stack:
#   docker compose -f docker/docker-compose.yml up -d redis postgres backend
#   wscat -c ws://localhost:8000/ws  &  curl -XPOST localhost:8000/api/simulation/inject -d '{"type":"robot_down","target_id":1}'
```

## Audit target

- Pre-stage baseline: **436** (`.audit-baseline` at stage open).
- Hold ≤ 436 during implementation (broker is additive, zero new fakery). **Close target: < 436** via frontend
  Disruption Console wiring to the real `/inject` + `/ws incident` stream (removes `Math.random()` hits).

## Role

- Primary: `backend-engineer` (broker + main.py wiring).
- Secondary (hand-offs): `frontend-engineer` (Disruption Console real-WS wiring at close), `devops-sre` (compose e2e).

## Risks / unknowns

- Sync→async bridge: `SimWorld.on_incident` runs in the SimPy worker thread; publishing must hop to the main
  loop via `asyncio.run_coroutine_threadsafe`. Mis-wiring would silently drop incidents — covered by the live e2e gate.
- Full-app boot on the Windows dev host pulls heavy/optional deps; the broker↔Redis path is therefore verified
  in isolation here, with the full-app compose e2e as the explicit close gate.
- Frontend uses `socket.io-client` while the backend `/ws` is a raw FastAPI WebSocket — reconcile at close
  (raw `WebSocket` client or a thin adapter); this is why the frontend mock-removal is a separate close step.

## Hand-off (read by scripts/seed-next-task.sh / next-task.sh when seeding the next stage)

- What is now true that wasn't before this stage:
  - A production-grade Redis pub/sub WebSocket incident broker exists (`backend/services/ws_broker.py`) with a
    `ConnectionManager` and a resilient `SimulatorEventBroker`; `main.py` wires the simulator→Redis→WS path.
  - The canonical KB_04 `incident` envelope is emitted by `build_incident_envelope`.
- What the next stage starts with:
  - A live incident fan-out the operator dashboard (PRD v2.1 §v2.1.4) and Stage 11+ agent traces ride on.
- Open items deferred to a future stage (name the stage if known):
  - Close-gate: frontend Disruption Console real-WS wiring + `Math.random()` removal (drops baseline < 436) and
    the compose-up live e2e — completes Stage 3 closure. Stage 3.5 is the CTO checkpoint #1 (read-only review).

---

*Authored 2026-05-31 (backend-engineer). Replaces the start-task.sh template seed; status in-progress until the
two close-gate criteria land.*
