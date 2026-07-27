---
name: API Contracts
description: REST + WebSocket endpoints with request/response schemas; canonical backend-frontend contract
type: spec
last-updated: 2026-05-24-stage2
---

> **Stage 2 close (2026-05-24)** — `POST /api/simulation/inject` now drives
> the SimPy-backed `SimWorld` directly (was: enqueued to the random-tick
> `_apply_problem_behavior`). The request is validated by the Pydantic
> `InjectRequest` schema in `backend/simulation/entities/incident.py`; the
> response is `IncidentPayload` (also Pydantic). `GET /api/simulation/snapshot`
> is new — returns the current `SimWorld.snapshot()` dict. See §"Inject /
> snapshot — Stage 2 detail" below.

# KB_07 — API Contracts

## Purpose
Every REST endpoint and every WebSocket message envelope. If frontend and backend disagree on what `/api/decision` returns, this file wins until reconciled.

## Source of truth
- `backend/api/routes.py`, `backend/api/metrics_routes.py`, `backend/api/voice_routes.py`
- `backend/main.py` (WS handler)
- `backend/models/*.py` (Pydantic shapes)
- `frontend-nextjs/src/lib/api.ts` (client; currently mock-dominated)

## Versioning
- REST URLs are unversioned for v1 (single product, single client). Breaking changes get a `/api/v2/...` prefix.
- WS envelopes carry `"v": 1` (see `KB_04_Data_Schema.md`).

## REST endpoints (current state — May 2026)

| Method | Path | Status | Returns | Note |
|---|---|---|---|---|
| GET | `/health` | real | `{status: "ok", services: {...}}` | Liveness probe |
| GET | `/api/state` | real | full state snapshot | Reads from Redis hot state |
| POST | `/api/decision` | real | `Decision` (see KB_06) | Triggers a coordination cycle |
| GET | `/api/prediction` | partial | world-model prediction | Calls into `world_model.py` (random fallback until Stage 8) |
| POST | `/api/simulation/inject` | **real (Stage 2)** | `IncidentPayload` (Pydantic) | Drives `SimWorld` directly. Pydantic-validated; malformed -> 400. See §"Inject / snapshot — Stage 2 detail" below. |
| GET | `/api/simulation/snapshot` | **real (Stage 2)** | full SimWorld snapshot dict | Best-effort thread-safe read of plant state |
| GET | `/api/metrics/models` | **fake** | hardcoded MAE/R²/accuracy strings | **Returns 503 from Stage 1 onward until Stage 4 ships real metrics** |
| GET | `/api/metrics/system` | fake | hardcoded uptime/SLA strings | Returns 503 from Stage 1 until Stage 14 |
| POST | `/api/voice/process` | partial | STT+LLM+TTS pipeline result | Real if Whisper + Groq available; error otherwise |
| GET | `/api/explainability/{decision_id}` | fake | `random.uniform` SHAP values | Real implementation lands in Stage 10 |

## Inject / snapshot — Stage 2 detail

### `POST /api/simulation/inject`

**Request body** — `InjectRequest` (Pydantic; backend/simulation/entities/incident.py):

```jsonc
{
  "type": "machine_crack",       // required; one of:
                                  //   machine_crack, robot_down, late_delivery,
                                  //   demand_spike, defect_surge, power_dip
  "target_id": 4,                 // required for: machine_crack, robot_down,
                                  //   late_delivery, defect_surge.
                                  //   optional for: demand_spike, power_dip.
  "details": {                    // optional; event-specific. Defaults applied:
    "eta_minutes": 12,            //   machine_crack default
    "delay_minutes": 25,          //   late_delivery default
    "multiplier": 3.0,            //   demand_spike default
    "duration_minutes": 20,       //   demand_spike / defect_surge / power_dip default
    "rate_increase": 6.0,         //   defect_surge default
    "max_throughput_pct": 0.6     //   power_dip default
  },
  "severity": "warning"           // optional; one of: info, warning, critical (default: warning)
}
```

**Responses:**
- `202 Accepted` + `IncidentPayload` (see below) — incident enqueued; plant mutation lands on next SimPy tick (≤ 100 ms wall-clock).
- `400 Bad Request` — Pydantic validation error body. No state mutation.
- `503 Service Unavailable` — `SimWorld` not initialized (FastAPI lifespan did not run; see backend/main.py).

**`IncidentPayload` (response shape; also published on the WebSocket `incident` envelope):**

```jsonc
{
  "incident_id": "uuid-v4-string",
  "type": "machine_crack",
  "target_id": 4,
  "details": { "eta_minutes": 12.0 },
  "severity": "warning",
  "started_at": "2026-05-24T10:23:00.000Z",
  "ended_at": null
}
```

