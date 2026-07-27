"""Stage 16 — VDA 5050 v2.1.0 robot-fleet master controller (multi-vendor AGV/AMR over MQTT).

`models/` are GENERATED from the official upstream JSON schemas (`schemas/`, MIT — see SCHEMAS_PROVENANCE.md).
`topics.py` builds/parses the `uagv/v2/<manufacturer>/<serial>/<topic>` namespace. `master.py` is the master
controller: subscribes to AGV→master topics (state/connection/visualization/factsheet), publishes master→AGV topics
(order/instantActions), and verifies `connection` freshness before any order dispatch (anti-spoof). Every actuator-bound
dispatch routes through `backend/safety/validator.py` (a structural+freshness stub now; the SIL-rated validator is Stage 17).
"""
