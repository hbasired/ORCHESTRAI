---
status: done
stage: 13
slug: cdc_ingestion
created: 2026-06-15
closed: 2026-06-15
---

# Stage 13 — CDC Ingestion (DB-driven incident injection)

> A DB write triggers agent reasoning: an INSERT into `incidents` (or a trouble-status UPDATE to `stages`) flows
> into the live SimWorld as an injected event — closing the bidirectional "edit the DB to make an agent problematic"
> loop (KB_05 §97, KB_25, PRD v3 §"dynamic operator features", G-023). Research §22; chosen mechanism: the
> research-endorsed **transactional outbox + LISTEN/NOTIFY signal + drain-on-connect** (Debezium is EOL 2026-03;
> Supabase Realtime is a heavy Elixir server; test_decoding is "avoid in prod"; pgoutput needs fragile from-scratch
> binary parsing; wal2json isn't in the image).

## Cross-cutting requirements

- [x] Read KB_24 (HLD/LLD) + KB_25 (self-healing) — CDC feeds the loop's `observe` via injected incidents.
- [x] Folded OPEN gaps ≤ Stage 13: **G-023** (NL/DB problem injection — the DB path is the deterministic half).
- [x] SOTA research-first → `research/initial-research.md` §22 (Postgres CDC 2026); deepest-honest-feasible-free
  path justified (outbox+NOTIFY+drain over the alternatives that each fail a constraint).
- [x] Free-cost only: native Postgres + psycopg (already present); no Kafka/Elixir/paid SaaS; no new deps.
- [x] Stage explainer `research/stage-explainers/STAGE_13/index.html`.

## Pre-requisites

- Stages 11–12.5 closed; Postgres (`wal_level=logical` set — restarted the container with it; data preserved).
- ADRs honoured: Stage-12 memory, Stage-12.5 observability.

## Acceptance criteria

- [x] Alembic `0006_cdc_outbox` creates `cdc_outbox` + the `cdc_emit()` trigger fn + triggers on `incidents`
  (AFTER INSERT) and `stages` (AFTER UPDATE OF status) — applied to the Docker PG; trigger verified (INSERT →
  outbox row + `pg_notify('cdc_events', <id>)`).
- [x] `backend/ingestion/cdc_listener.py::CDCListener` — sync-psycopg **background thread** (psycopg async can't use
  Windows' ProactorEventLoop, which the MCP stdio path needs); `LISTEN cdc_events` + drain-on-connect + per-notify
  drain; converts row-diffs to `InjectRequest` and injects into the live SimWorld; clean bounded shutdown.
- [x] `change_to_inject(table, change)` pure converter: `incidents` row → inject; `stages` trouble-status → a
  `machine_crack` on that stage; benign status / unknown table → None. (Unit-tested, no infra.)
- [x] Durable: rows written while the listener is OFFLINE are caught by the startup drain (`FOR UPDATE SKIP LOCKED`,
  ordered by serial id) — tested live.
- [x] `backend/main.py` lifespan starts the listener after the SimWorld is bound + stops it (bounded) on shutdown;
  honest no-op without `DATABASE_URL`. Added a non-raising `api.simulation_routes.get_sim_world()` accessor.
- [x] `pytest tests/ingestion/ -q` green — **6 passed** (4 converter + 2 live: insert→notify→drain→inject, and
  drain-on-connect durability) against the real Docker PG. Full backend suite **234 passed / 2 skipped**.
- [x] `scripts/audit.sh` HOLDS at 364 (`--no-baseline-drop`; native-SQL CDC + a real listener add no grep-counted
  theatre — Rule 1a).
- [x] Independent review PASS (Rule 11b) — `audits/STAGE_13_independent_review.md`.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/alembic/versions/0006_cdc_outbox.py` | cdc_outbox table + cdc_emit() trigger fn + triggers |
| `backend/ingestion/__init__.py` | package marker |
| `backend/ingestion/cdc_listener.py` | thread-based LISTEN + drain + row-diff→inject |
| `backend/tests/ingestion/test_cdc.py` | converter (no infra) + live roundtrip + durability |
| `research/stage-explainers/STAGE_13/index.html` | explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/main.py` | start/stop the CDC listener in the lifespan |
| `backend/api/simulation_routes.py` | add non-raising `get_sim_world()` accessor |
| `knowledge-base/KB_04_Data_Schema.md` | document `cdc_outbox` + the trigger |
| `knowledge-base/KB_05_Simulation_Spec.md` | DB-driven inject path now BUILT |
| `knowledge-base/KB_07_API_Contracts.md` | the CDC `db_event` ingestion contract |
| `knowledge-base/KB_01_System_Architecture.md` | topology (CDC built) |

## KB files this stage updates

- `KB_04_Data_Schema.md`, `KB_05_Simulation_Spec.md`, `KB_07_API_Contracts.md`, `KB_01_System_Architecture.md`, `KB_TASK_LOG.md`

## Verification commands

```bash
cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing alembic upgrade head
cd backend && DATABASE_URL=... pytest tests/ingestion/ -q
bash scripts/audit.sh   # 364
```

## Audit target

- Pre: 364. Target: hold (native-SQL CDC + listener wrap real injects; no grep-counted theatre to remove). `--no-baseline-drop`.

## Role

- Primary: `backend-engineer`. Secondary: `devops-sre` (the `wal_level=logical` + container restart).

## Risks / unknowns

- pgoutput-based WAL logical replication (for streaming changes to a NON-Postgres sink at scale) deferred → **G-068**
  (Stage 15 OT/IT bridge / a scale stage). The outbox+NOTIFY+drain is the right pattern for the in-process
  SimWorld-inject use case.
- The `stages.status`→inject mapping is a sensible default (trouble statuses → machine_crack); refine per pilot.

## Hand-off

- What is now true: external systems / operators can drive the agent by writing the DB — an INSERT into `incidents`
  (or a trouble-status UPDATE to `stages`) is durably, transactionally captured and injected into the live SimWorld;
  every such inject still flows through the Stage-11 runtime + Stage-12 audit_chain + Stage-12.5 traces.
- What the next stage (13.5 PQC Foundations) starts with: the `audit_chain` placeholder signatures become real
  ML-DSA-65 (KeyProvider + `backend/crypto/pqc_signing.py`); the zero-trust agent-identity work (G-064) begins.
- Open items deferred: pgoutput WAL logical replication for non-PG sinks (G-068); the operator-UI DB-edit surface.
