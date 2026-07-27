# Stage 13 — Independent Review (CDC Ingestion: DB write → SimWorld inject)

- **Reviewer**: independent `task-auditor` persona (a DIFFERENT agent than the Stage-13 implementer).
- **Date**: 2026-06-15
- **Verification mode**: **DYNAMIC** — live Docker Postgres (`pgvector/pgvector:pg15`, `wal_level=logical`) on
  host port **5544**. CDC tests, the audit, and direct SQL trigger probes were all run by this auditor.
- **Verdict**: **PASS** (with 3 low-severity, non-blocking findings — all documentation/test-robustness, none
  theatre, none blocking close).

---

## What was reviewed

`backend/alembic/versions/0006_cdc_outbox.py`, `backend/ingestion/cdc_listener.py`,
`backend/ingestion/__init__.py`, `backend/main.py` (lifespan), `backend/api/simulation_routes.py`
(`get_sim_world()`), `backend/tests/ingestion/test_cdc.py`, the ADR
`compliance/decision-logs/2026-06-15_stage13_cdc_ingestion.md`, `research/initial-research.md` §22,
KB_01/04/05/07, `audits/OPEN_GAPS_LEDGER.md` (G-068), `tasks/STAGE_13_cdc_ingestion.md`,
`research/stage-explainers/STAGE_13/index.html`. Supporting reads: `backend/simulation/sim_world.py`
(`inject()` thread-safety), `backend/simulation/entities/incident.py` (`InjectRequest` schema),
`backend/alembic/versions/0001_init.py` (`incidents`/`stages` table definitions).

---

## Dynamic verification (commands this auditor actually ran)

| Command | Result |
|---|---|
| `DATABASE_URL=…@localhost:5544/… python -m pytest tests/ingestion/ -q` | **6 passed, 1 warning in 4.58s** (4 converter + 2 live: NOTIFY→drain→inject + drain-on-connect durability) |
| `bash scripts/audit.sh` | **TOTAL 364**; baseline 364 → holds (matches declared `--no-baseline-drop`) |
| `SELECT current_setting('wal_level')` | **`logical`** (confirmed) |
| `cdc_outbox` table + `pg_trigger` probe | table exists; both triggers present: `cdc_incidents_insert`, `cdc_stages_status_update` |
| `SELECT version_num FROM alembic_version` | **`0006_cdc_outbox`** (migration is at head) |
| `INSERT INTO incidents(...)` then count `cdc_outbox` | **+1 outbox row**, change diff = `{type, details, severity, target_id}` — trigger writes the durable row + fires |
| `UPDATE stages SET status='offline'` (in a rolled-back txn) | **+1 outbox row**, diff = `{name, stage_id, old_status:'normal', new_status:'offline'}` |
| no-op `UPDATE stages SET status='offline'` (same value) | **+0 rows** — the `IS NOT DISTINCT FROM` guard works |
| `UPDATE stages SET name=…` (non-status column) | **+0 rows** — the `AFTER UPDATE OF status` scoping works |
| `change_to_inject('stages', {…new_status:'offline'…})` | → `InjectRequest(machine_crack, target_id=1, severity=warning, source='cdc:stages.status')` |
| `change_to_inject('stages', {new_status:'bottleneck'/'warning'})` | → `None` (non-actionable) |
| `change_to_inject('incidents', late_delivery, target_id=None)` | → `None` (validator raises → caught → honest drop) |

> Note: the full backend suite (`pytest -q`) was launched against live infra to confirm the implementer's
> "234 passed / 2 skipped" claim, but the run hit a **`pytest-timeout` while an unrelated test was performing a
> HuggingFace Hub model download over the network** (traceback in `xet_get`/`_hf_hub_download_to_cache_dir`) — a
> network/environment artifact, NOT a Stage-13 regression (no CDC test touches HuggingFace). The full count could
> therefore not be independently reproduced this session. The **Stage-13-specific** evidence above is fully and
> independently confirmed and is what this verdict rests on; the broader suite count remains the implementer's
> claim and is not load-bearing for this stage.

