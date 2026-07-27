---
name: Standards Map
description: Industrial standards adopted by this control plane — exact versions, where each is implemented, mapping to risk register and compliance evidence
type: spec
last-updated: 2026-05-18
---

# KB_12 — Standards Map

## Purpose

Single point of truth for every industrial standard this product touches. Versions, source of authority, where in the repo each standard is implemented, and which `compliance/risk-register.md` row covers any non-compliance risk.

## Source of truth

- Standards bodies (VDA, OPC Foundation, Eclipse Sparkplug, ISO, IEC, NIST, OASIS).
- This file is updated when a new standard is added or an existing standard's version bumps. Update rule: standard version change → bump KB_12 + corresponding KB body file (e.g., KB_13 for crypto, KB_17 for safety) + `compliance/risk-register.md`.

## Body

### Standards inventory

| Domain | Standard | Version | Authority | Implemented in | Compliance evidence |
|---|---|---|---|---|---|
| Robot fleet command | VDA 5050 | v2.1.0 | VDA (German Automotive Industry Association) | `backend/integrations/vda5050/` | Stage 16 conformance tests |
| Industrial IoT (T-D communication) | OPC UA | OPC UA Specification 1.05 | OPC Foundation | `backend/integrations/opcua/` (asyncua 1.1.x) | Stage 15 cert rotation |
| Pub/sub for IIoT | MQTT Sparkplug B | v3.0 | Eclipse Foundation | `backend/integrations/sparkplug/` (paho-mqtt + tahu) | Stage 15 birth/death/data tests |
| Enterprise-to-control integration model | ISA-95 Part 2 | latest | ISA / IEC 62264-2 | `backend/memory/graph_isa95.py` (Neo4j) + `isa95_metadata` mirror | KB_14 + Stage 12 |
| Robotics middleware | ROS 2 | Jazzy / Kilted | Open Robotics | `backend/integrations/ros2/` (feature-flagged via `ENABLE_ROS2=1`) | Stage 16 (optional adapter) |
| Industrial robot safety | ISO 10218-1/2 | :2025 (third edition) | ISO/TC 299 | `backend/safety/contract.py` (preconditions) | Stage 17 + Stage 23 conformity |
| Collaborative robot safety | ISO/TS 15066 | current | ISO/TC 299 | `backend/safety/contract.py` (collision force thresholds) | Stage 17 |
| Functional safety (E/E/PE systems) | IEC 61508 | parts 1–7 | IEC | `backend/safety/` (SIL classification routing) | Stage 17 |
| Machinery safety (control system parts) | ISO 13849-1 | :2023 | ISO/TC 199 | `backend/safety/` (PL routing) | Stage 17 |
| Programmable electronic safety (machinery) | IEC 62061 | :2021 | IEC/TC 44 | `backend/safety/` | Stage 17 |
| AI management system | ISO/IEC 42001 | :2023 | ISO/IEC JTC 1/SC 42 | `compliance/` (AIMS controls mapped in KB_18) | Stage 19 + Stage 23 |
| AI risk management | NIST AI RMF (Agentic Profile) | Feb 2026 | NIST | `compliance/risk-register.md` + `compliance/incident-playbook.md` | Stage 19 |
| EU AI Act | Regulation (EU) 2024/1689 | ~~2026-08-02 high-risk~~ → **Annex III 2 Dec 2027 / Annex I 2 Aug 2028** (Digital Omnibus, 2026-05-07; corrected 2026-05-31) | European Commission | `scripts/generate-annex-iv-doc.py` + `compliance/` | Stage 19 doc-pack; Stage 23 dry-run |
| PQC algorithms | NIST FIPS 203 (ML-KEM), 204 (ML-DSA), 205 (SLH-DSA) | :2024 | NIST | `backend/crypto/` | Stage 13.5 + Stage 18; rotation drill Stage 25 |
| PQC migration guidance | NIST IR 8547 | current | NIST | `KB_13_PQC_Crypto_Strategy.md` | Stage 18 plan |
| US government PQC mandate | CNSA 2.0 | deadline 2027-01-01 (NSS) | NSA / CISA | `KB_13` rotation timeline | Stage 18 / 25 |
| LLM observability | OpenTelemetry GenAI semantic conventions | 2026 (experimental, rapidly stabilising) | OpenTelemetry / CNCF | `backend/observability/otel_init.py` | Stage 12.5 |
| LLM threats | OWASP LLM Top 10 | current | OWASP | `compliance/incident-playbook.md` + Stage 20 evals | Stage 20 |
| Agent protocols | Model Context Protocol (MCP) | spec current; Anthropic donated to Linux Foundation Agentic AI Foundation Dec 2025 | Linux Foundation / Anthropic origin | `backend/mcp_servers/` (FastMCP) | Stage 11.5 |
| Agent protocols | A2A | spec current; donated to Linux Foundation Agentic AI Foundation | Linux Foundation / Google origin | `backend/a2a/` (`a2a-sdk` Python) | Stage 14 |

