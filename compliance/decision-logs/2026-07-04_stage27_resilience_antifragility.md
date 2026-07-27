# ADR — Stage 27: Resilience & Anti-Fragility (SPIFFE identity + durable execution + chaos)

- **Date:** 2026-07-04
- **Status:** Accepted
- **Stage:** 27 (`tasks/STAGE_27_resilience_antifragility.md`) — second roadmap-extension build stage (ADR
  `2026-07-02_strategic_audit_and_post_ga_roadmap.md`).
- **Roles:** `security-pqc-engineer` (SPIFFE/mTLS) + `devops-sre` (durable/chaos) + `backend-engineer`.
- **Research:** `research/initial-research.md §38` (SPIRE local deploy; py-spiffe X509Source/mTLS; circuit-breaker
  / saga / idempotency best practice) — appended BEFORE implementing (Hard Rule 11).

## Context

The 2026-07-02 strategic reset committed Stage 27 to making the system "not break under partial failure and get
stronger from chaos", adopting the Kagenti cloud-native pattern (SPIFFE/SPIRE identity, mesh mTLS, framework-neutral
AgentCard) + the durable-execution primitive set, and closing the go-live identity gaps R4/G-4/G-064-network.

## Decisions

1. **Dual-identity model (the Kagenti pattern on our spine):** SPIFFE X509-SVID = TRANSPORT authentication
   (short-lived, SPIRE-rotated, proves who-is-calling on the wire); ML-DSA-65 = EVIDENCE signing (audit rows, cards,
   ADRs — post-quantum). The AgentCard binds both. LIVE: `docker/docker-compose.spire.yml` (SPIRE server+agent,
   join-token attestation, trust domain `ai-agent.local`) + `backend/security/spiffe_identity.py` (X509Source +
   dev-host SVID fetch + `authenticate_peer` gate).
2. **A2A endpoint AUTHENTICATION (R4/G-4 closure):** `a2a/server.py` extracts the peer SPIFFE ID from the verified
   client cert (`X-Forwarded-Client-Cert`, mesh convention), trust-domain/allowlist-checks it, and uses it as the
   authenticated `peer_id` for governance — a foreign-domain peer is REJECTED. Without an mTLS-terminating front the
   Stage-24 confinement fallback applies (anonymous L0, read-only — honestly weaker, named). Istio Ambient mesh mTLS
   = pilot/K8s; the LOCAL load-bearing path is direct SVID-mTLS (proven).
3. **Kagenti/A2A-spec AgentCard export** (`a2a/agent_card_cnstyle.py`): re-shapes our signed card as the LF A2A-spec
   AgentCard JSON + a Kagenti AgentCard-CRD, both carrying the dual identity — channel-fit into CNCF platforms / IBM
   watsonx Orchestrate. Export/interop shaper, not a running mesh deployment (honest scope).
4. **Durable-execution primitives** (`backend/agents/runtime/durable/`): `EffectLedger` (at-most-once claim table,
   DB-durable across workers, replay returns the recorded outcome; extends the Stage-25 `incident_processed`
   pattern), `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN per dependency; OPEN raises `CircuitOpenError` — honest
   degradation, never a fabricated fallback; every transition a signed audit row), `Saga` (per-step idempotency keys
   + reverse compensation; STUCK surfaced, never swallowed). Built in-house (small, our audit/honesty constraints
   are specific) rather than adopting Temporal/Restate (workflow engines — pilot-scale option, ledgered).
5. **G-083 (Stage-26 review tail) PAID:** the disruption monitor's `_raised` de-dup gained EPISODE_QUIET_CHECKS
   expiry — a (kind,subject) episode closes after N consecutive quiet checks so the channel can re-raise a genuinely
   new episode (it previously deafened permanently after the first).

## Measured / verified (every number a live command this session)

- **SPIRE live:** server + agent attested; real SVIDs issued for `a2a-server` + `a2a-client` (1h TTL).
- **SVID-mTLS handshake (6/6 tests):** a valid client SVID authenticates; an anonymous client is REFUSED at the
  handshake (server-side `CERT_REQUIRED`) — the R4/G-4 closure, end-to-end.
- **SVID rotation drill:** cert serial changed (105164974… → 234666654…) with the SAME SPIFFE identity — zero-
  downtime rotating identity.
- **Durable primitives (13/13 tests):** at-most-once + replay-returns (DB-durable across instances); breaker
  OPEN→HALF_OPEN→CLOSED; saga reverse-compensation + no-double-execute-on-replay + STUCK surfacing.
- **AgentCard export + A2A XFCC auth (5/5 tests):** foreign-domain peer rejected; in-domain SVID admitted to
  governance; dual-identity CRD/spec shapes correct.
- **Circuit-breaker chaos drill:** 3 real failures tripped OPEN (1 call blocked without fabrication) → recovery →
  HALF_OPEN probe → CLOSED; 3 signed `circuit.transition` rows; **audit chain verifies (10,070 rows, exit 0)**.

## Consequences

- New package `backend/agents/runtime/durable/` + `backend/security/spiffe_identity.py` +
  `backend/a2a/agent_card_cnstyle.py` + `docker/docker-compose.spire.yml` + `docker/spire/` configs +
  `scripts/spire/{bootstrap-spire,rotate-svid-drill}.{sh,py}` + `scripts/chaos/circuit-breaker-drill.py` + 24 tests.
  New deps: `spiffe==0.3.0`, `spiffe-tls==0.4.0` (Apache-2.0, free — Rule 9). Audit baseline **holds 364**
  (`--no-baseline-drop`: additive real code, no de-mock surface — legacy de-mock is Stage 28).
- KB_13/16/10 updated; risk-register gains 4 Stage-27 rows (A2A-auth R4/G-4, effect double-exec, cascading failure,
  SPIRE scope). G-083 resolved.
- Deferred honestly: Istio Ambient mesh + production node attestation (pilot/K8s); Temporal/Restate durable-workflow
  engine (ledgered option); wiring the durable primitives into every existing effect call-site (the primitives +
  the pattern are proven; blanket retrofit is incremental — the actuator/order paths are the priority next).

## References
- research §38 · `research/stage-explainers/STAGE_27/index.html` · `backend/security/spiffe_identity.py` ·
  `backend/agents/runtime/durable/*` · `backend/a2a/agent_card_cnstyle.py` ·
  spiffe.io (spire101/deploying) · github.com/HewlettPackard/py-spiffe · temporal.io saga · Nygard *Release It!* ·
  ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-11T18:08:23+00:00 -->
<!-- signature: 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 -->
