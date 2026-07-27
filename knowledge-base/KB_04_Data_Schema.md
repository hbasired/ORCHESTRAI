---
name: Data Schema
description: Postgres schema, Redis keys, SimPy entity model, WebSocket message envelopes, Pydantic schemas
type: spec
last-updated: 2026-06-12-stage6
---

# KB_04 — Data Schema

## Purpose
Single source of truth for every data shape in the system: tables, Redis keys, simulator entities, WebSocket message envelopes, REST request/response Pydantic schemas. If frontend and backend disagree on a shape, this file is the arbiter.

## Source of truth
- `backend/alembic/versions/*.py` (post Stage 1 — schema authoritative)
- `database/schema.sql` (current, pre-Alembic — to be retired by Stage 1)
- `backend/models/*.py` (Pydantic schemas)
- WebSocket envelope definitions in `backend/main.py` and `backend/api/routes.py`
- Redis key conventions in `backend/services/state_manager.py` (or equivalent)

## Postgres schema (post Stage 1)

**Authority moved from `database/schema.sql` (now archival) to
`backend/alembic/versions/0001_init.py`.** That migration creates the
following tables — exact column-level DDL is in the migration file:

| Table | Purpose | New in Stage 1? |
|---|---|---|
| `robots` | Current robot state | no |
| `stages` | Current production-stage state | no |
| `decisions` | AI decisions with reasoning, confidence, override metadata | no |
| `suppliers` | Supplier directory | no |
| `supply_orders` | Open / fulfilled supply orders | no |
| `inventory` | Material stock levels | no |
| `telemetry_log` | Time-series metric stream | no |
| `alerts` | Operator-facing alerts | no |
| `system_metrics` | Aggregated KPI snapshots | no |
| `override_log` | Human override audit trail | no |
| **`incidents`** | Per-incident anchor row (UUID PK, started_at, ended_at, type, target_id, details JSONB, severity) | **yes** |
| **`decision_logs`** | Per-call agent-tool audit ledger (UUID PK, FK → incidents, caller, tool, input/output hashes, JSONB inputs/outputs, operator_override boolean, override_reason). 6-month retention enforced by a Stage-3 cleanup job. | **yes** |

EU AI Act Art. 12 evidence: every agent tool call writes a `decision_logs`
row; every problem the simulator (or external CDC) fires writes an
`incidents` row.

`wal_level=logical` is set on Postgres in the compose file (Stage 1) so
Stage 13's Supabase Realtime CDC works without a Postgres restart. The
self-hosted Supabase services themselves (Realtime / Studio / Meta / REST)
are deferred — see `compliance/decision-logs/2026-05-11_stage_01_close.md`.

## Redis keys

Convention: `{namespace}:{entity_type}:{entity_id}`

- `state:robot:<id>` — JSON of current robot state (position, battery, task). TTL 30s; refreshed by sim loop.
- `state:stage:<id>` — JSON of current stage state (queue, throughput, status). TTL 30s.
- `state:summary` — top-level KPI snapshot used by `/` dashboard. TTL 5s.
- `pubsub:simulator:events` — pub/sub channel for SimPy event broadcasts.
- `pubsub:agent:decisions` — pub/sub channel for embodied-agent decision events.
- `pubsub:ws:broadcast` — pub/sub channel multi-worker WS broker uses (Stage 3 introduces).
- `cache:shap:<decision_id>` — cached SHAP attribution. TTL 1 h.
- `cache:dice:<decision_id>` — cached DiCE counterfactual (Stage 10). TTL 1 h.

## SimPy entity model (Stage 2)

```
class Robot:
  id: int
  position: (float, float)
  battery: float   # 0.0 to 1.0
  task: Optional[Task]
  velocity: (float, float)
  status: Literal["idle", "moving", "charging", "fault"]

class Stage:
  id: int
  type: str        # e.g. "press", "weld", "qc"
  capacity: int    # max queue
  cycle_time: float  # mean, with stochastic noise
  throughput: float
  mtbf: float
  mttr: float
  status: Literal["nominal", "degraded", "broken"]

class Supplier:
  id: int
  sku: str
  lead_time: float  # mean, with stochastic noise
  reliability: float

class Incident:
  incident_id: UUID
  type: Literal["machine_crack", "robot_down", "late_delivery", "demand_spike", "defect_surge", "power_dip"]
  target_id: int
  eta_minutes: float
  details: dict
```

## WebSocket message envelopes

Outbound (server → client) — every message has the shape:

```json
{
  "v": 1,
  "type": "state_snapshot" | "delta" | "incident" | "decision" | "explanation"
        | "prediction" | "diagnosis" | "intervention" | "ab_report",
  "ts": "2026-05-11T18:00:00.000Z",
  "incident_id": "uuid-or-null",
  "payload": { ... type-specific shape ... }
}
```