### Coverage gaps tracked

| Standard | Status in repo | Reason for gap | Target stage |
|---|---|---|---|
| IEC 61511 (process safety) | Not implemented | Process industries are post-warehouse / discrete-mfg wedge per PRD v2 | Post-Stage 25 (future product wave) |
| ISA-100.11a / WirelessHART | Not implemented | OPC UA + Sparkplug B cover initial wedge; wireless can be a customer-driven extension | TBD |
| CMMC 2.0 / NIST SP 800-171 | Not implemented | Defense customers are explicitly out of v2 scope | Future product line |
| GxP (FDA / EMA / ICH) | Not implemented | Pharma is process-industries territory; out of v2 wedge | Future product line |

### Version-pinning policy

- VDA 5050 JSON Schemas pinned at v2.1.0 — committed under `backend/integrations/vda5050/schemas/` and regenerated only on a deliberate version bump (which requires an ADR + risk register update + conformance test refresh).
- OPC UA Security Policy: interim `Aes256_Sha256_RsaPss` while classical-only; PQC overlay (HMAC-SHA-384 + ML-DSA signed cert chain) tracked in KB_13, implementation in Stage 18.
- Sparkplug B v3.0 (NOT v2.x) — birth/death semantics changed; payload encoding remains protobuf.
- ISO 10218 third edition (2025) supersedes 2011 first edition; risk register row tracks the upgrade.

### Where standards intersect the agent runtime

- VDA 5050 `order` / `instantActions` outbound: master controller writes; LangGraph node calls master via MCP tool `policy_query.recommend_action`; every command passes through `backend/safety/validator.py` first.
- OPC UA inbound telemetry: subscription callbacks feed the LangGraph `world_state` node via `sim_world_server.subscribe_events`.
- Sparkplug B node/device birth: triggers ISA-95 graph node creation in Neo4j (Stage 15).
- ROS 2 messages: optional bridge for customers running ROS-native fleets; feature-flagged so CI doesn't require rclpy in the base image.

## Last verified

2026-06-21 (Stage 17), by robotics-integration-engineer: the **functional-safety standards are now IMPLEMENTED in code**
(`backend/safety/`) — IEC 61508 SIL routing + ISO 13849-1:2023 PL mapping (`sil_pl_map.py`), ISO/TS 15066 collaborative
speed/separation as contract invariants, ISO 10218-1/2:2025 clauses per-contract, IEC 61800-5-2 STO/SS1. The
LLM-planner/SIL-executor split + the `safety.validate`-before-`actuator` CI invariant are live (KB_17). Agentic
**zero-trust** adopts **NIST SP 800-207** (+ CSA Agentic Trust/MAESTRO/OWASP NHI) with per-agent ML-DSA-65 identity +
MCP tool authz + signed manifest (`backend/security/`). Actual SIL certification = Stage 23 + external assessor (no
claim). ADR `2026-06-21_stage17_functional_safety_wrapper.md`. — Prior:

