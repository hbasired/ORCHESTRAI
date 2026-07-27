# PRODUCT REQUIREMENTS DOCUMENT (PRD) v2.0
## Vendor-Neutral, EU-AI-Act-Grade, PQC-Ready Agent Control Plane for Industrial Robot + OT Fleets

**Document Version**: 2.0
**Date**: 2026-05-18
**Supersedes**: [PRD-ai-embodied-agent.md](PRD-ai-embodied-agent.md) (v1.0, January 2026 — kept as archival reference)
**Target Users**: Manufacturing engineers, warehouse operations leads, OT/IT integrators, compliance officers
**Deployment**: Cloud (GCP Cloud Run / AWS Fargate) + Edge (factory servers, ROS 2 hosts)
**Tech Stack**: Python 3.11, FastAPI, Next.js 15 LTS, LangGraph + Pydantic AI, FastMCP, a2a-sdk, PostgreSQL 15 + pgvector, Neo4j 5, Redis 7, OpenSSL 3.5 + oqs-provider (PQC), Docker Compose
**Licensing posture**: 100% open source (Apache 2.0 / MIT / equivalent). Zero paid SaaS dependencies.

---

## 0. One-Liner

> A vendor-neutral, EU-AI-Act-grade, post-quantum-ready agent control plane for industrial robot and OT fleets — warehouse-first, then discrete manufacturing, then process industries.

## 1. Why This Exists (Repositioning vs. v1)

### 1.1 What changed since v1 (January 2026)
Between January and May 2026 the agentic-industrial market shipped. By May 2026:
- **Microsoft Copilot Studio + Bosch "Manufacturing Co-Intelligence"** went into joint production deployments.
- **Siemens Industrial Copilot** extended into autonomous agents; the Erlangen "first AI-driven adaptive factory" was announced with Nvidia.
- **Nvidia Isaac GR00T N1.7** went commercial with ABB/Fanuc/Hexagon integrations.
- **AWS Bedrock AgentCore** GA, with Mem0 chosen as the exclusive Agent SDK memory provider.
- **IBM watsonx Orchestrate** GA; **ACP** merged into the Linux Foundation **Agentic AI Foundation** alongside MCP and A2A.
- **Google A2A protocol** crossed 150+ production organizations; landed in Azure Foundry and Bedrock AgentCore.
- **Anthropic MCP** donated to the Linux Foundation; 78% of enterprise AI teams report at least one MCP agent in production.

PRD v1 framed this product as another "AI embodied agent for multi-domain manufacturing optimization." That lane is closed. Every hyperscaler and OEM has a copilot for that pitch — most stacks are vertically integrated and proprietary.

### 1.2 The gap PRD v2 attacks
Three concentrated gaps remain. No incumbent has a credible end-to-end answer for any of them:

1. **Vendor-neutral, EU-AI-Act Article 11/12 evidence pipeline** that spans robot fleets (VDA 5050 v2.1.0 / ROS 2), OT (OPC UA + MQTT Sparkplug B v3.0), and LLM agent traces (OpenTelemetry GenAI semconv) into one append-only, hash-chained, ML-DSA-signed provenance graph. Two-thirds of orgs report they cannot determine, after the fact, whether a given action was taken by a human or by an agent. EU AI Act high-risk obligations begin **2026-08-02**.

2. **Crypto-agile, PQC-ready transport** for industrial equipment with 10–20 year deployed lifecycles. NIST finalized FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA) in August 2024. **CNSA 2.0** mandates new NSS acquisitions to be PQC-compliant by **2027-01-01**. The hyperscalers are migrating their cloud edges; the agent-to-PLC last mile is wide open.

3. **Open multi-vendor agent-fleet orchestration** on the post-merger MCP + A2A + ACP stack, glued to industrial standards (VDA 5050 v2.1.0 master controllers, OPC UA, Sparkplug B, ISA-95 Part 2 information model, ROS 2 Jazzy/Kilted). Closed copilots from OEMs lock customers into the OEM's stack; this product treats every vendor as a peer behind a uniform protocol surface.

### 1.3 Wedge and expansion
- **Wedge:** warehouse / fulfillment. VDA 5050 is mature; safety classification is the lowest in industry; ROI math is shortest (3–6 month sales cycle); buyers are pragmatic.
- **Adjacent expansion:** discrete manufacturing (defect/OEE/predictive maintenance). Siemens Erlangen is the benchmark to beat.
- **Long term:** process industries (chemicals, food, pharma). IEC 61511 raises the bar; only enter once warehouse + discrete-mfg are proven.
- **Out of v1/v2 scope:** automotive assembly (captive OEM stacks), defense (CMMC 2.0 + CNSA 2.0 dual compliance is a 12-month side quest of its own).

