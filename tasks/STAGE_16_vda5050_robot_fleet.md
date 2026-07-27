---
status: done
stage: 16
slug: vda5050_robot_fleet
created: 2026-05-18
---

# Stage 16 — Robot Fleet Adapter (VDA 5050 v2.1.0 Master Controller)

> Master controller for multi-vendor AGV / AMR fleets. Speaks VDA 5050 v2.1.0 over MQTT (`uagv/v2/<manufacturer>/<sn>/{order,state,instantActions,factsheet,visualization,connection}`). JSON schemas pinned from VDA reference repo.

## Pre-requisites

- Stage 15 closed (MQTT Sparkplug B broker operational).

## Acceptance criteria

- [ ] (CTO remediation) Prove the Groq->Ollama free-cost LLM fallback LIVE on a path that actually invokes an LLM (the self-healing runtime loop is LLM-free, so the fallback is code-real but run-unproven; NL-injection / 'ask the factory' G-022/G-023 are where it runs) — closes the long-standing CTO #1 #5 / CTO #2 R5 'prove it is real'

- [ ] (CTO remediation) Wire the runtime graph to consume the mounted MCP StructuredTools for at least one node (route model/tool calls through MCP rather than direct Python import) so runtime decisions are genuinely MCP-mediated (G-059, OPEN through Stages 11.5/12/14)

- [ ] VDA 5050 v2.1.0 JSON schemas committed under `backend/integrations/vda5050/schemas/`.
- [ ] Pydantic models generated from schemas via `datamodel-code-generator` in CI (build step).
- [ ] `backend/integrations/vda5050/master.py` subscribes to `+/+/state`, `+/+/connection`, `+/+/visualization`, `+/+/factsheet`; publishes to `+/+/order`, `+/+/instantActions`.
- [ ] Master controller verifies `connection` freshness before any `order` dispatch (anti-spoof per risk register).
- [ ] Every actuator-bound action routes through `backend/safety/validator.py` (Stage 17 — wired stub for now; full validator Stage 17).
- [ ] `pytest backend/tests/integrations/test_vda5050_schema.py` validates canned `order` + `state` payloads against pinned VDA reference fixtures.
- [ ] `pytest backend/tests/integrations/test_vda5050_master.py` — master controller dispatches valid `order` to a simulated AGV and receives `state` updates.
- [ ] CI gate `vda5050-schema-validate` enforces schema conformance.
- [ ] MCP tool `policy_query.recommend_action` returns VDA 5050-shaped actions when fleet routing is appropriate.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/integrations/vda5050/__init__.py` | Sub-package marker |
| `backend/integrations/vda5050/master.py` | Master controller |
| `backend/integrations/vda5050/topics.py` | MQTT topic schema |
| `backend/integrations/vda5050/schemas/*.json` | Pinned v2.1.0 JSON schemas |
| `backend/integrations/vda5050/models.py` | Generated Pydantic models (or generation hook) |
| `backend/tests/integrations/test_vda5050_schema.py` | Schema validation tests |
| `backend/tests/integrations/test_vda5050_master.py` | Master dispatch tests |
| `backend/tests/fixtures/vda5050/` | Canned payloads from VDA reference |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/mcp_servers/policy_query_server.py` | Emit VDA 5050-shaped fleet actions |
| `backend/requirements.txt` | Add `datamodel-code-generator` (dev dep) |
| `.github/workflows/ci.yml` | Add `vda5050-schema-validate` job + Pydantic model generation step |
| `compliance/risk-register.md` | Mark VDA 5050 spoofing row as implemented |

## KB files this stage updates

- `KB_12_Standards_Map.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
python -m datamodel_code_generator --input backend/integrations/vda5050/schemas/ --output backend/integrations/vda5050/models.py
cd backend && pytest tests/integrations/test_vda5050* -v
```

## Audit target

- Strict decrease.

## Role

- Primary: `robotics-integration-engineer`

## Hand-off

- What is now true: multi-vendor robot fleets can connect via VDA 5050; payloads schema-validated.
- Next stage (17) adds the functional safety wrapper — every actuator-bound VDA 5050 `order` will pass through the validator.