2026-06-20 (Stage 16), by robotics-integration-engineer: the **VDA 5050 v2.1.0 robot-fleet master controller is BUILT** —
`backend/integrations/vda5050/`: the 6 **official upstream JSON schemas** vendored from the VDA5050 repo at tag **2.1.0**
(MIT; `schemas/*.json` + `SCHEMAS_PROVENANCE.md` — NOT main, which is v3.0.0: caught because v3 `state` uses
`powerSupply` vs v2.1.0 `batteryState`); **Pydantic `models/` GENERATED** from them by `datamodel-code-generator`;
`topics.py` (the `uagv/v2/<mfr>/<sn>/<topic>` namespace); `master.py` (`Vda5050Master` — subscribes
state/connection/factsheet/visualization, publishes order/instantActions, **verifies connection freshness + ONLINE
before any order dispatch** [anti-spoof], routes every dispatch through `backend/safety/validator.py`); `actions.py`
(maps an intervention decision + fleet context → a VDA-5050 order graph). **`backend/safety/validator.py`** is the
Stage-16 **structural + freshness gate** emitting the `safety.validate` span (the SIL-rated contract validator is
Stage 17). `mcp_servers/policy_query_server.py::recommend_action` now returns **VDA-5050-shaped routing** when a `fleet`
block is present. **Verified live:** canned order/state/connection validate against the real v2.1.0 schemas + parse into
the generated models; an invalid order is rejected; the master dispatches to a **simulated AGV over a real Mosquitto
broker** + receives state; stale/offline AGVs are refused — **`tests/integrations/test_vda5050_*` 13 tests pass**
(incl. a test that the `policy_query.recommend_action` MCP tool emits VDA routing only when a `fleet` block is present).
CI gate `vda5050-schema-validate`. **CTO #3 remediations:** **G-059 RESOLVED** (the runtime `orient` node routes its
prediction through `model_inference_server` over MCP stdio when `RUNTIME_MCP_MEDIATED=1` — a genuinely MCP-mediated
decision; 2 tests pass) + **R11** (Groq→Ollama free-cost fallback proven LIVE against a local Ollama). New deps:
`datamodel-code-generator` (build-time). Actuator SIL wrapper + STO/SS1 = Stage 17; live mTLS/PQC = Stage 18.
ADR `2026-06-20_stage16_vda5050_robot_fleet.md`.

Prior: 2026-06-20 (Stage 15), by robotics-integration-engineer: the **OT/IT bridge is BUILT** — `backend/integrations/`:
- **OPC UA** (`opcua/server.py` + `opcua/client.py`, **asyncua 1.1.5**): an ISA-95 Part-2 tree
  (Enterprise→Site→Area→WorkCenter→WorkUnit) served with live telemetry vars; a subscribe-only client that browses +
  reads + receives data-change notifications. Interim policy **Aes256Sha256RsaPss** (armed only when certs loaded —
  `secure_policy_enabled()` reports honestly); certless `NoSecurity` for the in-process roundtrip; PQC overlay = Stage 18.
- **MQTT Sparkplug B v3.0** (`sparkplug/payload.py` + `sparkplug/client.py`): the **real protobuf** wire format
  (canonical Eclipse `sparkplug_b.proto` → `sparkplug_b_pb2.py`, compiled by `grpcio-tools`, NOT mqtt-spb-wrapper),
  full edge-node lifecycle (NDEATH-as-LWT, NBIRTH seq=0 + bdSeq, NDATA seq 0–255 wrap, NCMD `Node Control/Rebirth` →
  re-NBIRTH, NDEATH), every payload **HMAC-SHA-384** MAC'd (`backend/crypto/hmac_sha384.py`), inbound MAC-verified.
- **ISA-95 population** (`backend/memory/graph_isa95.py::populate_from_ot_event`): inbound OPC UA datachanges +
  Sparkplug DBIRTH/DDATA MERGE Equipment nodes under a WorkCenter (idempotent; honest-unavailable without Neo4j).

**Verified live:** OPC UA server↔client roundtrip + subscription over real loopback TCP; the full Sparkplug B
lifecycle over a real **Mosquitto** broker (NBIRTH seq0+bdSeq, NDATA seq1, NCMD-Rebirth → NBIRTH seq0, NDEATH);
HMAC tamper/wrong-key rejected; ISA-95 population over real Neo4j — **8 integration tests pass** (`tests/integrations/`).
CI gate `opcua-sparkplug-integration` (Mosquitto service). New deps: `asyncua==1.1.5`, `grpcio-tools==1.62.3`
(build-time protoc; protobuf pinned `<5` for TF-2.15 safety — research §25.4). Actuator/write paths (VDA 5050 orders @16,
PLC writes + `safety.validate` gate @17) remain out of scope (KB_17). ADR `2026-06-20_stage15_ot_it_bridge.md`.

Prior: 2026-05-18 — documented the intent/contract before any `backend/integrations/` code existed.