### 1.4 Differentiation pitch (the one-liner for a BDM at Bosch/Siemens/MS)
> *"The vendor-neutral agent control plane that makes your existing MES/ERP/WMS + any robot fleet EU AI Act-compliant in 90 days, with a PQC roadmap your 2035 board won't have to apologise for."*

### 1.5 What v2 keeps from v1
- The 4-domain crossover (AI ops + supply chain + robotics + manufacturing) remains the product's reason to exist; v2 just adds three new pillars (governance, PQC, vendor-neutral protocol surface) and reframes the pitch.
- The SimPy simulator (Stage 2), the 6-event problem catalog (machine_crack / robot_down / late_delivery / demand_spike / defect_surge / power_dip), and the 15-stage roadmap survive. The roadmap is *extended*, not replaced.
- The success criteria from v1 §1.3 still apply (25–30% cycle-time reduction, 15–20% carbon reduction, <500 ms decision latency, 99.5% uptime, explainability, scalability targets). v2 layers on governance + crypto + standards criteria.

---

### 1.6 New domains (added 2026-05-24)

Post-`report.md` (Project Aether) gap analysis, four new domains added:

- **Energy Intelligence** (KB_20). Microgrid PPO RL + Battery RUL via BatteryLife dataset + carbon-aware Kubernetes scheduling. Strategic for Bosch, Cummins, Siemens (microgrid + BESS investments). Stage 6.5.
- **Edge Compute via KubeEdge** (KB_21). CNCF graduated; offline autonomy; ~70 MB EdgeCore footprint; ArgoCD GitOps. Stage 22.5.
- **USD Digital Twin / NVIDIA Omniverse** (KB_22). Aligned with Siemens Xcelerator Mega Omniverse Blueprint (March 2026). Stage 22.7.
- **Digital Triplet** (KB_22 §22.3). Physical asset + Digital Twin + GenAI semantic layer ("Chat with Factory"). Backed by Mem0 + Neo4j ISA-95 + TimescaleDB. Stage 25.5.

These domains arose from `report.md` (operator-supplied Project Aether portfolio blueprint). After integration, we cover every Project Aether domain AND retain our existing moats (PQC audit chain, functional safety wrapper, EU AI Act + ISO 42001/42005/42006, MCP + A2A, red-team CI gate, federation).

## 2. Architecture (v2 Topology)

```
                              ┌──────────────────────────────────┐
                              │  CUSTOMER OPS UI (Next.js 15 LTS)│
                              │  Dashboard / Decisions / Audit   │
                              └──────────────┬───────────────────┘
                                             │ WSS (mTLS hybrid)
                              ┌──────────────┴───────────────────┐
                              │  FastAPI app + WebSocket gateway │
                              └──┬───────────────────────────────┘
                                 │
       ┌─────────────────────────┴────────────────────────────────┐
       │                                                           │
       │       LangGraph + Pydantic AI Agent Runtime               │
       │   ┌─────────────────┐  ┌─────────────────┐               │
       │   │ Embodied (root) │  │ HITL interrupts │               │
       │   ├─────────────────┤  └─────────────────┘               │
       │   │ Robotics node   │      MCP tools ─────────────┐      │
       │   │ Mfg node        │      (FastMCP servers)      │      │
       │   │ Supply node     │   sim_world / kpi_query /   │      │
       │   │ Safety node     │   decision_log / model_inf /│      │
       │   └─────────────────┘   policy_query              │      │
       │                                                   │      │
       └───────────────────────────────────────────────────┼──────┘
                                                           │
                  ┌────────────────────────────────────────┴───────┐
                  │             Internal services                  │
                  │ Mem0 (PG+pgvector) │ Neo4j ISA-95 │ Redis hot  │
                  │ audit_chain (PG, append-only, ML-DSA-signed)   │
                  │ DVC (procedural skills + datasets)             │
                  └────────────┬─────────────────────────┬─────────┘
                               │                         │
                ┌──────────────┴────────┐    ┌───────────┴───────────┐
                │  A2A boundary         │    │  OT / IT Bridge       │
                │  ML-DSA-signed agent  │    │  OPC UA (asyncua)     │
                │  cards; ML-KEM hybrid │    │  MQTT Sparkplug B     │
                │  mTLS via oqs-provider│    │  ISA-95 Part 2 model  │
                │  sidecar              │    │                       │
                └──────────┬────────────┘    └───────────┬───────────┘
                           │                             │
                ┌──────────┴────────┐         ┌──────────┴────────┐
                │  External agents  │         │  PLC / SCADA /    │
                │  (customer or     │         │  MES / ERP / WMS  │
                │  partner agents)  │         │  (Siemens, AVEVA, │
                │                   │         │   Rockwell, SAP)  │
                └───────────────────┘         └──────────┬────────┘
                                                         │
                              ┌──────────────────────────┴──────────────────┐
                              │  Robot Fleet Adapter — VDA 5050 v2.1.0       │
                              │  master controller (multi-vendor AGV/AMR)    │
                              └─────────────────────┬────────────────────────┘
                                                    │
                                            ┌───────┴──────────────┐
                                            │  Functional Safety   │
                                            │  Wrapper — LLM plan  │
                                            │  → safety contract   │
                                            │  → SIL-rated         │
                                            │  classical executor  │
                                            │  → actuator          │
                                            └──────────────────────┘
```

