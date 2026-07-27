# ADR — Stage 11 (increment 5, CLOSE): full-infra live verification + two production fixes

**Date**: 2026-06-15
**Status**: Accepted (Stage 11 final increment — closes the stage; follows increment 4
`2026-06-14_stage11_runtime_complete.md`)
**Author personas**: `backend-engineer` (primary) + `devops-sre` + `agentic-governance-engineer`
**Relates**: pays the **R-IND belt-and-suspenders** caveat on G-049/G-050 (a run-capable session re-runs the
commands the shell-denied reviewer agents could not); resolves two newly-found production defects G-053/G-054.
Follows Hard Rule 1a (no theatre — these are correctness fixes) + 11b (finish completely; ledger-and-fix honestly).

---

## Context

Stage 11's increments 1–4 built + self-verified the LangGraph self-healing runtime. The independent reviews for the
depth-hardening pass and the runtime were rigorous **but static** — the reviewer agents' Bash/pytest execution was
denied (ledger G-049/G-050 R-IND caveat), and the durable PostgresSaver had been verified against an *ad-hoc* clean
Postgres, not the project's real Docker stack. The operator directed: stand up the **real Docker infra** (use the
Docker Postgres, not the local one; bring up Neo4j), and **re-run every verification that the shell-denied agents
could not**, rectifying whatever breaks. This increment is that run, plus the two real defects it surfaced.

## Decisions

**D1 — Run the whole stack against the REAL Docker infra (not the local shadow).** A **local Postgres** on the host
shadows the Docker Postgres on `5432`, so the Docker container was re-published to host port **5544** (volume
`docker_postgres-data` preserved; creds `aiagent`/`devpass2026`/`manufacturing`). Neo4j brought up
(`neo4j:5.15-community`, `7687`/`7474`, volume `docker_neo4j-data`). Redis on `6379`. **Verified, not asserted:**
- Alembic `0001`→`0002` applied to the Docker PG; `alembic_version = 0002_langgraph_checkpoints`; the four
  `checkpoint*` tables exist.
- `agents/runtime/checkpointer.py` returns backend `postgres` against `…@localhost:5544`; a graph run persists and a
  fresh saver reloads it; `test_postgres_checkpointer_persists_when_available` now **runs** (not skipped) and passes.
- The app's `knowledge_graph` Neo4j client genuinely **connects** (`bolt://localhost:7687`, "Neo4J connected",
  "Neo4J schema initialized", `_driver` live) — Neo4j is exercised, not degraded around.
- **Full backend suite vs the live stack: 186 passed, 1 skipped, EXIT 0** (was hanging before). `scripts/audit.sh`
  **holds at 364**.

**D2 — Fix G-053: `SimulatorEventBroker` shutdown deadlock (real production defect).** The live-Redis integration
test (`test_ws_broker_redis_integration.py`) — which only *runs* when Redis is reachable, so it had always *skipped*
— **hung** in `broker.stop()` at `await self._task`. Root cause: cancelling the task **mid-`pubsub.listen()` socket
read** deadlocks redis-py's pubsub teardown on the Windows Proactor loop (pytest-asyncio's loop exposes it; plain
`asyncio.run()` happened to mask it). A broker that can deadlock on shutdown is a genuine defect. Fix in
`services/ws_broker.py`: drive the subscribe loop with **bounded `pubsub.get_message(timeout=1.0)` polling** so it
re-checks `_stopped` and exits *between* reads (never cancelled mid-read), and make `stop()` **time-boxed** (await
the self-exiting task with a bounded `wait_for`; cancel only as a last resort, also bounded) so shutdown can never
hang. `test_ws_broker.py`'s `FakePubSub` updated from the old `listen()` generator to the `get_message()` API to
match. Result: all 7 ws-broker tests pass incl. the live e2e (real publish→fan-out **11.1 ms**).

**D3 — Fix G-054: `ExternalAPIClient` background-task leak on shutdown.** With the G-044 lifespan fix now running the
app lifespan in client tests, 52 `Task was destroyed but it is pending` warnings appeared for
`_weather_update_loop`/`_carbon_update_loop`. Two bugs: (a) `main.py`'s lifespan shutdown **never called**
`api_client.close()`; (b) `ExternalAPIClient.close()` cancelled the tasks but **didn't await** them, so cancellation
never completed before loop teardown. Fix: lifespan now `await api_client.close()` on shutdown; `close()` now awaits
each cancelled task (suppressing `CancelledError`). Result: pending-task warnings **52 → 0**; suite still 186/1.

**D4 — Pay the R-IND caveat on G-049/G-050.** The depth-hardening + CTO #2 independent reviews' static-execution
caveat is now discharged: a run-capable session has re-run the full pytest suite, `audit.sh`, and the PG-durability
test against the real Docker stack, reproducing the headline results. G-049/G-050 R-IND noted RESOLVED.

## Why
- "Use the Docker Postgres / bring up Neo4j / re-run what failed" is only honest if actually executed against the
  real services — which surfaced two defects a degraded/skipped path had hidden (Rule 11b: shallow/skipped work
  hides gaps).
- Both fixes are correctness fixes (no theatre added/removed), so the audit baseline correctly **holds at 364**.

## Consequences
- Modified: `services/ws_broker.py` (polling loop + bounded stop), `tests/test_ws_broker.py` (FakePubSub→get_message),
  `main.py` (lifespan closes api_client), `pipeline/api_integrations.py` (`close()` awaits cancelled tasks). New: this
  ADR; KB_TASK_LOG close entry; ledger rows G-053/G-054 (RESOLVED), G-049/G-050 R-IND discharged. `pytest-timeout`
  added as a dev/test dep (used to pinpoint the hang).
- Verified end-to-end vs the real Docker stack (PG@5544 + Neo4j@7687 + Redis@6379): **186 passed / 1 skipped**,
  runtime 7/7 incl. PG durability, audit **364**, zero pending-task warnings.
- Audit holds 364 (`--no-baseline-drop`; correctness fixes, no grep-counted theatre touched — Rule 1a).

## Honest residual
- `langgraph` 0.2.60 ↔ `langgraph-checkpoint-postgres` 2.0.25 emit a cosmetic version-skew `DeprecationWarning`;
  the durable path works (tests pass). Upgrading langgraph reintroduces the `Reviver(allowed_objects=...)` break
  resolved in increment 4 — left pinned; ledgered as low-priority G-055.
- The legacy `api_integrations.py` weather/carbon **mock** helpers (`random.*`) remain part of the 364 baseline,
  scheduled for de-mock on their own stage — out of Stage-11 scope.
- G-051 (Stage-6 no-op VERIFY gate) remains OPEN, routed to Stage 7/17 (the runtime already pays it with a binding
  PlantState — `agents/runtime/nodes.py`).

## References
- `services/ws_broker.py` · `pipeline/api_integrations.py` · `main.py` · `tests/test_ws_broker.py` ·
  `tests/test_ws_broker_redis_integration.py` · `tests/agents/runtime/test_canned_decision.py`.
- Increment-4 ADR `2026-06-14_stage11_runtime_complete.md`. Ledger G-049/G-050/G-053/G-054/G-055. KB_01/06/25.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:30+00:00 -->
<!-- signature: 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 -->
