"""Stage 15 — OT/IT bridge: open-standards integration between the agent control plane and customer OT/IT.

Sub-packages:
- `opcua/`      — OPC UA (asyncua) ISA-95 server + telemetry-subscription client.
- `sparkplug/`  — MQTT Sparkplug B v3.0 (real protobuf payload + birth/death/data lifecycle), HMAC-SHA-384 MAC'd.

Inbound OPC UA datachanges + Sparkplug DBIRTH/DDATA metrics populate the Stage-12 ISA-95 Neo4j graph
(`backend/memory/graph_isa95.py`). This layer is telemetry/read + graph population only — actuator command paths
(VDA 5050 orders @16, PLC writes / safety wrapper @17) are out of scope here (KB_17).
"""