**Latency target (Stage 2 acceptance):** inject -> first WebSocket `delta` ≤ 250 ms p95 (KB_10 latency budget).

### `GET /api/simulation/snapshot`

Returns the SimWorld's best-effort snapshot. Used by calibration tests and the operator dashboard. Schema:

```jsonc
{
  "sim_time_seconds": 1234.5,
  "seed": 20260524,
  "stages": [ { "stage_id": 0, "name": "intake", "queue_depth": 3, "status": "nominal", "units_produced": 42, "units_defective": 1, "defect_rate_effective": 0.005 }, ... ],
  "robots": [ { "id": 0, "battery": 0.83, "status": "moving", "queue_len": 1, "completed_tasks": 12, "charge_cycles": 0 }, ... ],
  "suppliers": [ { "id": 0, "sku": "default", "fulfilled": 4, "failed": 0 }, ... ],
  "orders_started": 80,
  "orders_complete": 72,
  "throughput_units_per_hour": 482.3,
  "amr_utilization": 0.68,
  "modulation": { "demand_multiplier": 1.0, "throughput_cap_pct": 1.0 },
  "incidents_fired_count": 3
}
```

## WebSocket endpoint

- `ws://{host}:8000/ws` — single channel, server-pushed broadcasts every 100–200 ms. Envelopes per `KB_04` "WebSocket message envelopes" section.

## Stage 1 changes

- `/api/metrics/models` and `/api/metrics/system` switch from hardcoded demo to `503 Service Unavailable` until real metrics exist (Stage 4 for models, Stage 14 for system).
- All endpoints get OpenAPI tags so the auto-generated `/docs` is readable.
- CORS is restricted to `localhost:3000` (and configured per-env via `.env`).

## Stage 3 changes (kill frontend mocks)

- Frontend `getMockState()` (`frontend-nextjs/src/lib/api.ts:233-358`) only fires when WS has been disconnected > 5 s.
- An "Offline" banner is rendered while the mock is active.

## Stage 12 changes (operator surface)

- New REST `POST /api/chat/translate` — translates an operator's natural-language problem statement into a structured `inject` payload, returns the parsed event for confirmation.
- New WS inbound envelope `override` (see `KB_06`).

## Stage 13 changes (DB-driven) — BUILT 2026-06-15

- **CDC ingestion is a server-internal mechanism, not an HTTP/WS contract.** A DB write (INSERT `incidents` /
  trouble-status UPDATE `stages.status`) → `cdc_emit()` trigger → durable `cdc_outbox` row (`{table_name, op, row_pk,
  change}` jsonb) + `pg_notify('cdc_events', <id>)` → `backend/ingestion/cdc_listener.py` drains + `change_to_inject()`
  → `SimWorld.inject()`. The row-diff is converted to an `InjectRequest` internally; nothing new is exposed to the
  frontend. (Replaces the original "Supabase Realtime `db_event` WS" sketch with the research-§22 transactional-outbox
  + LISTEN/NOTIFY + drain-on-connect pattern — durable, ordered, free, single-PG.) Non-raising accessor
  `api.simulation_routes.get_sim_world()` added for the background worker.

## Response time targets

Every endpoint must hit the per-hop budget in `KB_10_Production_Hardening.md`. Specifically:
- `GET /api/state` p95 ≤ 60 ms (Redis read + serialization).
- `POST /api/decision` p95 ≤ 250 ms (drives the latency budget; world-model + PPO + LLM).
- `POST /api/simulation/inject` p95 ≤ 100 ms (sim engine write + broadcast).
- `GET /api/explainability/{decision_id}` p95 ≤ 50 ms when cached; ≤ 1 s on cache miss (async backfill).

## Error envelope

All errors return:
```json
{"error": {"code": "string", "message": "human readable", "incident_id": "uuid-or-null"}}
```
Codes are stable; messages can change. Frontend matches on `code`.

### WebSocket `incident` delivery (Stage 3, 2026-05-31)

`GET /ws` clients now receive a live `incident` message for every simulator event, fanned out by the
`SimulatorEventBroker` (`backend/services/ws_broker.py`) subscribed to Redis `pubsub:simulator:events`. The
message is the canonical KB_04 envelope:

```json
{"v": 1, "type": "incident", "ts": "<iso8601>", "incident_id": "<uuid>", "payload": { /* IncidentPayload */ }}
```

`payload` is the `IncidentPayload` shape documented above (incident_id, type, target_id, details, severity,
started_at, ended_at). Delivery target: KB_10 budget p95 ≤ 250 ms inject→client (verified at Stage 3 close on
the compose stack). Dead/slow clients are pruned by `ConnectionManager.broadcast`.

