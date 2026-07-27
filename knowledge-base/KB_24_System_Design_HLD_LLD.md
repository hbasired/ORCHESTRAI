---
name: System Design — HLD & LLD
description: High-Level Design (layers, components, flows, deployment, scaling, failure modes) and Low-Level Design (component contracts, schemas, sequences, concurrency) for the embodied-agent industrial control plane
type: spec
last-updated: 2026-05-31
---

# KB_24 — System Design (HLD + LLD)

## Purpose

Own the design altitude between product (PRD) and code (KB_01 "what runs"). HLD = structure, boundaries,
flows, scaling, failure modes. LLD = concrete contracts the implementer builds to. Owned by the
`system-designer` role. Append-only, dated sections.

## Source of truth

- PRD v2.0 §2 (topology) + PRD v2.1 §v2.1.3 (ecosystem seams) + §v2.1.5/6 (crypto boundary, workflow).
- KB_01 (running architecture), KB_13/14/15/16/17/22/23 (domain specs), `audits/OPEN_GAPS_LEDGER.md`.
- Verify HLD against the repo; LLD interfaces against the named source files.

## Body

### 1. High-Level Design (HLD)

**Design tenet:** an open, vendor-neutral *layer* — it sits above/between OT + robot stacks and below business
systems. Every seam is an interface so any layer can be swapped (PRD v2.1 §v2.1.3).

```
                          ┌─────────────────────────── Experience layer ───────────────────────────┐
                          │ Operator dashboards: live agentic vs non-agentic activity, alarms,        │
                          │ predictive-maintenance, observability/teleop, audit-chain & safety panes  │
                          └───────────────▲───────────────────────────────▲──────────────────────────┘
                                          │ WebSocket (KB_04 envelopes)    │ REST
   ┌──────────────── Trust layer ─────────┤                               │
   │ Safety wrapper (LLM-planner /         │                               │
   │ SIL-executor) · ML-DSA-65 signed,     │     ┌───────── Coordination layer ─────────┐
   │ hash-chained audit chain · Annex IV   │     │ EmbodiedCoordinator                   │
   └───────────────▲───────────────────────┘     │  ↳ RoboticsAgent                      │
                   │ every actuator cmd gated      │  ↳ ManufacturingAgent                 │
                   │                               │  ↳ SupplyChainAgent                   │
   ┌─────── Cognition layer ───────┐               │ cross-domain conflict resolution +    │
   │ LangGraph durable runtime      │◀──────────────┤ global optimization (ISOLATED↔COORD) │
   │ (planner) + MCP tool servers   │   plans       └───────────────▲───────────────────────┘
   └───────────────▲────────────────┘                               │ observe / act
                   │ simulate-before-act                            │
   ┌─────── World layer ───────┐                    ┌────────── Ingress / OT layer ─────────┐
   │ SimPy DES (today) →        │                    │ VDA 5050 · OPC UA · MQTT Sparkplug B  │
   │ USD/Omniverse digital twin │                    │ ISA-95 · ROS 2 adapters               │
   └───────────────▲────────────┘                    └───────────────▲───────────────────────┘
                   │                                                  │
   ┌──────────────────────── Data + Memory + Edge/Cloud ────────────────────────────────────┐
   │ Postgres (incidents, audit_chain, checkpoints) · Redis (pubsub/cache) · pgvector + Neo4j │
   │ (memory) · DVC (datasets/skills) · Docker Compose → KubeEdge cloud-edge continuum        │
   └──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Major flows:**
- *Incident*: OT/sim event → `incidents` row + Redis `pubsub:simulator:events` → WS broker → dashboard. (BUILT)
- *Decision*: agents observe → coordinator plans → **simulate in world** → **safety-gate** → execute via adapter → **sign to audit chain** → emit to dashboard. (planner/coordinator BUILT; gate/twin/sign PLANNED)
- *Evidence*: audit_chain → Annex IV pack generator (Stage 19).

**Scaling:** stateless FastAPI workers behind a load balancer; Redis pub/sub fan-out is per-worker
(multi-worker safe); Postgres is the single source of durable truth; agent state checkpointed (resumable).
Edge sites run a KubeEdge node with offline autonomy.

**Failure modes (degrade, don't crash):** Redis down → broker reconnect/backoff, sim keeps running, dashboard
stales gracefully; Postgres write fail → Redis-FIFO retry (Stage 2); LLM/planner down → SIL executor refuses
unsafe actions, operator HITL; key store down → signing queues, no unsigned writes accepted.

### 2. Low-Level Design (LLD) — critical-path contracts

| Component | Contract (file) | Key points |
|---|---|---|
| Incident envelope | `build_incident_envelope` (`backend/services/ws_broker.py`) | KB_04 `{v,type,ts,incident_id,payload}`. BUILT. |
| Fan-out | `ConnectionManager.broadcast` / `SimulatorEventBroker` | per-send timeout + dead-client prune; Redis SUBSCRIBE on own connection; reconnect/backoff. BUILT (11.6 ms measured). |
| Sim→async bridge | `main.py` `_on_incident` | worker-thread → `run_coroutine_threadsafe` → `append_incident`. BUILT. |
| Coordinator | `EmbodiedAgent` (`backend/agents/embodied_agent.py`) | ISOLATED↔COORDINATED; `ConflictResolution`; global optimize. BUILT. |
| Durable workflow | LangGraph `AgentState` + Postgres checkpointer | idempotent tools (input-hash dedupe), bounded retries, compensation, HITL `interrupt()`. PLANNED (Stage 11). |
| Crypto boundary | `KeyProvider` ABC + factory (`backend/crypto/key_provider.py`) | software/PKCS#11/Vault by config; `sign/verify/rotate/capabilities`. PLANNED (Stage 13.5; spec KB_13). |
| Safety gate | `SafetyContract` + `validator.validate(action, world, contract)` | SIL routing (0 direct / 1 confirm / 2+ bridge); fail-safe path. PLANNED (Stage 17; spec KB_17). |
| Memory | namespaced adapters, cross-namespace reads forbidden | working/episodic/semantic/procedural/audit. PLANNED (Stage 12; spec KB_14). |

**Decision sequence (target, Stage 11+):**
```
observe → coordinator.plan() → world.simulate(plan) → if SIL≥1: safety.validate() →
  (SIL0 direct | SIL1 operator confirm | SIL2+ sil_bridge→PLC) → audit_chain.append(signed) → dashboard emit
```

**Concurrency/idempotency:** SimPy in a worker thread (seeded RNG, deterministic); async I/O on the main loop;
tool calls idempotent by `input_hash`; audit_chain append is the serialization point (hash-chained).

### 3. Design → implementation hand-off (who builds what, when)

| Design unit | Implementer role | Stage | Ledger gap |
|---|---|---|---|
| Durable/HITL workflow | backend-engineer | 11 | G-014 |
| Cross-fleet repair-dispatch | backend + robotics-integration | 11 + 16/17 | G-005 |
| KeyProvider/PKCS#11 | security-pqc-engineer | 13.5 | — |
| Safety wrapper | robotics-integration-engineer | 17 | — |
| Digital twin (USD/Omniverse) | ml/devops | 22.7 | G-007 |
| PdM models + dashboard | ml-engineer + frontend | 4 + dashboard | G-006 |
| Evals/guardrails depth | ml-engineer | 20 | G-008 |

## Last verified

2026-05-31, by system-designer (initial HLD/LLD). BUILT items verified against the repo; PLANNED items are
designs for their named stages. Implementers fold in the `OPEN_GAPS_LEDGER.md` rows targeted at their stage.