---

## Honesty audit (Hard Rule 1 / 1a) — read the actual code, did not trust the ADR

**No theatre found.** The full fabrication surface was swept:

- **No DB → honestly disabled.** `cdc_listener.py:73-74` — `if not self._dsn: logger.warning(...); return False`.
  `main.py:242-245` sets `cdc_listener = None` when `start()` returns False. No faked listener.
- **DB unreachable → honest failure, not faked.** `_run_loop` `cdc_listener.py:103-110` sets `_failed` and closes
  conns; `start()` returns False. No fabricated "connected" state.
- **No SimWorld bound → row LEFT UNPROCESSED (real durability), not marked done.** `_apply` `cdc_listener.py:165-166`
  — `if sw is None: return False`, and `_drain` only adds an id to `done_ids` (→ `processed_at = now()`) when
  `_apply` returns True (`cdc_listener.py:140-141`). Confirmed: a non-actionable row returns True (handled, line
  159) but a no-world row returns False and is retried. This is real, not theatre.
- **`change_to_inject` builds REAL `InjectRequest`s from the row diff** (`cdc_listener.py:31-56`) — no hardcoded /
  canned inject. `incidents` row → `InjectRequest(type=change["type"], target_id=…, details=…, severity=…)`;
  `stages` trouble-status → `machine_crack` on `int(stage_id)`. Verified live that the trigger's emitted diff feeds
  straight through the converter into a valid request.
- **The trigger writes a durable outbox row in the writing txn + `pg_notify`** (`0006_cdc_outbox.py:74-77`) — the
  `INSERT INTO cdc_outbox … RETURNING id` then `PERFORM pg_notify(...)` are inside the trigger fn, so the outbox row
  commits atomically with the change. Verified live (an `INSERT` produced exactly one outbox row).
- **Drain is real CDC mechanics** (`cdc_listener.py:130-146`): `SELECT … WHERE processed_at IS NULL ORDER BY id FOR
  UPDATE SKIP LOCKED LIMIT %s`, convert+inject, then `UPDATE … SET processed_at = now() WHERE id = ANY(%s)`. Ordered
  by serial id, skip-locked for concurrency, marks processed only after a successful inject. Real.
- **Durability claim is real.** `test_drain_on_connect_catches_offline_writes` inserts a row with **no listener
  running**, then `start()` (whose first action is `_drain`, `cdc_listener.py:112`) catches it. Passed live.
- Grep of the new code for `random.uniform|random.choice|Math.random|generateMockState|_get_demo|RESPONSES = {|
  MODELS = [`: none in `backend/ingestion/`. `audit.sh` holds at 364 (necessary-but-not-sufficient; the code read
  above is the sufficient check).

## Mechanism — is the sync-thread-not-async decision honest? (criterion D2)