**Telemetry path (every layer):** OpenTelemetry collector → Langfuse self-hosted (mutable trace store, 90-day retention) **AND** `audit_chain` table (immutable, ML-DSA-signed, 6-month minimum retention per EU AI Act Art. 12). The two stores are separate by design — traces are for debugging, evidence is for regulators.

---

## 3. Standards Map (v2 first-class)

| Domain | Standard | Version | Where in repo |
|---|---|---|---|
| Robot fleet | VDA 5050 | v2.1.0 | `backend/integrations/vda5050/` |
| Industrial IoT | OPC UA | latest | `backend/integrations/opcua/` (`asyncua`) |
| Pub/sub | MQTT Sparkplug B | v3.0 | `backend/integrations/sparkplug/` (paho-mqtt + tahu payload) |
| Enterprise / control integration | ISA-95 Part 2 | object model | `backend/memory/graph_isa95.py` (Neo4j) + `isa95_metadata` (PG mirror) |
| Robotics middleware | ROS 2 | Jazzy / Kilted | `backend/integrations/ros2/` (feature-flagged) |
| Robot safety | ISO 10218-1/2 | :2025 | `backend/safety/contract.py` |
| Collaborative robots | ISO/TS 15066 | current | `backend/safety/contract.py` |
| Functional safety | IEC 61508 | current | `backend/safety/` (SIL-level routing) |
| Machinery safety | ISO 13849-1 | :2023 | `backend/safety/` |
| Programmable safety | IEC 62061 | :2021 | `backend/safety/` |
| AI mgmt system | ISO/IEC 42001 | :2023 | `compliance/` (AIMS control mapping in KB_18) |
| AI risk mgmt | NIST AI RMF Agentic Profile | Feb 2026 | `compliance/risk-register.md` + `compliance/incident-playbook.md` |
| AI regulation | EU AI Act | enforcement 2026-08-02 | Annex IV doc-pack generator in `scripts/generate-annex-iv-doc.py` |
| PQC | NIST FIPS 203 / 204 / 205 | :2024 | `backend/crypto/` |
| PQC migration | NIST IR 8547 | current | `KB_13_PQC_Crypto_Strategy.md` |
| PQC government | CNSA 2.0 | deadline 2027-01-01 | `KB_13` rotation plan |
| LLM observability | OpenTelemetry GenAI semantic conventions | 2026 (experimental) | `backend/observability/otel_init.py` |
| LLM threats | OWASP LLM Top 10 | current | `compliance/incident-playbook.md` + Stage 20 evals |

---

## 4. A2A + MCP Surface

### 4.1 Why both — not one or the other
After the Linux Foundation Agentic AI Foundation merger (late 2025 / early 2026), MCP and A2A are **complementary**, not competitive:
- **MCP** = how an individual agent reaches tools, resources, prompts (vertical: agent ↔ tools/data).
- **A2A** = how agents discover, delegate, and coordinate across organizations or vendors (horizontal: agent ↔ agent).
- **ACP** (IBM) is folded into the same foundation.

This product ships both. MCP for internal agent→tool; A2A for any external boundary (cross-org delegation, multi-plant orchestration, vendor agent integration).

### 4.2 MCP servers (Stage 11.5)
Five FastMCP servers, each a separate supervised process. Mounted into the LangGraph runtime via `langchain-mcp-adapters`.

| Server | Tools | Source |
|---|---|---|
| `sim_world_server` | `inject_event`, `query_state`, `subscribe_events` | `backend/mcp_servers/sim_world_server.py` |
| `kpi_query_server` | `throughput`, `oee`, `utilization`, `queue_depth` | `backend/mcp_servers/kpi_query_server.py` |
| `decision_log_server` | `append_decision`, `query_decisions` (writes route through `backend/memory/audit_chain.py`) | `backend/mcp_servers/decision_log_server.py` |
| `model_inference_server` | `predict_demand`, `predict_failure`, `classify_defect` | `backend/mcp_servers/model_inference_server.py` |
| `policy_query_server` | `recommend_action`, `explain_action` | `backend/mcp_servers/policy_query_server.py` |

