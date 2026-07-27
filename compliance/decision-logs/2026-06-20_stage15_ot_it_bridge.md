# ADR — Stage 15: OT/IT bridge (OPC UA + MQTT Sparkplug B v3.0 + ISA-95 population)

**Date**: 2026-06-20
**Status**: Accepted (Stage 15 — follows Stage 14.5 CTO Checkpoint #3)
**Author personas**: `robotics-integration-engineer` (primary) + `agentic-governance-engineer` (CTO remediations)
**Relates**: KB_12 (standards), KB_14 (memory/ISA-95), KB_13 (PQC/HMAC), KB_17 (safety boundary). Research §25.
Hard Rule 1a (real protobuf + real broker, no theatre), Rule 9 (free/local OSS), Rule 11 (research-first + deepest
honest path), Rule 2 (HMAC-SHA-384 quantum-resistant MAC, no classical signatures in new crypto use).

---

## Context

After the internal control plane (Stages 11–14: runtime + MCP + memory + observability + CDC + PQC + A2A), Stage 15
opens the **open-standards bridge to the customer's existing OT/IT**: OPC UA (the IIoT telemetry standard) + MQTT
Sparkplug B v3.0 (the IIoT pub/sub standard) feeding the Stage-12 ISA-95 Neo4j graph. Telemetry/read + graph
population only — actuator command paths (VDA 5050 orders @16, PLC writes + the `safety.validate` gate @17) are
deliberately out of scope (KB_17).

## Decisions

**D1 — Real Sparkplug B protobuf, hand-built lifecycle (NOT mqtt-spb-wrapper) (research §25.1/25.2).** The canonical
Eclipse `sparkplug_b.proto` is committed + compiled to `sparkplug_b_pb2.py` (build-time `grpcio-tools` protoc; runtime
needs only `protobuf`). `sparkplug/payload.py` builds/parses spec-conformant payloads (typed metric oneofs, datatype
inference); `sparkplug/client.py` implements the full edge-node lifecycle with **correct seq/bdSeq accounting**:
NDEATH registered as the MQTT **Last-Will** at CONNECT (carrying `bdSeq`); **NBIRTH** right after CONNECT (seq=0, same
`bdSeq`, `Node Control/Rebirth`); **seq** 0–255 wrapping on every subsequent message; inbound **NCMD Rebirth** →
re-NBIRTH. Hand-built (not mqtt-spb-wrapper) for full control over seq/bdSeq + no maintenance/pin risk — the deepest
honest path (real wire format, real lifecycle).

**D2 — HMAC-SHA-384 payload integrity (Rule 2 / KB_13).** Every Sparkplug payload carries an HMAC-SHA-384 tag (a
`MAC/HMAC-SHA384` metric) computed over the canonical payload-with-tag-cleared (`backend/crypto/hmac_sha384.py`);
inbound payloads are MAC-verified, bad MAC → dropped. Quantum-resistant symmetric MAC (the right primitive for the OT
bus per KB_13; not a PQC signature).

**D3 — OPC UA via asyncua; ISA-95 tree; subscribe-only.** `opcua/server.py` exposes an ISA-95 Part-2 object tree with
live telemetry vars; `opcua/client.py` browses + reads + subscribes (data-change → callback). Interim security policy
**Aes256Sha256RsaPss**, armed only when certs are loaded (`secure_policy_enabled()` reports honestly; certless
`NoSecurity` for the in-process roundtrip). PQC overlay = Stage 18 (KB_13). The client is **subscribe-only** (no
writes to external servers — the write/actuator path is the Stage-17 safety wrapper, KB_17).

**D4 — ISA-95 graph population.** `graph_isa95.populate_from_ot_event()` MERGEs Equipment nodes (under a WorkCenter)
from inbound OPC UA datachanges + Sparkplug DBIRTH/DDATA (idempotent; honest-unavailable without Neo4j).

**D5 — Dependency tension resolved (research §25.4).** `grpcio-tools` 1.81 pulls protobuf 6.x which **breaks
TensorFlow 2.15** (dice-ml/Stage 10, needs `protobuf<5`). Pinned **grpcio-tools 1.62.3 + protobuf `>=4.25,<5.0`** — a
protoc that emits protobuf-4.x code, TF-safe; the OTLP serialize path verified still working at 4.25.9.

**D6 — CTO #3 remediations folded in (this stage's ACs).** (R2) Risk-register **refreshed** — added rows for the A2A
interim-unauthenticated gate (G-064), the legacy placeholder-sha256 rows + the `verify-audit-chain.py` signature-verify
gap (G-073), A2A trace blindness (G-074), and the Stage-15 OT surfaces; `Last reviewed` updated. (R1) The formal
**different-agent independent review of Stage 12** (owed as **G-062**) was run → `audits/STAGE_12_independent_review.md`.
Also corrected (Rule 1a) the residual "verify-audit-chain verifies sigs end-to-end" overclaim in KB_14 + the ledger.

## Why
- OPC UA + Sparkplug B are THE open standards the wedge (warehouse/discrete-manufacturing) OT speaks; honest depth here
  (real protobuf, real broker lifecycle, real HMAC, real ISA-95 graph) is the credibility difference vs a mock bridge.
  Subscribe-only + HMAC + the safety-path deferral keep the boundary safe before the Stage-17 wrapper exists.

## Consequences
- New: `backend/integrations/{__init__, opcua/{__init__,server,client}, sparkplug/{__init__,payload,client,
  sparkplug_b.proto,sparkplug_b_pb2,compile_proto.sh}}`; `backend/tests/integrations/` (4 files, 8 tests); CI gate
  `opcua-sparkplug-integration` (Mosquitto service). Modified: `backend/memory/graph_isa95.py`
  (`populate_from_ot_event`), `requirements.txt` (asyncua, grpcio-tools, protobuf pin), KB_12/KB_14, risk-register.
- New deps: `asyncua==1.1.5` (runtime), `grpcio-tools==1.62.3` (build-time), protobuf pinned `>=4.25,<5.0`.
- Verified live (Docker up): OPC UA server↔client roundtrip + subscription over real loopback TCP; full Sparkplug B
  lifecycle over a real **Mosquitto** broker (NBIRTH seq0+bdSeq → NDATA seq1 → NCMD-Rebirth → NBIRTH seq0 → NDEATH);
  HMAC tamper + wrong-key rejected; ISA-95 population over real Neo4j — **8 integration tests pass**. `main.py` imports
  clean. Audit holds **364** (additive real integration code; no grep-visible theatre to remove — `--no-baseline-drop`).

## Honest residual / ledger
- Actuator/write paths (VDA 5050 orders, PLC writes) + the `safety.validate` span gate = Stage 16/17 (KB_17).
- Live OPC UA mTLS certs (Aes256Sha256RsaPss armed) + broker mTLS + the PQC overlay (ML-KEM/ML-DSA cert chain) = Stage 18.
- The Neo4j-gated ISA-95 population tests skip without Neo4j (CI has no Neo4j service here; covered in memory/full runs).

## References
- `backend/integrations/**` · `backend/memory/graph_isa95.py` · `backend/tests/integrations/**` ·
  `.github/workflows/ci.yml` (opcua-sparkplug-integration) · `docker/docker-compose.yml` (Mosquitto). KB_12/13/14/17.
  Research §25. Eclipse Sparkplug B v3.0.0 spec; FreeOpcUa/opcua-asyncio.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:31+00:00 -->
<!-- signature: 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 -->