## MCP tool surface (Stage 11.5, 2026-06-15)

Internal **agent→tool** contract (NOT HTTP REST; Model Context Protocol over stdio/streamable-HTTP). Five FastMCP
servers under `backend/mcp_servers/`; full inventory + schemas in [KB_16](KB_16_A2A_MCP_Protocols.md). Every tool
returns `{"available": bool, ...}` — `available:false` + `reason` is the honest "backend unavailable" path (no
fabrication). Namespaced `server.tool` when mounted into the runtime (`MCPToolMount`, 14 tools).

| Server | Tools | Returns (available:true) |
|---|---|---|
| model_inference | `predict_failure`, `predict_demand`, `classify_defect` | `{p_fail,at_risk,arch}` / `{forecast,window}` / `{label,confidence,probabilities}` |
| policy_query | `recommend_action`, `explain_action` | `{stage_id,kind,rationale,diagnosis}` / `{top_drivers,counterfactual,method}` |
| kpi_query | `throughput`, `oee`, `utilization`, `queue_depth` | KPI dicts computed from a plant snapshot (real A×P×Q OEE) |
| sim_world | `inject_event`, `query_state`, `subscribe_events` | incident dict / plant snapshot / fired-events list |
| decision_log | `append_decision`, `query_decisions` | `{decision_id,persisted}` / `{count,decisions[]}` (Postgres `decisions` table; audit_chain at 13.5) |

Transport: stdio (CI tests + runtime mount) / streamable-HTTP (supervised production, ports 9101-9105). Conformance:
`backend/tests/mcp/` (22 tests) + CI gate `mcp-conformance`.

## Conversational Factory Intelligence — `/factory/*` (Stage 29, 2026-07-12) — BUILT

Free/local (Groq→Ollama, Rule 9); every surface answers from real data or degrades honestly. Router:
`backend/api/conversation_routes.py`.

| Method | Path | Body | Behaviour |
|---|---|---|---|
| POST | `/factory/ask` | `{question, use_llm?}` | G-022 — grounded operational QA + "why did X happen?". Gathers REAL evidence (Art-12 `decision.trace` rows via `audit_chain.read_recent` + Stage-28 GraphRAG + live sim) with citable handles; LLM synthesis is constrained to that evidence and MUST cite handles; **no evidence → `"I have no evidence for that."`** (Verifier pattern, §40.1). Never fabricates. |
| POST | `/factory/inject` | `{report, run_loop?, use_llm?}` | G-023 — NL problem injection. Parses NL → strict Pydantic `InjectedIncident` (LLM structured output + re-ask; deterministic keyword fallback; honest abstain on unknown) → `SimWorld.inject()` / the validator-gated self-healing loop. **Hard Rule 3: the LLM never actuates** — it produces a proposed structured incident that enters the same gated path as a sensor-fired one. |
| POST | `/factory/diagnose` | `{commit_threshold?, max_probes?, tpr?, fpr?}` | G-026 — information-gain active diagnosis over the LIVE sim stages: probe→reason→commit/abstain (KB_25 §1b). No bound sim → `{"available": false}` (honest-unavailable). |
| POST | `/factory/db-edit` | `{table, column, old_value?, new_value, target_id?, context?, run_loop?}` | G-024 (Stage 37) — bidirectional CDC: DIAGNOSE the problem an operator's DB value-edit induces (root-cause, not a canned incident) → optionally drive the validator-gated self-healing loop. `stages`/`inventory`/`suppliers` value columns → `defect_surge`/`machine_crack`/`power_dip`/`late_delivery` with **magnitude-derived severity**; a benign/unmonitored edit → `{"diagnosed": false}` (honest — no fabricated problem). The reasoning is signed to `audit_chain` (`cdc.diagnose`, Art-12). **Hard Rule 3: the reasoner proposes; it never actuates** (sole emitter stays `master.dispatch_order`). Same reasoning the live CDC trigger drives (migration `0010_cdc_value_changes`). |

Supersedes the Stage-12 `POST /api/chat/translate` sketch (line ~130) with the real, validated `/factory/inject`.

## Facilities / Energy — `/facilities/*` (Stage 38, 2026-07-18) — BUILT