### 4.3 A2A surface (Stage 14)
- **Discovery:** `GET /.well-known/agent.json` returns the signed agent card.
- **Agent card:** Pydantic model (`backend/a2a/agent_card.py`) — `name`, `capabilities`, `endpoints`, ML-DSA-65 public key, supported protocols (`a2a/1.0`), provenance metadata, expiry, signature over JCS-canonicalized JSON.
- **Transport:** plain HTTP to a sidecar that terminates client TLS with ML-KEM-768 + X25519 hybrid (OpenSSL 3.5 + oqs-provider via haproxy/stunnel).
- **Peer trust:** pinned root keys in `docker/secrets/a2a_roots/`; revocation list polled from a configurable URL.
- **mTLS:** at the sidecar with PQC client auth (CNSA 2.0 alignment).
- **Use cases:**
  - Warehouse fulfillment agent delegating to a carrier's logistics agent.
  - Plant-level orchestration agent talking to a vendor-supplied robot-fleet agent without giving it MCP-level access into the customer's ERP.
  - Cross-site agents in a multi-plant manufacturer where each site has its own MES.

---

## 5. Post-Quantum Cryptography Strategy

### 5.1 Algorithm placement
| Layer | Algorithm | Rationale |
|---|---|---|
| Agent ↔ agent TLS (A2A external) | **ML-KEM-768 + X25519 hybrid** | Matches Chrome/Cloudflare/AWS pattern; ≤200 µs handshake overhead |
| Signed agent actions, audit chain entries, agent cards | **ML-DSA-65** (FIPS 204) | Smaller than SLH-DSA; fast verify on PLC-class hardware |
| Firmware updates to edge devices and robot controllers; signed policy bundles | **SLH-DSA-SHA2-128s** (FIPS 205) | Stateless hash-based; cryptanalytically conservative; only viable choice for 15-year code-signing trust horizon |
| OT message integrity (Sparkplug B payloads, OPC UA UserTokenPolicy MAC) | **HMAC-SHA-384** | Already quantum-resistant at this length; documented as such |

### 5.2 Library choices (Docker/Linux only — no Windows-native build)
- `liboqs` (system package; built into backend Docker image).
- `liboqs-python` for ML-DSA-65, ML-KEM-768, SLH-DSA-SHA2-128s primitives.
- Python `cryptography` for HMAC-SHA-384, X25519, SHA-256, key serialization.
- OpenSSL 3.5+ with `oqs-provider` for TLS termination — runs in a **sidecar** (`docker/docker-compose.pqc.yml`) so the Python process doesn't need PQC TLS bindings.
- `hvac` for HashiCorp Vault Transit (pilot) or `python-pkcs11` for SoftHSM (no-budget dev default).

### 5.3 Key inventory & rotation
| Key | Algorithm | Storage | Rotation | Used in |
|---|---|---|---|---|
| `agent-identity-<env>` | ML-DSA-65 | Vault Transit (pilot) / SoftHSM (dev) | quarterly | A2A agent-card signature; decision-log hash chain |
| `agent-tls-<env>` | ML-KEM-768 + X25519 | Vault Transit / SoftHSM | quarterly | Sidecar TLS |
| `firmware-policy-<env>` | SLH-DSA-SHA2-128s | Offline HSM (SoftHSM in dev) | annual | Signed policy bundles, model-card attestations |
| `ot-msg-integrity-<env>` | HMAC-SHA-384 | Vault Transit / SoftHSM | monthly | OPC UA + Sparkplug B message MAC |

Rotation drill: `scripts/rotate-pqc-keys.sh` performs overlap rotation, signs the audit-chain with both old and new keys for a grace window, then revokes the old key. CNSA 2.0 deadline (2027-01-01) requires NSS-facing surfaces to be PQ-only (not hybrid) — the script supports `--mode={hybrid,pq-only,classical-only}`.

---

## 6. Functional Safety Wrapper

### 6.1 Architectural principle
**LLM = planner. Classical SIL-rated controller = executor. Formal contract gates every actuator command.**

An LLM is non-deterministic and cannot provide the validation that ISO 10218 / IEC 61508 / ISO 13849-1 require. The wrapper architecturally enforces that the LLM contributes plans only; a classical controller (PLC-bridged) is the actual actuator. This makes the system *amenable* to TÜV / notified-body certification — actual certification is a Stage 23 + external-assessor activity, not a code-only claim.

### 6.2 Component shape
- `backend/safety/contract.py` — Pydantic safety-contract DSL: preconditions, postconditions, invariants (speed limits per ISO/TS 15066, separation distances, collision force thresholds).
- `backend/safety/validator.py` — pre-flight check; every actuator-bound action must pass through `validate(action, world_state, contract) -> Decision`.
- `backend/safety/sil_bridge.py` — bridge to PLC / safety controller (OPC UA Safety profile or PROFIsafe placeholder).
- `backend/safety/sto_ss1.py` — emergency stop / safe stop 1 paths.

