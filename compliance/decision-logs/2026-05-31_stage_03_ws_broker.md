# ADR — Stage 3 WebSocket incident broker (2026-05-31)

**Status**: accepted (Stage 3 in-progress; close gates documented)
**Stage**: 3 — WebSocket broker: Redis pub/sub fan-out of simulator incidents
**Author**: backend-engineer persona (Claude session, 2026-05-31)
**Related task doc**: [`tasks/STAGE_03_ws_broker.md`](../../tasks/STAGE_03_ws_broker.md)
**KB updates**: KB_01 (architecture), KB_07 (WS incident delivery contract), KB_TASK_LOG (Stage 3 entry)

Design decisions for the Stage 3 incident broker that fans simulator events out to WebSocket clients.

---

## D1 — Redis pub/sub decoupling (publisher ≠ subscriber)

**Context.** Stage 2 left `SimWorld` publishing each incident to Redis `pubsub:simulator:events` via
`persistence.append_incident`. The WS fan-out could read incidents directly from the simulator callback, or
via the Redis channel.

**Decision.** Fan out via a `SimulatorEventBroker` that SUBSCRIBES to `pubsub:simulator:events`
(`backend/services/ws_broker.py`). The simulator publishes; the broker subscribes.

**Why.** Decoupling makes the fan-out multi-worker safe: under multiple uvicorn workers, each worker
subscribes and serves only its own connected clients, and the simulator need not know who is listening. It
also matches the Stage 2 hand-off design and keeps the simulator path non-blocking.

**Consequences.** A small in-process Redis round-trip even for a single worker (intentional). The broker holds
its own dedicated connection (pub/sub SUBSCRIBE blocks; must not share the publish client).

## D2 — Canonical KB_04 envelope, not the legacy ad-hoc shape

**Context.** Existing `/ws` state messages use `{type, timestamp, data}`. KB_04 defines the canonical outbound
envelope `{v, type, ts, incident_id, payload}` and names it the arbiter.

**Decision.** `build_incident_envelope()` emits the canonical KB_04 `incident` envelope. The legacy
state_update/decision messages are left unchanged (out of Stage 3 scope).

**Why.** KB_04 is the single source of truth for shapes; the operator dashboard (PRD v2.1 §v2.1.4) and Stage
11+ consumers expect it.

## D3 — Sync→async bridge for `on_incident`

**Context.** `SimWorld.on_incident` is invoked from the SimPy worker thread (sync); `append_incident` is async.

**Decision.** `main.py:lifespan()` captures the running loop and bridges via
`asyncio.run_coroutine_threadsafe(append_incident(payload, redis_client=...), main_loop)`.

**Why.** It is the correct, standard mechanism to schedule a coroutine on the event loop from another thread.

**Consequences.** Publish failures are logged (not raised) so a Redis hiccup never crashes the simulator.

## D4 — Resilience: prune dead clients; reconnect; skip malformed

**Decision.** `ConnectionManager.broadcast` sends with a per-client timeout and prunes any client that errors
or stalls (a slow client cannot block the loop). `SimulatorEventBroker` reconnects with backoff on Redis
errors and skips malformed/idless messages without crashing.

**Why.** Production-grade fan-out must tolerate flaky clients and transient Redis outages.

## D5 — Stage 3 stays IN PROGRESS (no `--no-baseline-drop` abuse)

**Context.** CLAUDE.md rule 1 requires the audit count to strictly decrease at a feature-stage close.
`--no-baseline-drop` is reserved for CTO/protocol/governance-only stages. The broker is additive backend code
that removes no existing fakery, so the count holds at 436.

**Decision.** Do **not** close Stage 3 yet. Closure requires (1) wiring the frontend Disruption Console to the
real `/ws incident` stream + `/inject` (removing `Math.random()` mocks → baseline < 436) and (2) a full-app
compose e2e (inject→client p95 ≤ 250 ms). Both need the compose stack / a frontend pass not runnable on this
dev box (Docker daemon down; no local Redis).

**Why.** Honesty + the audit discipline: a feature stage must reduce the count to close; faking a close or
abusing the flag would violate the project's core rule.

**Consequences.** The broker is shipped + unit-verified (34 tests, audit 436) and ready; the two close gates
are tracked in the Stage 3 task doc and KB_TASK_LOG.

## Verification (2026-05-31)
- `pytest tests/test_ws_broker.py tests/test_inject_validation.py tests/test_sim_world_smoke.py` → 34 passed.
- `py_compile` main.py + ws_broker.py → OK. `scripts/audit.sh` → TOTAL 436 (no regression).
- Full subscribe→broadcast→client path verified via fake-pubsub run-loop test (Docker/Redis unavailable here).

## Risk register references
- Stage 3 introduces no new high-risk surface; the actuator/safety path (Stage 17) is unaffected.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:03+00:00 -->
<!-- signature: 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 -->
