# ADR — Stage 16: VDA 5050 v2.1.0 robot-fleet master controller (+ CTO #3 R3/R11)

**Date**: 2026-06-20
**Status**: Accepted (Stage 16 — follows Stage 15 OT/IT bridge)
**Author personas**: `robotics-integration-engineer` (primary) + `backend-engineer` (CTO remediations)
**Relates**: KB_12 (standards), KB_17 (safety boundary), KB_16 (MCP), KB_25 (self-healing → fleet actuation).
Research §26. Hard Rule 1a (real schemas + real broker, no theatre), Rule 9 (free/local), Rule 11 (research-first +
deepest honest path), Rule 2 (no classical signatures in new crypto use).

---

## Context

After the OT/IT bridge (Stage 15: OPC UA + Sparkplug B + ISA-95), Stage 16 adds the **multi-vendor AGV/AMR fleet
boundary** — a **VDA 5050 v2.1.0** master controller over MQTT — and pays two CTO #3 remediations: R3/**G-059** (route
a runtime decision through MCP, not a direct import) and R11 (prove the Groq→Ollama free-cost LLM fallback live).

## Decisions

**D1 — Real upstream v2.1.0 schemas + generated models (research §26.2).** The 6 official JSON schemas
(order/state/connection/instantActions/factsheet/visualization) are vendored verbatim from `github.com/VDA5050/VDA5050`
at git **tag `2.1.0`** (MIT) — NOT `main` (which is **v3.0.0**: v3 `state` uses `powerSupply` vs v2.1.0 `batteryState`;
caught during fixture validation + corrected in the provenance/research notes, Rule 1a). Pydantic `models/` are
**generated** by `datamodel-code-generator`; payloads validate against the real schemas with `jsonschema`.

**D2 — Hand-rolled master over paho-mqtt (research §26.5).** No mature free Python VDA-5050 *master* library
(coaty's is JS + v1.1). `Vda5050Master` subscribes to the AGV→master topics, maintains a per-AGV registry, and
dispatches order/instantActions. **Anti-spoof gate (risk register):** `dispatch_order` REFUSES (no publish) unless the
AGV `connection` is **ONLINE + fresh** (within a freshness window) — verified over a real broker (a stale/ghost AGV
gets nothing).

**D3 — Safety gate now, SIL validator at 17 (KB_17).** Every dispatch routes through `backend/safety/validator.py`,
which performs **structural well-formedness + connection-freshness** checks and emits the **`safety.validate`** span
(the CI invariant: a `safety.validate` span precedes every actuator span). Honest scope: this is the Stage-16 gate,
NOT the SIL-rated contract-DSL validator + STO/SS1 (Stage 17). `validate_order(...).allowed == False` blocks dispatch.

**D4 — policy_query → VDA bridge.** `policy_query_server.recommend_action` returns VDA-5050-shaped routing
(`vda5050_routing`: nodes/edges with pick/drop actions) when the telemetry carries a `fleet` block — `master.build_order`
turns it into a schema-valid order (still gated by D2/D3). `integrations/vda5050/actions.py::recommend_fleet_order`.

**D5 — CTO #3 R3 / G-059: MCP-mediated runtime decision.** The runtime `orient` node routes its Stage-4 failure
prediction through `model_inference_server.predict_failure` over **MCP stdio** (a real subprocess round-trip via the
Stage-11.5 `call_mcp_tool`) when `RUNTIME_MCP_MEDIATED=1` — so the decision is genuinely MCP-mediated, not a direct
Python import. Honest: an MCP *transport* failure falls back to the direct import (resilience, traced); a model
honest-unavailable is surfaced, never faked. Verified live (2 tests): with the flag the orient trace shows
`mediation=mcp:model_inference_server.predict_failure` + a real at-risk prediction.

**D6 — CTO R11: Groq→Ollama fallback, proven LIVE.** `agents/llm_client.py` already had the fallback logic; R11 was
"prove it is real." A **real local Ollama** (Docker, free) with a tiny model + a test that forces Groq to fail proves
the client switches to Ollama and returns real content (`provider == "ollama"`); a sibling test proves all-providers-
failing raises (no fabricated response). Free-cost (Rule 9). Closes the long-standing CTO #1 #5 / CTO #2 R5.

## Why
- VDA 5050 is THE open robot-fleet standard; honest depth (real v2.1.0 schemas, real broker dispatch, the anti-spoof +
  safety gates) is the credibility difference vs a mock adapter. G-059 makes the "MCP-mediated runtime" claim true for
  the first time (it was OPEN through Stages 11.5/12/14). R11 finally proves the free-cost LLM resilience is real.

## Consequences
- New: `backend/integrations/vda5050/{__init__,topics,master,actions,compile_models.sh,SCHEMAS_PROVENANCE.md,
  schemas/*.json,models/*}`, `backend/safety/{__init__,validator}.py`, `backend/tests/integrations/test_vda5050_{schema,
  master}.py` + `tests/fixtures/vda5050/*`, `backend/tests/agents/runtime/test_stage16_remediations.py`, CI gates
  `vda5050-schema-validate` (+ split the opcua-sparkplug job). Modified: `agents/runtime/nodes.py` (MCP-mediated orient),
  `mcp_servers/policy_query_server.py` (VDA routing), `requirements.txt` (datamodel-code-generator), KB_12, risk-register.
- New deps: `datamodel-code-generator` (build-time/dev). No runtime deps added (paho-mqtt/jsonschema already present).
- Verified live (Docker up): 12 VDA schema/master tests (incl. real-Mosquitto dispatch roundtrip + anti-spoof) +
  2 G-059 MCP-mediation tests pass; audit holds **364**; `main.py` imports clean.

## Honest residual / ledger
- The SIL-rated contract-DSL validator + STO/SS1 + the `safety.validate`-before-actuator CI enforcement = **Stage 17**
  (the Stage-16 validator is a structural+freshness gate). Broker mTLS + live OPC-UA/VDA PQC cert chain = **Stage 18**.
- The real-broker VDA dispatch test + the Ollama R11 test are infra-gated (skip without Mosquitto / a local Ollama).

## References
- `backend/integrations/vda5050/**` · `backend/safety/validator.py` · `backend/agents/runtime/nodes.py` ·
  `backend/mcp_servers/policy_query_server.py` · `backend/tests/integrations/test_vda5050_*` ·
  `backend/tests/agents/runtime/test_stage16_remediations.py` · `.github/workflows/ci.yml`. KB_12/16/17/25. Research §26.
  VDA 5050 v2.1.0 spec (vda.de); VDA5050 GitHub (tag 2.1.0, MIT).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:32+00:00 -->
<!-- signature: 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 -->