### 6.3 SIL routing
| SIL | Examples | Path |
|---|---|---|
| SIL 0 | LLM planning, monitoring, dashboarding | LLM direct |
| SIL 1 | Routing recommendations, throughput throttling (advisory) | LLM → validator → operator UI for confirmation |
| SIL 2+ | Any actuator command (robot motion, conveyor start/stop, machine state change) | LLM → validator → classical executor → PLC (LLM CANNOT bypass) |

The CI gate enforces this: every actuator-path test must show a `safety.validate` OpenTelemetry span immediately before the `actuator` span, or the test fails.

---

## 7. Agent Memory Architecture

### 7.1 Layers
| Layer | Lifespan | Backend | Purpose |
|---|---|---|---|
| Working | per-task (<8 k tokens) | In-process (Pydantic `AgentState` in LangGraph; Postgres checkpointer) | Current task scratchpad |
| Episodic | per-shift, per-incident | **Mem0** on PostgreSQL + pgvector | Diary: "we tried X last shift, failed" |
| Episodic (long-horizon, opt-in) | shift-persistent | **Letta** (MemGPT) | Multi-day agent personality memory |
| Semantic | persistent | pgvector + **Neo4j** ISA-95 graph | KB, SOPs, equipment hierarchy |
| Procedural | versioned | DVC-tracked `data/skills/<name>/skill.yaml` | Learned recipes / playbooks |
| Audit | append-only, indefinite | PostgreSQL `audit_chain` (immutable + ML-DSA-65 signed) + `pgaudit` | EU AI Act Art. 12 evidence |

### 7.2 Why Mem0 as default (and Letta as opt-in)
- Mem0 won the 2026 benchmarks on token footprint (1,764 vs Zep ~600k per conversation) and latency.
- Mem0 is the exclusive memory provider for AWS Bedrock AgentCore — adoption signal.
- Mem0 backs naturally onto PostgreSQL + pgvector (no new datastore to operate).
- Letta is genuinely better for multi-day agent identity but adds operational weight; reserve for pilot customers who actually need shift-persistent personality.

### 7.3 SQL not NoSQL
The user explicitly asked for the SQL-vs-NoSQL decision. Verdict: **SQL**.
- Auditors (EU AI Act conformity assessors, ISO/IEC 42001 internal audit, SOC 2) want SQL — they know how to query Postgres, not Mongo or Cassandra.
- PostgreSQL with pgvector handles both relational schema and embeddings without a second datastore.
- pgaudit + immutability triggers on `audit_chain` give the legal-grade evidence Art. 12 requires.
- The graph layer (Neo4j) is the one exception — graph queries on ISA-95 are genuinely better in Cypher than SQL.

### 7.4 Namespacing & retention
- Per `incident_id`, per operator, per agent role.
- Cross-namespace reads forbidden in `mem0_adapter.py` (enforced).
- Retention: `retained_until` column on every Mem0 row; sweep job purges expired (GDPR + Art. 12 retention).
- `audit_chain` has no retention — append-only, ML-DSA-signed, chained by SHA-256 prev_hash.

---

## 8. Observability & Evidence Pipeline

### 8.1 Two stores, separated by design
- **Trace store (mutable, 90-day retention):** Langfuse v3 self-hosted (Postgres + ClickHouse + Redis). For debugging, performance, eval review.
- **Evidence store (immutable, indefinite):** `audit_chain` table in PostgreSQL — append-only, ML-DSA-65 signed, SHA-256 hash chained. For regulators, auditors, post-market monitoring under EU AI Act Art. 72.

Traces are noisy and pruned; evidence is forever. Mixing them in a single store is a compliance own-goal.

### 8.2 OpenTelemetry GenAI semantic conventions
Every layer instrumented:
- LangGraph node entry/exit (`langgraph.node.<name>`).
- MCP tool calls (`mcp.tool.<server>.<tool>`).
- A2A inbound/outbound (`a2a.peer.<peer>.<method>`).
- Model inference (`gen_ai.completion`, `gen_ai.embedding`, `ml.inference.<model>`).
- Safety validator gates (`safety.validate.<contract>`).
- Audit-chain appends (`audit_chain.append`).
- Memory reads/writes (`memory.<backend>.<op>`).

### 8.3 Phoenix evals as CI gate (Stage 20)
Nightly runs on:
- Prompt-injection corpus (OWASP LLM01).
- NIST AI RMF Agentic attack vectors (Feb 2026 profile).
- Industry-specific safety scenarios.

