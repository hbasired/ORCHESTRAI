# Independent review — Stage 3 (WebSocket incident broker + Redis pub/sub fan-out)

**Date**: 2026-06-12
**Reviewer**: `task-auditor` (fresh, independent agent — did NOT implement Stage 3, Stage 3's close, or the Stage-6 broker extension).
**Task doc**: `tasks/STAGE_03_ws_broker.md` (status: done, closed 2026-05-31; baseline rewritten 436 → 411 at close).

> **This 2026-06-12 run COMPLETES and SUPERSEDES the partial 2026-05-31 attempt** (which hit a subprocess
> limit after 18 tool calls and recorded only an interim mechanical re-verification). The owed full
> independent re-audit — **gap G-001** — is satisfied by this report. This file replaces the partial one.

**VERDICT: PASS-WITH-GAPS** — the broker is real, the tests are honest, the close was legitimate (no gate
bypass; strict baseline decrease 436 → 411), and every remaining gap is already ledgered with a target stage.
The gaps below are observations and already-tracked carry-forwards, none of which invalidate the close.

---

## 1. Scope & independence

- Scope: Stage 3 acceptance criteria in `tasks/STAGE_03_ws_broker.md`, judged against **current** code —
  including the 2026-06-12 Stage-6 extension to `backend/services/ws_broker.py` (`build_slice_envelope` +
  slice pass-through in `handle_raw`). I explicitly verified the **legacy incident path still works** under
  the extension.
- Independence: this session built nothing in Stage 3 or Stage 6; read-only except this one file.
- Inputs read: task doc; `audits/STAGE_03_audit.md` (mechanical, total 411 vs baseline 436 at close);
  the partial 2026-05-31 review; `backend/services/ws_broker.py`; `backend/simulation/persistence.py`;
  `backend/main.py` (lifespan + `/ws`); `frontend-nextjs/src/lib/api.ts`; the three Stage 3 entries in
  `knowledge-base/KB_TASK_LOG.md`; KB_04 envelope spec; `audits/OPEN_GAPS_LEDGER.md` rows G-001…G-004,
  G-021, G-044; test sources for all three suites run.

## 2. What I ran (real output)

**Command** (per instruction; `backend/venv` Python 3.x on the Windows dev host):

```
cd backend && python -m pytest tests/test_ws_broker.py tests/test_ws_broker_redis_integration.py tests/test_slice_events.py -q
```

**Real result**: **`12 passed, 1 skipped, 1 warning in 1.84s`**

- The 1 skip is `tests/test_ws_broker_redis_integration.py::test_live_redis_publish_fans_out_to_ws_client`
  — `SKIPPED [1] tests\test_ws_broker_redis_integration.py:51: no Redis reachable at redis://localhost:6379/0`.
  The self-skip behaved exactly as designed (test file lines 50–51); **no Redis was running on this host
  during this audit, so the live-Redis leg did NOT execute this run** (see Finding F-2).
- The only warning is the pre-existing pytest-asyncio `event_loop` fixture deprecation from
  `backend/tests/conftest.py:13` — unrelated to Stage 3.

**Exclusion (honest)**: `tests/test_websocket_smoke.py` was deliberately NOT run. It hangs for
**pre-existing** reasons verified via git-stash experiment on the pre-Stage-6 tree and ledgered as **G-044**
(`audits/OPEN_GAPS_LEDGER.md:71`, target Stage 11). Its exclusion is documented debt, not a dodge.

**Mechanical audit** (read-only, no `--baseline`): `bash scripts/audit.sh` →

```
TOTAL 396 ... Baseline (from .audit-baseline): 402
OK: count decreased from 402 to 396.
```

`math_random_ts = 84` — identical to the count recorded at Stage 3 close; all 84 hits live in six `page.tsx`
files (pre-existing, ledgered G-021/G-032), **zero in `src/lib/api.ts`**.

## 3. Findings (file:line evidence)

### Per-criterion verification

| # | Criterion (task doc) | Independently confirmed? | Evidence |
|---|---|---|---|
| 1 | `ws_broker.py` exports `ConnectionManager` + `SimulatorEventBroker` subscribed to `pubsub:simulator:events` | **YES** | `backend/services/ws_broker.py:27` (channel constant), `:75`, `:131`; matches the publisher in `backend/simulation/persistence.py:43-45` |
| 2 | `build_incident_envelope` = canonical KB_04 envelope `{v,type,ts,incident_id,payload}` | **YES** | `ws_broker.py:41-53` vs `knowledge-base/KB_04_Data_Schema.md:98-110`; exact key set asserted in `tests/test_ws_broker.py:60` — passed |
| 3 | Broadcast delivers + prunes dead/slow clients, per-send timeout, never raises per-client | **YES** | `ws_broker.py:92-113` (`asyncio.wait_for` per send, `DEFAULT_SEND_TIMEOUT=2.0` at `:29`, dead-list pruning); tests `test_broadcast_delivers_and_prunes_dead_clients`, `test_broadcast_prunes_slow_client_on_timeout` — passed |
| 4 | Resilient: malformed-skip, Redis reconnect/backoff, clean `stop()` | **YES (code + unit), backoff not fault-injected** | malformed-skip `ws_broker.py:166-183` + `tests/test_ws_broker.py:113-120` and `tests/test_slice_events.py:76-83`; reconnect loop `ws_broker.py:187-213` (exception → `sleep(self._backoff)` → re-subscribe); clean stop `:220-233`, exercised by `test_broker_run_loop_fans_message_to_client`. Chaos test of the backoff path is **G-004** (target Stage 12.5) — already ledgered, unchanged |
| 5 | `main.py` wires SimWorld→Redis (sync→async bridge), starts/stops broker, `/ws` registers clients | **YES** | `backend/main.py:170-197` (`run_coroutine_threadsafe` bridge at `:183-186`, broker start `:196-197`), shutdown `:222-225`, `/ws` register `:382`, unregister in `finally` `:429` |
| 6 | Audit no regression (≤ 436); close target < 436 | **YES, exceeded** | Close: 436 → **411** (`audits/STAGE_03_audit.md:7`, strict decrease, no `--no-baseline-drop`). Today: 396 vs baseline 402 — still trending down |
| 7 | Live Redis path verified, fan-out latency 11.6 ms | **PARTIAL — not reproduced this run** | Test is real (`tests/test_ws_broker_redis_integration.py:75-94`: real `append_incident` → real PUBLISH → real SUBSCRIBE → assert envelope + latency, prints measured latency). It **self-skipped today** (no Redis on host). See F-2 |
| 8 | (close gate) Full-app HTTP→WS compose e2e | **NOT DONE — honestly ledgered** | **G-002** (`OPEN_GAPS_LEDGER.md:28`, OPEN). Carried forward explicitly at close (`KB_TASK_LOG.md:388`), not silently dropped |
| 9 | (close gate) Frontend de-mock to drop baseline < 436 | **YES** | See F-1. G-003 marked RESOLVED in ledger (`OPEN_GAPS_LEDGER.md:29`) — confirmed real |

### F-1 — Frontend Math.random fallbacks really gone in the wired paths: CONFIRMED

- `frontend-nextjs/src/lib/api.ts` contains **zero** `Math.random` (full-file read + repo grep: all 84
  remaining `math_random_ts` hits are in `app/*/page.tsx`, pre-existing).
- The fabricated `getMockState()` is gone; the unreachable-backend path now returns an honest all-zeros
  `emptyState()` (`api.ts:133-135`, `:268-290`) — no fabricated data.
- `connectWebSocket` targets the real `/ws` (`api.ts:246`) and types the canonical KB_04 `IncidentEnvelope`
  (`api.ts:73-87`). The 436 → 411 drop claimed at close is consistent with `math_random_ts` 109 → 84 in the
  close-time audit report.
- **Caveat (known, ledgered)**: `connectWebSocket` still has no UI callers — the close entry itself admits
  this (`KB_TASK_LOG.md:383`); rendering the live stream is **G-021** (operator dashboard, Stage 12.5).

### F-2 — The 11.6 ms figure is not reproducible from any committed artifact (finding, not a crime)

The number appears only in prose (`tasks/STAGE_03_ws_broker.md:45`, `KB_TASK_LOG.md:302`, the prior partial
review, research docs). There is no committed machine artifact (metrics JSON, CI log, captured pytest
output). The test that produces it is genuine and prints the measured latency when Redis is up
(`test_ws_broker_redis_integration.py:93-94`), and its in-test assertion is a loose `< 1000 ms` sanity bound
— so 11.6 ms is a **single-shot measurement on one dev host, not a p95**, and could not be re-measured this
run (Redis down, test self-skipped). The KB_10 budget claim (p95 ≤ 250 ms) therefore rests on plausibility
plus one recorded run. Recommendation (no ledger row from me, per scope): capture the printed latency into a
committed artifact when G-002's compose e2e runs.

### F-3 — Stage-6 extension does not regress the Stage 3 contract: CONFIRMED

- `handle_raw` checks for already-enveloped slice events first (`ws_broker.py:178-179`: `v == 1` and `type`
  in `SLICE_EVENT_TYPES = ("prediction","diagnosis","intervention","ab_report")`, `:31`) and passes them
  through as-is; **raw incident dicts still take the legacy wrap path** (`:180-185`).
- Independently verified by `tests/test_slice_events.py::test_legacy_incident_path_still_wraps` (asserts the
  wrapped message equals `build_incident_envelope(raw)`, `:62-72`) — **passed** in my run, alongside the six
  original Stage 3 unit tests, which all still pass unmodified.
- Minor observation (Stage 6 documentation drift, not Stage 3): KB_04's outbound `type` enum
  (`KB_04_Data_Schema.md:105`) lists `state_snapshot|delta|incident|decision|explanation` and does not yet
  include the four slice types `build_slice_envelope` emits. The envelope *shape* is KB_04-conformant; the
  enum is stale (KB_04 `last-updated: 2026-05-11-stage1`). Belongs to Stage 6's KB updates, not this verdict.
- Edge note: a hypothetical pre-enveloped `type:"incident"` message would be double-wrapped by `handle_raw`
  (it is not in `SLICE_EVENT_TYPES`), but no publisher emits pre-enveloped incidents —
  `persistence.append_incident` publishes raw payload dicts (`persistence.py:43-45`). Theoretical only.

### F-4 — Real Redis subscribe with reconnect/backoff: REAL, with one design note

The subscribe loop is a genuine `redis.asyncio` pub/sub `SUBSCRIBE` + `listen()` (`ws_broker.py:191-200`),
not a polling fake. On any exception it logs, sleeps `reconnect_backoff` (default 2.0 s), and re-subscribes;
`CancelledError` exits cleanly; the pubsub handle is closed in `finally` via the version-tolerant `_aclose`
(`:116-128`). Design note: `_ensure_redis` (`:152-158`) never recreates the client object after a failure —
recovery relies on redis-py's connection-pool reconnection, which is standard behavior but is exactly the
untested path already ledgered as **G-004** (fixed backoff, no jitter/cap either). Not a Stage 3 blocker.

## 4. Theatrical scan

- `backend/services/ws_broker.py`: **clean** — no `random.uniform|random.choice|Math.random|
  generateMockState|_get_demo_*|RESPONSES = {|MODELS = [`. Emits real envelopes for real incidents;
  returns `None`/0 when there is nothing to send.
- `backend/tests/test_ws_broker.py`, `test_slice_events.py`, `test_ws_broker_redis_integration.py`: tests
  assert real behavior (exact envelope key-set, delivery counts, pruning, real PUBLISH→SUBSCRIBE round-trip).
  No no-ops, no always-pass asserts. The integration test's skip is environment-gated, not a fake pass.
- `backend/main.py` wiring: real Redis client from `settings.redis_url`, real thread→loop bridge; the
  degraded path (`redis_client = None` on init failure, `:172-176`) logs honestly and downgrades — it does
  not fabricate.
- `frontend-nextjs/src/lib/api.ts`: wired paths clean (F-1). **Residual**: `getMockModelMetrics()`
  (`api.ts:292-323`) and `getMockEmbodiedComparison()` (`api.ts:325-342`) return hardcoded fabricated
  metrics in the catch paths of `getModelMetrics`/`getEmbodiedComparison`. These pre-date Stage 3, were not
  part of its criteria, and slip past `scripts/audit.sh` patterns (no `const MODELS =` / `Math.random`
  match) — i.e., they are invisible to the mechanical count. Hard-rule-1-spirit debt for a frontend cleanup
  stage; flagged here for visibility, not ledgered by me (out of my scope mandate).
- Gate bypass check: none. No `--no-baseline-drop` on this feature stage; baseline strictly decreased at
  close (436 → 411) via real de-mocking; deferred criteria were ledgered (G-002, G-021), not checked off.

## 5. VERDICT

**PASS-WITH-GAPS.**

The Stage 3 deliverable — Redis pub/sub → WebSocket incident broker with canonical KB_04 envelopes, pruning
broadcast, resilient subscriber, and real `main.py` wiring — is genuinely implemented, honestly tested
(12 passed this run), and survived the Stage-6 extension with the legacy path intact. The close was
legitimate: strict baseline decrease through real mock removal, deferred items ledgered transparently.

Gaps (all pre-tracked or observational; none block the already-completed close):
1. **G-002** (OPEN) — full-app HTTP→WS compose e2e still owed; verify on first `docker compose up backend`.
2. **G-004** (OPEN) — reconnect/backoff path not fault-injection tested; fixed backoff, client never
   recreated (Stage 12.5).
3. **G-021** (OPEN) — `connectWebSocket` has no UI consumers yet (operator dashboard).
4. **F-2** — the 11.6 ms latency claim has no committed reproducible artifact and is single-shot, not p95;
   could not be re-measured this run (Redis down, integration test self-skipped as designed).
5. **F-3 note** — KB_04 `type` enum not yet updated for Stage-6 slice types (Stage 6 doc debt).
6. **Theatrical-scan residual** — `getMock*` hardcoded fallbacks remain in `api.ts` catch paths, invisible
   to `audit.sh` patterns (pre-existing; frontend cleanup stage).

**G-001 is retired by this report.** Per my read-only contract I fixed nothing and added no ledger rows;
the implementer/governance session should mark G-001 RESOLVED referencing this file.