Justification is accurate. `cdc_listener.py:96-128` uses **sync** psycopg in a daemon thread; the stated reason
(psycopg async cannot use Windows' ProactorEventLoop, which the MCP stdio path needs) is consistent with the
Stage-11.5 MCP stdio design. The SimWorld `inject()` is genuinely thread-safe — `sim_world.py:113,145` enqueue onto
a `queue.Queue` (`thread_queue.Queue`), so a foreign thread calling `inject()` is safe (verified by reading the
method, not assumed). **Clean bounded shutdown is real**: `stop()` `cdc_listener.py:174-179` sets `_stop` then
`await asyncio.to_thread(self._thread.join, 6.0)` (bounded join — the Stage-11 ws_broker lesson applied); the loop
checks `_stop` every ≤1 s (`notifies(timeout=1.0)`, line 117). `main.py:278-282` calls `stop()` in the lifespan
shutdown under try/except. No unbounded join, no leaked thread.

## Tests — real, not theater (criterion: tests honest)

- **Converter tests** (`test_cdc.py:15-34`) assert real field-level behaviour (type, target_id, severity, the
  injected `source` tag, benign→None, unknown-table→None). Meaningful.
- **Live roundtrip + durability** actually `psycopg.connect` + `INSERT` into the real DB and assert
  `listener.injected >= 1`. Not mock-asserting. Both passed live this session.
- The "worker thread not needed / we assert the listener injected" note is honest: the tests verify the **listener's**
  responsibility (drain → call `inject()`), not the separate Stage-2 SimPy mutation.

---

## Acceptance criteria — independently confirmed

| Criterion (task doc) | Claimed | Confirmed? | Note |
|---|---|---|---|
| `0006` creates `cdc_outbox` + `cdc_emit()` + triggers; INSERT→outbox+NOTIFY | [x] | **YES (live)** | table + both triggers present; INSERT→+1 row verified; `pg_notify` is in the fn |
| `CDCListener` sync-thread, LISTEN + drain-on-connect + per-notify drain + bounded shutdown | [x] | **YES** | code read + 6 tests + the sync/async rationale is accurate |
| `change_to_inject` pure converter (incidents→inject; stages trouble→machine_crack; benign/unknown→None) | [x] | **YES (live + unit)** | verified against the trigger's real emitted diff |
| Durable: offline-written rows caught by startup drain | [x] | **YES (live)** | dedicated test passed; `_drain` runs first in the loop |
| `main.py` lifespan starts after world bound + bounded stop; no-op without `DATABASE_URL`; `get_sim_world()` added | [x] | **YES** | `main.py:231-248,278-288`; `simulation_routes.py:56-61` non-raising accessor |
| `pytest tests/ingestion/ -q` green (6) | [x] | **YES** | 6 passed, 4.58 s, live |
| `audit.sh` HOLDS at 364 (`--no-baseline-drop`) | [x] | **YES** | 364 = baseline; additive de-mock-invisible stage (Rule 1a) — legitimate |
| Independent review PASS | [x] | **THIS DOCUMENT** | PASS |
| Full suite 234 passed / 2 skipped | [x] | not reproduced | Full live run aborted by `pytest-timeout` on an unrelated HuggingFace download (network); not a Stage-13 regression; implementer claim, not load-bearing here |

Honest deviations (all disclosed in the ADR/task doc/§22 and confirmed legitimate): transactional **outbox** instead
of Supabase Realtime (Realtime = heavy Elixir; outbox is the research-§22 endorsed self-hosted equivalent); the real
table is **`stages`** not the aspirational `production_stages`; pgoutput WAL replication for non-PG sinks **deferred →
G-068** (ledgered, low, → Stage 15 / scale stage). G-068 is present and correctly scoped in
`audits/OPEN_GAPS_LEDGER.md:94`. The explainer HTML exists at `research/stage-explainers/STAGE_13/index.html`.

---

## Findings (severity-ranked) — none blocking

### F-1 (LOW) — Stale "Supabase Realtime CDC" / no-restart text in updated KB files
The Stage-13 changelog/section text in KB_05 §97 and the ADR are accurate, but **residual planning-era sentences in
KB files the stage updated still name "Supabase Realtime"**:
- `knowledge-base/KB_04_Data_Schema.md:45-48` — "Stage 13's Supabase Realtime CDC works without a Postgres restart …
  Supabase services … deferred". Stage 13 did **not** use Supabase Realtime; per ADR D4 the running dev container
  *was* restarted to apply `wal_level=logical` (the compose `command:` bakes it in for fresh deploys, so "no restart"
  is only true for a clean `compose up`, not the existing volume).
- `knowledge-base/KB_01_System_Architecture.md:157,160` — the mermaid diagram still routes `PG --> SR -- "CDC"` where
  `SR` is the old Supabase-Realtime node; line 27 repeats the "without a restart" phrasing.
These do not contradict the *authoritative* Stage-13 entries (KB_01:251-256, KB_05:97 are correct and explicit about
the deviation), so this is cosmetic doc-drift, not an overclaim about what the code does. **Recommend** a follow-up
sweep to align the residual sentences. Not close-blocking.

### F-2 (LOW) — research §22 narrative names `production_stages` and "async LISTEN"
`research/initial-research.md:2251,2253` describes the trigger on `production_stages` and an **async** `LISTEN` loop,
whereas the shipped code is on `stages` with a **sync** background thread. The ADR (the authoritative decision
record) and KB_05 §97 both state the correct `stages`/sync-thread design and explicitly flag the deviation, so this
is stale research-narrative text, not a code/claim mismatch. Append-only research convention means this is corrected
by a forward note, not an edit. Not close-blocking.

### F-3 (LOW) — `test_db_insert_drains_into_simworld` can pass on backlog, not only the NOTIFY path
`test_cdc.py:51-63`: after `listener.start()` (which drains any pre-existing unprocessed backlog first), the test
inserts a new incident and asserts `listener.injected >= 1` — it does **not** snapshot `injected` immediately after
`start()` and assert it *increased*. On a DB carrying leftover unprocessed rows, the assertion could be satisfied by
the startup drain alone, so the live NOTIFY→drain path would not be strictly proven by this test. In practice it held
this session (the DB's outbox rows were already `processed_at`-marked, so the startup drain found nothing and the
NOTIFY path genuinely fired — and the direct SQL probe above independently proves the NOTIFY/trigger mechanism).
**Recommend** hardening: `baseline = listener.injected` after `start()`, then assert `injected > baseline`. Low
severity (the durability test + the live SQL probe cover the mechanism); a test-robustness nit, not theatre.

---

## New gaps proposed for the ledger

| Proposed | Description | Severity | Target stage |
|---|---|---|---|
| (cover under existing follow-up) F-1/F-2 | Residual "Supabase Realtime / no-restart / production_stages / async LISTEN" wording in KB_04, KB_01 (mermaid), research §22 — align with the shipped outbox+sync-thread design | low | doc-hygiene / next KB-touching stage |
| (cover under test-hardening) F-3 | Strengthen `test_db_insert_drains_into_simworld` to assert `injected` *increased* post-start (prove the NOTIFY path independently of backlog) | low | Stage 13 follow-up / test-hardening |

These are low-severity doc/test-robustness items; I did **not** mint a new top-level G-ID since the substantive
CDC mechanism is sound and G-068 already captures the one real deferred-capability gap (pgoutput WAL for non-PG
sinks). If the operator prefers a tracked ID, F-1/F-2/F-3 can be ledgered as a single "Stage-13 doc/test hygiene"
row → next KB-touching stage. (Not appended here to avoid over-ledgering cosmetic items.)

---

## Verdict

**PASS.** Stage 13 is honest, mechanism-real CDC: the trigger durably + transactionally captures DB writes and
signals via `pg_notify`; the listener LISTENs + drains (`FOR UPDATE SKIP LOCKED`, ordered, marks processed only on
successful inject) + catches offline-written rows on startup; the converter builds real `InjectRequest`s from the
row diff; degradation is honest (no DB → disabled; no world → row left unprocessed and retried — verified in code,
not asserted from the ADR); shutdown is bounded. The sync-thread rationale is accurate and the SimWorld `inject()`
thread-safety is real. All Stage-13 acceptance criteria are independently confirmed by re-run tests + direct SQL
probes against the live `wal_level=logical` Postgres. The three findings are low-severity documentation drift /
test-robustness nits — none is theatre, none blocks close. The `--no-baseline-drop` hold at 364 is legitimate
(additive de-mock-invisible work, Rule 1a). G-068 (pgoutput WAL for non-PG sinks) is correctly ledgered.