Thresholds in `backend/training/evals/thresholds.yaml`; CI fails on breach.

---

## 9. Governance Mapping

### 9.1 ISO/IEC 42001:2023 — AI Management System
Control mapping in `knowledge-base/KB_18_Governance_Evidence.md`. Highlights:
- A.6.1 (AI policy) → repo-level `compliance/ai-policy.md` (to be authored Stage 19).
- A.7 (resources) → DVC-tracked datasets, model cards, key inventory.
- A.8 (AI system impact assessment) → `compliance/risk-register.md` augmented per stage.
- A.9 (lifecycle) → 25-stage roadmap + decision logs + audit reports.
- A.10 (data) → DVC + dataset CARDs + retention policy.

### 9.2 EU AI Act
| Article | Obligation | Where met |
|---|---|---|
| Art. 9 (risk mgmt) | Risk register, continuous review | `compliance/risk-register.md` |
| Art. 10 (data governance) | Dataset CARDs, bias audits | `data/datasets/*/CARD.md` + Stage 5/6/9 model cards |
| Art. 11 (technical docs) | Annex IV doc-pack | `scripts/generate-annex-iv-doc.py` |
| Art. 12 (record-keeping) | 6-month minimum agent action logs | `audit_chain` table, indefinite retention |
| Art. 13 (transparency) | Operator-facing decision explanations | Frontend decision panel + SHAP/DiCE (Stage 10) |
| Art. 14 (human oversight) | HITL interrupts, override path | LangGraph `interrupt()` + `compliance/human-oversight.md` |
| Art. 15 (accuracy + cybersecurity) | PQC, hybrid TLS, eval suite | `backend/crypto/` + `KB_13` + Stage 20 evals |
| Art. 26 (deployer obligations) | Incident playbook | `compliance/incident-playbook.md` |
| Art. 72 (post-market monitoring) | Live ops monitoring loop | Stage 25 |
| Annex III | High-risk classification (safety component) | `compliance/risk-register.md` row 1 |

### 9.2b ISO/IEC 42005:2025 (AI system impact assessment) + ISO/IEC 42006 (audit) — added 2026-05-24

ISO/IEC 42005:2025 (published May 2025) provides structured guidance for AI system impact assessment. Complements ISO/IEC 42001 (AIMS). We adopt:
- `compliance/impact-assessments/<system>.md` template + auto-generator (Stage 19, `scripts/generate-impact-assessment.py`).
- Reads from PRD §1.2 + risk register + Annex III classification + model cards + safety contracts.

ISO/IEC 42006 specifies audit requirements for ISO/IEC 17021-1 bodies certifying AI management systems. We adopt:
- `compliance/iso-42006-audit-readiness.md` checklist for Stage 23 conformity dry-run.

### 9.2c Governance enforcement hardening — competitive parity with Galileo / Guild.ai (added 2026-05-24)

Per `compliance/decision-logs/2026-05-24_governance_hardening_and_training_scaffold.md` and `knowledge-base/KB_19_Competitor_Comparative_Governance.md`, three capabilities added to match best-in-class governance platforms (Galileo Agent Control, Guild.ai) while keeping our existing moat (PQC audit chain + functional safety wrapper + industrial standards):

- **Policy DSL** (Stage 19): Pydantic-validated `compliance/policies/*.yaml`, ML-DSA-65 signed, enforced at OTel span emit + MCP boundary + safety validator + CI gate.
- **Per-tool RBAC + Governed Runtime** (Stage 11.5): each MCP tool declares `required_capabilities`; agent registry with capability + identity key version; MCP server process sandbox.
- **Budget caps + approval workflows** (Stage 11.5): token/call budget tracker integrated with LangGraph; declarative `approval-required` MCP tool tags trigger HITL `interrupt()`.
- **PII output filter** (Stage 19): MCP server boundary; email/phone/SSN/IBAN/credit-card patterns; EU=hard, non-EU=soft.

After these land, the project matches or exceeds Galileo Agent Control and Guild.ai on every published governance dimension PLUS keeps the six moat dimensions no competitor has (PQC audit chain, functional safety wrapper, industrial standards, Annex IV pack, red-team CI gate, A2A federation).

### 9.3 NIST AI RMF Agentic Profile (Feb 2026)
| Attack vector | Mitigation | Where |
|---|---|---|
| Prompt injection via tool outputs | JSON schema enforcement + heuristic sanitizer before LLM context | LangGraph node validators |
| Cross-session memory leakage | Per-`incident_id` namespacing; cross-namespace reads rejected | `backend/memory/mem0_adapter.py` |
| Tool-chain provenance gaps | Every tool call records `(caller, tool, input_hash, output_hash)` | `audit_chain` |
| Excessive agency | Safety wrapper + operator confirmation for SIL 1+ | `backend/safety/validator.py` |
| Model supply-chain | DVC pinning + model cards + SLH-DSA-signed bundles | Stage 18 PQC Wave 2 |

