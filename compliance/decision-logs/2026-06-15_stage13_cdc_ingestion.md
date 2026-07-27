# ADR — Stage 13: CDC ingestion (DB-driven incident injection)

**Date**: 2026-06-15
**Status**: Accepted (Stage 13 — follows Stage 12.5 `2026-06-15_stage12_5_observability.md`)
**Author personas**: `backend-engineer` (primary) + `devops-sre` (wal_level + container restart)
**Relates**: KB_05 (sim triggers), KB_04 (schema), KB_07 (contracts), KB_01 (topology), KB_25 (bidirectional).
Research §22. Follows Hard Rule 1a (honest degradation, no faked inject), Rule 9 (free/native), Rule 11 (research-first).
Pays G-023 (the deterministic DB half of NL/DB problem injection).

---

## Context

"A DB write triggers agent reasoning" (KB_05 §97, KB_25, PRD v3 dynamic operator features, G-023): an INSERT into
`incidents` or a trouble-status UPDATE to `stages.status` must flow into the live SimWorld as an injected event, so
every such event then runs through the Stage-11 runtime + Stage-12 audit_chain + Stage-12.5 traces.

## Decisions

**D1 — Mechanism: transactional outbox + LISTEN/NOTIFY signal + drain-on-connect (research §22).** The deepest-
honest-feasible-free CDC for our single self-hosted Postgres: every realistic alternative fails a constraint —
**Debezium** is EOL (2026-03-31); **Supabase Realtime** is a heavy Elixir server; **test_decoding** is "avoid in
prod"; **pgoutput** needs fragile from-scratch binary parsing; **wal2json** isn't in the `pgvector/pgvector:pg15`
image. The outbox pattern is research-endorsed (reliable, transactional, ordered); LISTEN/NOTIFY is the recommended
low-latency *signal* on top of the durable store (NOTIFY alone is not durable). Migration `0006_cdc_outbox`: the
`cdc_emit()` trigger on `incidents` (AFTER INSERT) + `stages` (AFTER UPDATE OF status, only on a real status change)
writes a JSON change event into the durable `cdc_outbox` within the writing txn, then `pg_notify('cdc_events', <id>)`.

**D2 — Listener: sync-psycopg in a background thread (deliberate, not async).** `backend/ingestion/cdc_listener.py`
runs the `LISTEN cdc_events` loop in a daemon thread with SYNC psycopg, because **psycopg's async mode cannot use
Windows' ProactorEventLoop — which the rest of the app needs for the MCP stdio subprocesses** (changing the global
loop policy would break that; verified `InterfaceError`). The SimWorld's `inject()` is already thread-safe, so a
thread fits naturally + is portable. On startup AND each notify it **drains** unprocessed rows (`ORDER BY id FOR
UPDATE SKIP LOCKED`), converts each via the pure `change_to_inject()` (`incidents` row → inject; `stages`
trouble-status → `machine_crack`; benign/unknown → None), injects, marks processed. **Durable** (offline-written rows
caught by the startup drain — tested), **ordered** (serial id), **low-latency** (NOTIFY). Clean bounded shutdown
(the Stage-11 ws_broker/api_client lesson).

**D3 — Honest degradation + a non-raising accessor.** No `DATABASE_URL` → the listener doesn't start (logged, not
faked). No SimWorld bound → the row is **left unprocessed** (retried on the next drain), never marked done without
actually injecting (Rule 1a). Added `api.simulation_routes.get_sim_world()` — a non-raising `Optional[SimWorld]`
accessor for background workers (the existing `_get_world()` raises a 503 for the HTTP path).

**D4 — Infra: wal_level=logical (data preserved).** The PG container was restarted with `-c wal_level=logical`
(+ `max_replication_slots`/`max_wal_senders`) on the SAME `docker_postgres-data` volume — manufacturing DB +
decisions + checkpoints + memory tables all intact (verified alembic head 0006). `wal_level=logical` is the standard
prerequisite for logical CDC even though the outbox pattern doesn't strictly need a replication slot today (it
positions us for the pgoutput WAL path later).

## Why
- The use case is "DB row write → in-process SimWorld inject", for which the outbox+NOTIFY+drain is both robust and
  the simplest honest free path; the heavier WAL-streaming machinery (Debezium/Supabase/pgoutput-to-Kafka) is only
  warranted when changes must reach a NON-Postgres sink at scale — deferred + ledgered (G-068).

## Consequences
- New: `backend/alembic/versions/0006_cdc_outbox.py`, `backend/ingestion/{__init__,cdc_listener}.py`,
  `backend/tests/ingestion/test_cdc.py` (6 tests), the explainer, this ADR, KB_TASK_LOG entry, ledger G-068.
  Modified: `backend/main.py` (lifespan start/stop), `backend/api/simulation_routes.py` (`get_sim_world`),
  KB_04/05/07/01. No new dependencies (native Postgres + psycopg).
- Verified live (Docker PG@5544, wal_level=logical): trigger emits outbox row + NOTIFY; **6 CDC tests pass**
  (converter + insert→notify→drain→inject + drain-on-connect durability); full backend suite **234 passed /
  2 skipped**; audit holds **364** (`--no-baseline-drop`; native-SQL CDC + a real listener add no grep-counted
  theatre — Rule 1a).

## Honest residual / ledger
- **G-068** — pgoutput-based WAL logical replication (for streaming changes to a non-PG sink / Kafka at scale)
  routed to Stage 15 (OT/IT bridge) or a scale stage. The outbox+NOTIFY+drain is the right pattern for the in-process
  SimWorld-inject use case today.
- The `stages.status`→inject mapping is a sensible default (trouble statuses → machine_crack); refine per pilot.

## References
- `backend/ingestion/cdc_listener.py` · `backend/alembic/versions/0006_cdc_outbox.py` · `backend/main.py` ·
  `backend/api/simulation_routes.py` · `backend/tests/ingestion/test_cdc.py`. KB_04/05/07/01/25. Research §22.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:31+00:00 -->
<!-- signature: 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 -->