| Method | Path | Body | Behaviour |
|---|---|---|---|
| POST | `/facilities/optimize-energy` | `{required_slots?, horizon_slots?, demand_cap_kw?, window_start?, window_end?}` | G-018 (Stage 38) — the KB_25 energy loop: observe the sim's REAL per-stage `nominal_kw` → DIAGNOSE an approaching demand-charge breach (when `demand_cap_kw` set) → REASON via a **real MILP** (`scipy.optimize.milp`/HiGHS) peak-shaving + load-shifting against a documented ToU + demand-charge tariff → VERIFY the load-shift through `safety/validator.validate()` under the `energy_load_shift` contract (**Hard Rule 3: the agent proposes; `master.dispatch_order` stays the sole actuator emitter**) → return the gated plan + measured `peak_reduction_pct`/`cost_reduction_pct` (signed to `audit_chain` as `energy.load_shift`, Art-12). Honest: a fully-constrained facility returns 0% reduction, never a fabricated saving. |

## Last verified
- 2026-07-18 — Stage 38 (G-018, Facilities/Energy head-agent): new `POST /facilities/optimize-energy` (MILP peak-shaving/load-shifting over the sim's real per-stage nominal_kw, validator-gated, audit-signed). Cross-checked against `backend/agents/facilities/*` + `backend/api/facilities_routes.py` + `main.py` registration + `backend/tests/facilities/test_facilities.py` (15) + the A/B artefact `training/evals/results/energy_ab.json` (peak −22.1% mean, all floors held) + a live cycle signing audit_seq. Hard Rule 3 preserved; audit holds 3.
- 2026-07-18 — Stage 37 (G-024, bidirectional CDC): new `POST /factory/db-edit` (diagnose a DB value-edit → self-optimize) + the live-CDC path via migration `0010_cdc_value_changes` (a `cdc_emit_value()` trigger on `stages`/`inventory`/`suppliers` value columns → `cdc_outbox`+NOTIFY → `cdc_reasoner.diagnose_change` → the same self-healing loop). Cross-checked against `backend/ingestion/cdc_reasoner.py` + `cdc_listener.py` + `backend/api/conversation_routes.py` + `backend/tests/ingestion/test_cdc_reasoner.py` (22) + `tests/conversation/test_conversation_routes.py` (route tests) + a LIVE `UPDATE stages SET defect_rate=0.15` roundtrip. Hard Rule 3 preserved; audit chain green (10,477 rows).
- 2026-07-18 — Stage 35 (C6-R3 tail): `POST /factory/ask` + `POST /factory/inject` gain an OPTIONAL `session_id` for multi-turn dialogue (durable Postgres sliding-window session store; history aids phrasing/coreference; the grounding/Verifier honest-empty invariant is preserved — history is never cited as evidence). Cross-checked against `backend/conversation/session_store.py` + `ask.py`/`nl_inject.py` + `backend/tests/conversation/test_session_store.py` (6 tests) + live Groq coreference smoke.
- 2026-07-13 — Stage 34 (G-047/G-032, frontend honesty): the `/api/metrics/models` + `/api/metrics/embodied` endpoints honestly **503 until real metrics are recorded** (they never fabricate); the frontend now matches that honesty — `lib/api.ts` returns `{}`/`null` on error (the `getMock*` fabricated fallbacks are DELETED) and the `model-metrics` page renders real data or an honest "no live metrics recorded" empty-state (pointing to the model cards). `simulation/page.tsx` reads the REAL `SimulationState` shape; `next build` type-checks strictly (`ignoreBuildErrors:false`). Cross-checked against `frontend-nextjs/src/lib/api.ts` + `app/model-metrics/page.tsx` + `app/simulation/page.tsx` + `tsc --noEmit` (0) + `npm run build` (exit 0).
- 2026-07-12 — Added the `/factory/*` conversational surface (Stage 29); cross-checked against `backend/api/conversation_routes.py` + `backend/conversation/*` + the passing `backend/tests/conversation/` suite (25 tests).
- 2026-05-11 — Plan-mode session. Endpoint list cross-checked against `backend/api/routes.py` and `metrics_routes.py`.
- 2026-05-31 — Added WS `incident` delivery contract (Stage 3 broker); cross-checked against `backend/services/ws_broker.py` + `backend/main.py`.
- 2026-06-15 — Added the MCP tool surface (Stage 11.5); cross-checked against `backend/mcp_servers/*` + `backend/agents/runtime/mcp_mount.py` + the passing `backend/tests/mcp/` suite.
- 2026-07-12 — Stage 30 (G-036): the supply-chain state's 7-day `demand_forecast` is now SERVED by `services/demand_forecast_service.py` (real LSTM / empirical / honest labelled baseline) and carries `demand_forecast_source` + `demand_forecast_served` (+ `demand_forecast_note`) provenance fields; the legacy fabricated per-day `confidence` is REMOVED. Cross-checked against `backend/services/state_manager.py::_create_initial_supply_chain` + `backend/tests/services/test_demand_forecast_service.py`.