---

## 10. The 25-Stage Roadmap (v2)

Stage 2 (SimPy) is **unchanged**. New stages slot in around and after. CTO checkpoints fire every 10 task-doc completions and are internal cadence (not part of the marketed roadmap).

| # | Stage | Status |
|---|---|---|
| 1 | Foundation & KB | ✅ Done (2026-05-11) |
| 2 | SimPy DES — port + 6-event catalog → `incidents` table | 🟡 Next (locked) |
| 3 | WebSocket broker + Redis fanout | ⚪ Existing |
| **3.5** | **CTO Checkpoint #1** | ⚪ New |
| 4 | Predictive maintenance (Transformer / MsFormer) | ⚪ Existing, reframed |
| 5 | Defect detection (Real-IAD + Conv-AE) | ⚪ Existing |
| 6 | Demand forecasting (M5 / TFT) | ⚪ Existing |
| 7 | RL Policy (Isaac Sim + PPO + safety reward) | ⚪ Existing |
| 8 | World model (Dreamer-V3 / LeWorldModel) | ⚪ Existing |
| 9 | Robot vision (YOLOv10 + obstacle CNN) | ⚪ Existing |
| 10 | Explainability (real SHAP + DiCE counterfactuals) | ⚪ Existing |
| **10.5** | **CTO Checkpoint #2** | ⚪ New |
| 11 | **LangGraph + Pydantic AI runtime (pulled forward)** | ⚪ New (was Stage 11+) |
| 11.5 | **MCP server suite (FastMCP × 5)** | ⚪ New |
| 12 | **Agent Memory (Mem0 + pgvector + Neo4j ISA-95 + audit_chain)** | ⚪ New |
| 12.5 | **Observability (OTel GenAI semconv + Langfuse + Phoenix)** | ⚪ New |
| 13 | CDC ingestion (DB-driven scenarios) | ⚪ Existing |
| 13.5 | **PQC Foundations (ML-DSA-65 signing for decision_logs + key mgmt)** | ⚪ New |
| 14 | **A2A Protocol Surface (signed agent cards, ML-KEM hybrid mTLS)** | ⚪ New |
| **14.5** | **CTO Checkpoint #3** | ⚪ New |
| 15 | **OT/IT Bridge (OPC UA + Sparkplug B + ISA-95 graph)** | ⚪ New |
| 16 | **Robot Fleet Adapter (VDA 5050 v2.1.0 master controller)** | ⚪ New |
| 17 | **Functional Safety Wrapper (LLM planner → SIL executor)** | ⚪ New |
| 18 | **PQC Migration Wave 2 (hybrid TLS everywhere, SLH-DSA firmware)** | ⚪ New |
| 19 | **Governance Evidence Pipeline (immutable sink, Annex IV generator)** | ⚪ New |
| 20 | **Red-team & Adversarial Eval Harness (Phoenix as CI gate)** | ⚪ New |
| 21 | DR / HA / backups / chaos | ⚪ Reframed (was old Stage 14) |
| **21.5** | **CTO Checkpoint #4** | ⚪ New |
| 22 | Pilot deployment runbook (warehouse wedge) | ⚪ Reframed (was old graduation) |
| 23 | **Conformity assessment dry-run (Annex IV doc-pack + ISO 10218 RA)** | ⚪ New |
| 24 | Graduation / GA release | ⚪ Reframed |
| **24.5** | **CTO Checkpoint #5** | ⚪ New |
| 25 | **Post-GA (PQC rotation drill, A2A federation test, post-market monitoring)** | ⚪ New |

Each new stage has its own task doc seeded from `tasks/TASK_TEMPLATE.md`.

---

## 11. Success Criteria (v2)

In addition to v1 §1.3 (efficiency, sustainability, latency, uptime, explainability, scalability):

| Criterion | Target | Stage |
|---|---|---|
| EU AI Act Annex IV doc-pack auto-generates | ≤ 60 s, full pack | Stage 19 |
| Audit chain integrity verifiable | `verify-audit-chain.py` passes end-to-end at any time | Stage 13.5+ |
| A2A federation interop | Two independent instances exchange signed messages | Stage 14 |
| VDA 5050 message conformance | 100% schema validation against VDA reference fixtures | Stage 16 |
| Functional safety gate coverage | 100% of actuator paths have `safety.validate` span | Stage 17 |
| PQC posture | Every external boundary supports ML-KEM-768 + X25519 hybrid TLS | Stage 18 |
| Crypto agility | Key rotation drill completes in ≤ 15 min with zero data plane downtime | Stage 18, drilled Stage 25 |
| Prompt-injection eval pass rate | ≥ 99% on OWASP LLM01 corpus + NIST RMF Agentic vectors | Stage 20 |
| Conformity dry-run | Notified-body / external assessor can complete review with the auto-generated pack | Stage 23 |

