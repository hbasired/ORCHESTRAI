---
status: done
stage: 27
slug: resilience_antifragility
created: 2026-07-02
---

# Stage 27 — Resilience & Anti-Fragility (workload identity + durable execution + chaos hardening)

> Make the system **not break under partial failure and get stronger from chaos** — the operator's "resilient systems
> that don't break + scale + solid + deployable" ask (2026-07-02 strategic reset). Adopts the **Kagenti/kagent** cloud-
> native pattern (SPIFFE/SPIRE rotating workload identity, mesh mTLS, MCP-Gateway, framework-neutral AgentCard) + the
> **durable-execution** pattern set (idempotent compensable effects, circuit breakers, saga, event-sourcing). Sourced in
> `research/initial-research.md §35.1 / §35.3` (kagenti.github.io; next.redhat.com 2026-03-05 zero-trust-agents;
> temporal.io; Microsoft Durable Task for AI agents 2026-04; LangGraph persistence). Free/local: SPIRE + Istio run in
> Docker; no paid infra (Rule 9). Also closes the go-live identity gaps R4 / G-4 / G-064-network.

## Pre-requisites
- Stage 26 closed (or coordinated). Read KB_24 / KB_25 / `audits/OPEN_GAPS_LEDGER.md` (Rule 10).
- Research-first (Rule 11): append a Stage-27 SOTA section BEFORE implementing (SPIFFE/SPIRE deploy, Istio Ambient mTLS,
  saga/compensation for agent effects, circuit-breaker libraries, idempotency-key design).

## Acceptance criteria

- [ ] **Workload identity (Kagenti-pattern, free/local):** run **SPIRE** in Docker; issue each agent/service an X.509
  SVID; map the SVID identity onto our existing per-agent **ML-DSA-65** identity (SPIFFE for transport/mesh auth, ML-DSA
  for evidence signing — documented dual-identity model). Prove SVID rotation with zero data-plane downtime.
- [ ] **Mesh mTLS + Kagenti/kagent interop:** put the A2A + MCP surfaces behind mesh mTLS (Istio Ambient or a local mTLS
  sidecar); publish a **Kagenti/kagent-compatible AgentCard** (CRD-shaped) so our agent can be deployed/orchestrated
  inside a CNCF agent platform or IBM watsonx Orchestrate (A2A) — channel-fit. Closes **R4/G-4** (A2A endpoint becomes
  AUTHENTICATED, not only RBAC-confined) + **G-064 network pillar**.
- [ ] **Durable-execution hardening** (`backend/runtime/durable/`): wrap every external effect (actuator, A2A call, OT
  write, order dispatch) as an **idempotent, journaled, compensable activity** (idempotency key + saga compensation on
  failure) so a crash/replay never double-acts and a partial failure rolls back cleanly. Build on the existing LangGraph
  PostgresSaver + the append-only signed `audit_chain` (which already IS cryptographic event-sourcing). Add **circuit
  breakers** on the integration clients (OPC UA / Sparkplug / A2A / LLM) with honest-degradation (no fabrication) when a
  breaker is open.
- [ ] **Chaos-as-anti-fragility:** extend `scripts/chaos/` — kill Postgres / Neo4j / an integration mid-decision and
  assert: (a) no fabrication, (b) honest degradation, (c) clean recovery via replay, (d) audit chain still verifies. Each
  drill that finds a weakness → fix → re-drill (anti-fragility = the drill makes it stronger).
- [ ] **Scale foothold (G-066 down-payment):** a multi-worker incident-sharding entrypoint + a pilot-scale load test
  (single-node is fine here; multi-node HA stays pilot/cloud, Rule 9) — proving the runtime holds under concurrent
  incidents without lost/duplicated effects.
- [ ] Tests under `backend/tests/resilience/` + `backend/tests/crypto/` (SVID rotation, mTLS handshake, idempotency,
  saga compensation, circuit-breaker open/close, chaos recovery). Independent review (DIFFERENT agent) → PASS.
- [ ] Explainer `research/stage-explainers/STAGE_27/index.html`.

## Files to CREATE
| Path | Purpose |
|---|---|
| `backend/runtime/durable/{activity,saga,circuit_breaker,idempotency}.py` | durable-execution primitives |
| `backend/security/spiffe_identity.py` | SPIRE SVID fetch/rotate + ML-DSA dual-identity mapping |
| `backend/a2a/agent_card_cnstyle.py` | Kagenti/kagent-compatible AgentCard export |
| `docker/docker-compose.spire.yml` | local SPIRE server/agent + mesh mTLS overlay |
| `scripts/chaos/*.sh` | additional anti-fragility drills |
| `backend/tests/resilience/test_*.py` | resilience/durability tests |
| `research/stage-explainers/STAGE_27/index.html` | explainer |

## Files to MODIFY
| Path | Change |
|---|---|
| `backend/a2a/server.py` | mesh-mTLS client-cert → peer_state binding (authenticated, not only confined) |
| `backend/integrations/**` | circuit breakers + idempotent effects |
| `backend/safety/sil_bridge.py` | actuator effect as a compensable journaled activity |
| `compliance/risk-register.md`, `compliance/dr-runbook.md` | resilience posture update |

## KB files this stage updates
- `KB_13_PQC_Crypto_Strategy.md`, `KB_16_A2A_MCP_Protocols.md`, `KB_17_Functional_Safety_Wrapper.md`,
  `KB_10_Production_Hardening.md`, `KB_TASK_LOG.md`

## Verification commands
```bash
docker compose -f docker/docker-compose.spire.yml up -d
cd backend && python -m pytest tests/resilience/ tests/crypto/ -v
bash scripts/chaos/kill-postgres-drill.sh && python scripts/verify-audit-chain.py
bash scripts/audit.sh   # <= 364
```

## Audit target
- Strict decrease or hold with justification (protocol/infra-heavy; additive real code).

## Role
- Primary: `security-pqc-engineer` (SPIFFE/mTLS) + `devops-sre` (durable/chaos/scale) + `backend-engineer`.

## Hand-off
- What becomes true: rotating workload identity + mesh mTLS (A2A/MCP authenticated + Kagenti-interoperable), external
  effects idempotent+compensable, circuit-breakered integrations, chaos-proven recovery, single-node concurrent-load
  foothold. Multi-node HA + real-fleet-magnitude load stay pilot/cloud (Rule 9, G-066 tail).
