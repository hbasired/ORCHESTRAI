# Stage 27 — Independent Review (Resilience & Anti-Fragility)

- **Auditor:** independent `task-auditor` agent (DID NOT implement Stage 27).
- **Date:** 2026-07-11
- **Scope:** SPIFFE/SPIRE workload identity + SVID-mTLS A2A authentication + durable-execution primitives + chaos drills + G-083 tail.
- **Status:** IN PROGRESS — written incrementally (prior reviewers hit session limits).

## Verdict: **PASS** (dynamic verification reproduced everything; no theatre found)

> Different agent than the implementer. Static read (below) found the durable primitives honest; the dynamic pass
> (this section) reproduced every headline number live — 24/24 resilience tests, a REAL SPIRE-issued SVID driving a
> genuine mTLS handshake, the circuit-breaker chaos drill with signed audit rows, and a full audit-chain verify
> (10,076 rows, all 9,997 post-cutover ML-DSA-65 signatures) exit 0. One operational wrinkle (the SPIRE agent had
> crashed on SVID-TTL expiry, so the gated test *honestly skipped* until I re-bootstrapped it) is expected
> honest-degradation, not a code gap — enumerated below as a non-blocking operational note.

---

## Static read findings (line-by-line)

### Durable primitives (backend/agents/runtime/durable/)
- `circuit_breaker.py`: OPEN state RAISES `CircuitOpenError` (never a fabricated fallback) — honesty hunt (a) SATISFIED on static read. Transitions queued and audited outside the lock (documented reason: in-lock DB append serializes breaker calls). Monotonic clock. LOOKS HONEST.
- `idempotency.py` (EffectLedger): real PG table `effect_ledger` (key PK, ON CONFLICT DO NOTHING at-most-once claim); honest in-process dict fallback WITHOUT a DB, with an explicit disclaimer that cross-process at-most-once REQUIRES the DB. Honesty hunt (b) SATISFIED on static read.
- `saga.py`: reverse-order compensation, per-step idempotency keys, STUCK surfaced via `SagaStuckError` + signed audit row (never swallowed). LOOKS HONEST.
- `__init__.py`: records the task-doc deviation (`backend/runtime/durable/` -> `backend/agents/runtime/durable/`) honestly.
- `spiffe_identity.py`: every acquisition path raises `SpiffeUnavailable` when SPIRE is unreachable — NEVER a faked
  identity. `authenticate_peer()` raises `PermissionError` on (i) no SPIFFE ID in the cert, (ii) SPIFFE ID outside the
  trust domain, (iii) not in the allowlist. Honesty hunt (c) SATISFIED on static read.
- `a2a/server.py` (lines 83-121): the R4/G-4 XFCC path — extracts the peer SPIFFE ID from the mesh's
  `X-Forwarded-Client-Cert` header, calls `authenticate_peer`, and on `PermissionError` RETURNS a JSON-RPC auth error
  (`peer authentication failed`) + a failed audit row. Absent XFCC, `peer_id = ... or "anonymous"` with the fallback
  named "honestly weaker" in-comment (lines 87-88, 108-109) — NOT hidden. Honesty hunt (c)/(d) SATISFIED on static read.

---

## Dynamic verification (this session, live infra) — the load-bearing pass

Environment: `DATABASE_URL=postgresql://aiagent:...@localhost:5544/manufacturing`; Docker up (ai-agent-postgres,
neo4j, redis, mqtt, spire-server). `MSYS_NO_PATHCONV=1` guard set.

### 1. Resilience test suite — 24/24 pass (23 + 1 gated)
`python -m pytest tests/resilience/ -q` → **initially 23 passed, 1 skipped**. The skip was the SPIRE-gated
`test_real_svid_mtls_authenticates_a_valid_client_and_refuses_an_anonymous_one`, reason `SPIRE agent not running
(bootstrap-spire.sh)`. **Root cause (investigated, not assumed):** `docker ps -a` showed `spire-agent Exited (1)` ~44
min prior; `docker logs spire-agent` showed the agent SVID expired and re-attestation was `PermissionDenied` (join-token
already consumed — the 1h agent-SVID TTL lapsed). This is the test's HONEST skip-gate working: it declines to run rather
than fake a handshake. I re-ran `scripts/spire/bootstrap-spire.sh` (server was still up → fresh agent + re-issued
`a2a-server`/`a2a-client` entries), polled until SVIDs issued, and **re-ran the gated test: PASSED (1 passed in 5.85s)**.
So with the agent up, **24/24 resilience tests pass**. The gated test (read in full) drives a genuine `ssl` mTLS handshake
over a real socket with REAL SVIDs, requires a client cert server-side (`CERT_REQUIRED`), and asserts the server REJECTS
an anonymous client and identifies no peer — this is not faked.

### 2. SVID identity path is REAL (not a fabricated cert)
- `fetch_svid_via_docker()` → `spiffe://ai-agent.local/a2a-server  True  790` (SPIFFE ID + nonzero cert file).
- Loaded with `cryptography.x509`: `serial 140770807490021535215238701390485213094  issuer O=SPIFFE,C=US` — a
  genuine SPIRE-issued X.509-SVID (SPIFFE CA), not a hand-rolled/self-signed placeholder.