---

## 12. Risks & What Could Kill the Project

1. **Hyperscaler bundling.** Microsoft + Bosch could ship 80% of v2's value as a Fabric SKU by Q4 2026. *Mitigation:* keep the spine Apache 2.0; proprietary value is the compliance evidence pipeline + the PQC roadmap discipline, not the agent runtime.
2. **EU AI Act enforcement softens.** Council/Parliament already agreed (May 2026) to streamline rules. *Mitigation:* don't make this a 100% compliance-only pitch; OEE/throughput gains stand alone.
3. **Functional safety hubris.** First LLM-driven SIL-2 fatality ends the project. *Mitigation:* the wrapper split is architectural and contractual, not "best practice."
4. **Mem0/Letta vendor consolidation.** *Mitigation:* memory + observability behind interfaces, not tight coupling.
5. **GR00T N2 + Bedrock AgentCore commoditize embodied agents by mid-2027.** *Mitigation:* ship the warehouse wedge by Q1 2027.
6. **Industrial enterprise sales cycle (9–18 months).** *Mitigation:* warehouse SaaS wedge has 3–6 month cycles; funds the manufacturing push.
7. **Over-scope.** This repo already has 13 KB docs, compliance dirs, simulation, frontend, backend, DVC, Docker, Alembic. *Mitigation:* the 25-stage roadmap forces depth-per-stage; CTO checkpoints catch breadth-over-depth before it metastasizes.

---

## 13. Appendix — What v2 keeps verbatim from v1

The following v1 sections are still authoritative; v2 references them rather than restating:

- v1 §2.1 (Real-Time System Perception sub-features for robotics tracking, manufacturing monitoring, supply chain visibility).
- v1 §3 (Frontend Dashboard Specification — 4 quadrants).
- v1 §4 (AI Decision Panel — live feed, confidence, counterfactuals).
- v1 §5 (Optimization Control Panel — throughput/energy tradeoffs).
- v1 §6 (Alerts & Warnings).
- v1 §7 (API Specification — REST + WebSocket endpoints; extended in v2 by KB_07 with A2A and MCP additions).
- v1 §8 (Data Pipeline — extended by the OT/IT bridge stages).
- v1 §9 (ML Models — extended by Stages 4–10 model cards).
- v1 §10 (Deployment Architecture — extended by Stage 22 pilot runbook).

The v1 PRD is preserved at [PRD-ai-embodied-agent.md](PRD-ai-embodied-agent.md) for the historical record.

---

## 14. Related Documents

- [CLAUDE.md](CLAUDE.md) — Claude Code role-based orchestration entrypoint.
- [SKILLS.md](SKILLS.md) — Role persona index.
- [knowledge-base/KB_README.md](knowledge-base/KB_README.md) — KB index (updated with KB_12–18).
- [knowledge-base/KB_12_Standards_Map.md](knowledge-base/KB_12_Standards_Map.md) — VDA 5050 / OPC UA / Sparkplug B / ISA-95 / ROS 2 / ISO / IEC details.
- [knowledge-base/KB_13_PQC_Crypto_Strategy.md](knowledge-base/KB_13_PQC_Crypto_Strategy.md) — ML-DSA / ML-KEM / SLH-DSA placement and rotation.
- [knowledge-base/KB_14_Agent_Memory_Architecture.md](knowledge-base/KB_14_Agent_Memory_Architecture.md) — Mem0 + pgvector + Neo4j + audit_chain.
- [knowledge-base/KB_15_Observability_Evidence_Pipeline.md](knowledge-base/KB_15_Observability_Evidence_Pipeline.md) — OTel GenAI + Langfuse + Phoenix + evidence sink.
- [knowledge-base/KB_16_A2A_MCP_Protocols.md](knowledge-base/KB_16_A2A_MCP_Protocols.md) — MCP servers + A2A agent cards + trust boundary.
- [knowledge-base/KB_17_Functional_Safety_Wrapper.md](knowledge-base/KB_17_Functional_Safety_Wrapper.md) — LLM-as-planner / SIL-as-executor.
- [knowledge-base/KB_18_Governance_Evidence.md](knowledge-base/KB_18_Governance_Evidence.md) — ISO/IEC 42001 + Annex IV pack.
- [compliance/decision-logs/2026-05-18_prd_v2_repositioning.md](compliance/decision-logs/2026-05-18_prd_v2_repositioning.md) — ADR for this expansion.
