---
status: done
stage: 15
slug: ot_it_bridge
created: 2026-05-18
---

# Stage 15 — OT/IT Bridge (OPC UA + MQTT Sparkplug B + ISA-95 Graph)

> Open-standards bridge between the agent control plane and the customer's existing OT/IT systems. OPC UA (asyncua) + MQTT Sparkplug B v3.0 (paho-mqtt + mqtt-spb-wrapper) + ISA-95 Part 2 object model mapped into Neo4j (Stage 12's graph).

## Pre-requisites

- Stages 12 (Neo4j ISA-95 graph) + 13.5 (HMAC-SHA-384 helper) closed.

## Acceptance criteria

- [ ] (CTO remediation) Refresh compliance/risk-register.md AT THIS CTO checkpoint (cadence unmet, last-reviewed 2026-06-15): add rows for the A2A interim-unauthenticated capability gate, the 79 legacy placeholder-sha256 audit_chain rows, the verify-audit-chain.py signature-check gap (G-073), and A2A trace blindness (G-074); update Last-reviewed

- [ ] (CTO remediation) Run the owed FORMAL different-agent independent review of Stage 12 (scripts/independent-audit.sh 12) now that fresh-agent tooling works; its dynamic verification is done, only the different-agent judgement is owed (G-062)

- [ ] `backend/integrations/opcua/server.py` exposes ISA-95 nodes via OPC UA.
- [ ] `backend/integrations/opcua/client.py` pulls telemetry from external OPC UA servers (test against open-source test server).
- [ ] OPC UA Security Policy: `Aes256_Sha256_RsaPss` interim. PQC overlay tracked in KB_13 for Stage 18.
- [ ] `backend/integrations/sparkplug/payload.py` implements Sparkplug B v3.0 protobuf payload (or wraps `mqtt-spb-wrapper`).
- [ ] `backend/integrations/sparkplug/client.py` implements full birth/death/data/NCMD/DCMD lifecycle with correct SeqNum / bdSeq accounting.
- [ ] Sparkplug B payloads MAC'd with HMAC-SHA-384 from `backend/crypto/hmac_sha384.py`.
- [ ] ISA-95 graph populated from inbound OPC UA + Sparkplug B events.
- [ ] `pytest backend/tests/integrations/ -v` green; coverage includes cert rotation, broker mTLS, Sparkplug birth/death sequence.
- [ ] CI gate `opcua-sparkplug-integration` runs on every PR (uses a Mosquitto test broker + open OPC UA server in CI).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/integrations/__init__.py` | Package marker |
| `backend/integrations/opcua/__init__.py` | Sub-package marker |
| `backend/integrations/opcua/server.py` | ISA-95 OPC UA server |
| `backend/integrations/opcua/client.py` | OPC UA client/subscription |
| `backend/integrations/sparkplug/__init__.py` | Sub-package marker |
| `backend/integrations/sparkplug/payload.py` | Sparkplug B v3.0 payload schema |
| `backend/integrations/sparkplug/client.py` | Sparkplug B node/device client |
| `backend/tests/integrations/test_opcua_roundtrip.py` | Server-client roundtrip |
| `backend/tests/integrations/test_sparkplug_lifecycle.py` | Birth/death/data sequence |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/memory/graph_isa95.py` | Populate from OPC UA + Sparkplug B events |
| `backend/requirements.txt` | Add `asyncua`, `paho-mqtt` (already pinned), `mqtt-spb-wrapper` |
| `docker/docker-compose.yml` | Mosquitto already present; add open OPC UA test server for CI |
| `compliance/risk-register.md` | Update OPC UA cert chain + VDA 5050 spoofing rows |

## KB files this stage updates

- `KB_12_Standards_Map.md`
- `KB_14_Agent_Memory_Architecture.md` (Neo4j graph now populated)
- `KB_TASK_LOG.md`

## Verification commands

```bash
docker compose up -d
cd backend && pytest tests/integrations/ -v
```

## Audit target

- Strict decrease.

## Role

- Primary: `robotics-integration-engineer`

## Hand-off

- What is now true: OT/IT systems can publish to and read from the agent control plane via open standards; ISA-95 graph populated.
- Next stage (16) adds the VDA 5050 robot fleet adapter on top of the OT layer.