### 3. Circuit-breaker chaos drill + signed audit rows + chain integrity
- `scripts/chaos/circuit-breaker-drill.py` → **`DRILL PASS`**: "3 real failures tripped the breaker OPEN; 1 call
  blocked WITHOUT fabrication" → "recovered → HALF_OPEN probe succeeded → CLOSED (self-healed)".
- `SELECT count(*) FROM audit_chain WHERE action='circuit.transition'` → **9** (nonzero; real signed transition rows).
- Audit chain verify: `--quick` → `Audit chain OK ... all 100 post-cutover signatures verify [quick]` exit 0. **FULL**
  verify (ran to completion, 10,076 rows) → **`Audit chain OK (10076 rows; hash chain intact; all 9997 post-cutover
  signatures verify)` exit 0** — the drill's new rows are hash-linked and ML-DSA-65-signed like every other.
  (Note: the verifier lives at `scripts/verify-audit-chain.py`, not `backend/scripts/...` as the task prompt wrote.)

### 4. A2A authentication closure (R4/G-4) — REAL rejection, honest fallback
Read `a2a/server.py` around the XFCC handling (grep-confirmed `X-Forwarded-Client-Cert` / `authenticate_peer` /
`authenticated_sid`). (1) A foreign-trust-domain peer cert → `authenticate_peer` raises `PermissionError` → the handler
returns a JSON-RPC `peer authentication failed` error + failed audit row (verified live by
`test_foreign_trust_domain_peer_is_rejected` and `test_authenticate_rejects_foreign_trust_domain`, both PASS). (2) The
no-cert fallback to anonymous L0 confinement is NAMED in code ("honestly weaker, and named as such") — not hidden;
verified by `test_no_xfcc_falls_back_to_anonymous_confinement` (PASS).

### 5. Mechanical audit gate
`scripts/audit.sh` → **TOTAL 364, flat at baseline 364**. Correctly waived `--no-baseline-drop` (additive
resilience/identity code; zero `random.*`/mock/`RESPONSES={}`/`MODELS=[]` introduced; the legacy de-mock is Stage 28).
`STAGE_27_audit.md §6` gaps are both resolved-with-justification (the actuator-heuristic hit is the same known
FALSE-POSITIVE class — `.pytest_cache` + untouched G-082 legacy demo agents; Stage 27 added no actuator emitter).

### Honesty checks (all four SATISFIED, dynamically)
- **(a) CircuitBreaker never fabricates a fallback** — `call()` on OPEN raises `CircuitOpenError` *without attempting
  the call* (verified in code + the drill's "1 call blocked WITHOUT fabrication").
- **(b) EffectLedger is DB-durable + honest in-process fallback** — real `effect_ledger` PG table, `ON CONFLICT DO
  NOTHING` at-most-once claim; no-DB path degrades to an in-process dict WITH an explicit disclaimer that cross-process
  at-most-once REQUIRES the DB. `test_effect_ledger_is_durable_across_instances` PASS (DB present this run).
- **(c) authenticate_peer really rejects foreign domains / missing IDs** — confirmed in code and by 4 passing tests.
- **(d) Deferrals are NAMED in the ADR** (`2026-07-04_stage27_resilience_antifragility.md`), not silently missing:
  Istio Ambient mesh + production node attestation = pilot/K8s (Decision 2 + Consequences); Temporal/Restate durable
  engine = ledgered option (Decision 4); durable primitives not yet retrofitted into every effect call-site
  (Consequences: "blanket retrofit is incremental"); AgentCard export is an "export/interop shaper, not a running mesh
  deployment (honest scope)" (Decision 3). All present.

## Gaps enumerated

**No must-fix-before-close gaps.** Everything the ADR/task-doc claims reproduced live with no theatre.

Non-blocking operational notes (ledgerable, not close-blockers):
1. **SPIRE agent SVID TTL is 1h** (join-token attestation) → the agent crashes and the gated mTLS test *honestly
   skips* once the TTL lapses without a running renewer. This is correct honest-degradation, but it means CI/audit
   re-runs need `bootstrap-spire.sh` re-run first (or a longer TTL / SVID renewer) to keep the gated leg live. Worth a
   one-line note in the runbook; the ADR already scopes continuous rotation (X509Source) to the containerised path.
2. **Durable primitives are proven but not yet wired into every existing effect call-site** — already disclosed in the
   ADR Consequences as incremental follow-up; ledgered (the pattern + primitives are load-bearing and tested; the
   blanket retrofit is a later increment). Not a Stage-27 gap.

## Bottom line
**PASS.** Independent (different-agent) dynamic verification reproduced the SPIRE-issued real-SVID mTLS handshake, the
circuit-breaker chaos drill with signed `circuit.transition` audit rows, a full 10,076-row ML-DSA-65 chain verify
(exit 0), the A2A foreign-domain rejection, and the flat-364 audit gate. The durable primitives raise/compensate/
surface rather than fabricate; the identity layer raises `SpiffeUnavailable` rather than fake a cert; all four deferrals
are named in the ADR. No theatre. Clear to close.