Types and payloads:
- `state_snapshot` — full state (sent on connect, on resume after disconnect). Payload: `{robots: [...], stages: [...], suppliers: [...], inventory: [...], summary: {...}}`.
- `delta` — incremental update (5–10 Hz). Payload: only changed fields, keyed by entity id.
- `incident` — problem fired (button click, chat translation, or DB-driven CDC). Payload: `Incident` shape above.
- `decision` — agent action. Payload: `{decision_id, agent, action, target, reasoning, predicted_reward, timestamp}`.
- `explanation` — SHAP + DiCE for a decision. Payload: `{decision_id, shap_values, integrated_gradients, counterfactual, top_features}`.
- **Stage 6 slice family (2026-06-12; built by `services/ws_broker.py::build_slice_envelope`, published pre-enveloped on the simulator Redis channel):**
  - `prediction` — at-risk machine sample. Payload: `{kind, sim_time_seconds, payload: {stage_id, telemetry, prediction: {p_fail, at_risk, threshold, arch, dataset}}}`.
  - `diagnosis` — ranked root-cause. Payload: `Diagnosis.to_dict()` (`{stage_id, p_fail, at_risk, primary_cause, hypotheses: [{cause, score, evidence, recommended_action}]}`).
  - `intervention` — coordinator decision + execution flag. Payload: `InterventionDecision.to_dict()` + `{executed: bool}`.
  - `ab_report` — A/B experiment summary (see `backend/training/evals/stage06/results.json` shape).

Inbound (client → server) — currently only ping/pong. Stage 12 adds:
- `override` — operator override of an agent decision. Payload: `{decision_id, override_action, reason}`.

## Pydantic schemas

Live in `backend/models/`. Stage 1 audits them for completeness against this file; any missing shape becomes a TODO in `KB_TASK_LOG.md`.

## Stage 12 memory tables (2026-06-15)

| Table | Migration | Purpose |
|---|---|---|
| `audit_chain` | `0003_audit_chain` | Append-only EU-AI-Act Art-12 evidence. Cols: `seq` (bigserial PK), `ts`, `actor`, `action`, `payload` (jsonb), `prev_hash`/`hash` (bytea; `hash = SHA-256(prev_hash‖canonical(payload))`), `sig_mldsa` (bytea), `key_version`, `algorithm`. **BEFORE UPDATE/DELETE triggers RAISE** (`no_update`/`no_delete`) → append-only at the DB level. Placeholder signature (`algorithm='placeholder-sha256'`, `key_version=0`) until Stage 13.5 swaps in real ML-DSA-65. |
| `isa95_metadata` | `0004_isa95_metadata` | Relational mirror of the Neo4j ISA-95 graph for SQL joins. Cols: `id` (PK, shared with the Neo4j node), `isa95_class` (CHECK ∈ ISA-95 Part-2 classes), `name`, `parent_id` (self-FK), `attributes` (jsonb), timestamps. Graph is source of truth; `graph_isa95.py` keeps the mirror in sync. |
| `mem0_memories` | `0005_mem0` | Episodic/semantic store. Cols: `id` (uuid PK), `namespace`, `content`, `embedding` (`vector(MEM0_EMBED_DIM)`, default 1024), `metadata` (jsonb), `created_at`/`updated_at`, `retained_until`. **HNSW** cosine index (`mem0_memories_vec USING hnsw (embedding vector_cosine_ops)`; research §19.2). Requires the `vector` extension (`pgvector/pgvector:pg15` image). Namespace-isolated in `mem0_adapter.py`. |
| `cdc_outbox` | `0006_cdc_outbox` | **Stage 13 transactional-outbox CDC** (research §22). Cols: `id` (bigserial PK), `table_name`, `op`, `row_pk`, `change` (jsonb row-diff), `created_at`, `processed_at` (NULL until drained). The `cdc_emit()` trigger on `incidents` (AFTER INSERT) + `stages` (AFTER UPDATE OF status) writes a JSON change event here within the writing txn, then `pg_notify('cdc_events', <id>)`. `backend/ingestion/cdc_listener.py` LISTENs + drains (`FOR UPDATE SKIP LOCKED`, ordered) → SimWorld inject. Partial index `cdc_outbox_unprocessed (id) WHERE processed_at IS NULL`. Needs `wal_level=logical` set on the container. |

Migration chain: `0001_init → 0002_langgraph_checkpoints → 0003_audit_chain → 0004_isa95_metadata → 0005_mem0 → 0006_cdc_outbox`.

## Last verified
- 2026-05-11 — Plan-mode session. `database/schema.sql` confirmed present; Alembic dir not yet created; Redis key conventions exist informally in code and are codified here for the first time.
- **2026-06-12 (Stage 6)** — slice envelope family (`prediction`/`diagnosis`/`intervention`/`ab_report`) added to the outbound enum (drift caught by the Stage 3 independent re-audit; fixed same day).
- **2026-05-11 (Stage 1 close)** — Alembic created (`backend/alembic/`); first migration `0001_init.py` ships in this PR with verbatim ports of all pre-existing tables + the new `incidents` and `decision_logs` tables. `database/schema.sql` is now archival.
