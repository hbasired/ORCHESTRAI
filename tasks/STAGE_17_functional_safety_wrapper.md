---
status: done
stage: 17
slug: functional_safety_wrapper
created: 2026-05-18
---

# Stage 17 — Functional Safety Wrapper

> LLM-as-planner / SIL-rated-classical-controller-as-executor. Pydantic safety contract DSL. STO / SS1 paths. CI gate fails any actuator test without a preceding `safety.validate` span. See KB_17.

## Pre-requisites

- Stage 16 closed (actuator surfaces exist — VDA 5050 orders, OPC UA writes, Sparkplug DCMD).
- Stage 12.5 closed (OpenTelemetry spans wired).

## Acceptance criteria

- [ ] (CTO remediation) Adopt a NAMED zero-trust framework (CSA Agentic Trust / NIST SP 800-207 / OWASP Top-10 Agentic) and issue a per-internal-agent ML-DSA-65 identity (today only the single agent-identity alias signs ADRs/audit/cards; internal agents/tools are unsigned); scope MCP tools to per-tool capability authz + argument sanitisation + a signed tool manifest + rate-limiting; bind the A2A interim X-A2A-Peer-Key gate to real mTLS client-cert->peer_state (G-063/G-064)

- [ ] `backend/safety/contract.py` defines the safety-contract DSL (per KB_17 §"Safety contract DSL").
- [ ] `backend/safety/validator.py` implements `validate(action, world_state, contract) -> Decision`.
- [ ] `backend/safety/sil_bridge.py` implements PLC / safety-controller bridge (OPC UA Safety profile or PROFIsafe placeholder).
- [ ] `backend/safety/sto_ss1.py` implements `trigger_sto()`, `trigger_ss1(deceleration_profile)`.
- [ ] At least 5 safety contracts defined: `move_amr_to_charging_station`, `start_conveyor_segment`, `expedite_supplier_order` (SIL 0 demo), `change_machine_state`, `dispatch_amr_to_zone`.
- [ ] `backend/safety/sil_pl_map.py` maps IEC 61508 SIL ↔ ISO 13849-1 PL.
- [ ] `scripts/check-safety-trace-pairing.py` — parses traces; fails CI if any `actuator.*` span lacks a preceding `safety.validate.*` span.
- [ ] CI gate `safety-contract-tests` runs on every PR.
- [ ] `pytest backend/tests/safety/ -v` green (contract conformance, validator decisions, STO/SS1 round-trip, ISO/TS 15066 speed/force).
- [ ] LangGraph runtime structurally separates planning nodes from execution nodes; execution nodes are the only callers of `sil_bridge.py`.
- [ ] Every STO/SS1 trigger writes an `audit_chain` row (signed ML-DSA-65).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/safety/__init__.py` | Package marker |
| `backend/safety/contract.py` | Pydantic safety-contract DSL |
| `backend/safety/validator.py` | Pre-flight validator |
| `backend/safety/sil_bridge.py` | PLC bridge (OPC UA Safety / PROFIsafe placeholder) |
| `backend/safety/sto_ss1.py` | Emergency stop paths |
| `backend/safety/sil_pl_map.py` | SIL ↔ PL routing |
| `backend/safety/contracts/*.py` | Per-action safety contracts |
| `backend/tests/safety/test_validator_decisions.py` | Validator pass/fail matrix |
| `backend/tests/safety/test_iso15066.py` | Speed/force/separation limits |
| `backend/tests/safety/test_sto_ss1.py` | Emergency stop round-trip |
| `backend/tests/safety/test_trace_pairing.py` | Asserts safety→actuator span pairing |
| `scripts/check-safety-trace-pairing.py` | CI gate trace parser |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/agents/runtime/graph.py` | Execution nodes call `validator.validate()` before any actuator dispatch |
| `backend/integrations/vda5050/master.py` | Route every `order` through validator |
| `backend/integrations/opcua/client.py` | Route every write through validator |
| `backend/integrations/sparkplug/client.py` | Route every DCMD through validator |
| `.github/workflows/ci.yml` | Add `safety-contract-tests` + `safety-trace-pairing` jobs |
| `compliance/risk-register.md` | Functional-safety bypass row marked implemented |
| `knowledge-base/KB_17_Functional_Safety_Wrapper.md` | Confirm spec matches implementation |

## KB files this stage updates

- `KB_17_Functional_Safety_Wrapper.md`
- `KB_12_Standards_Map.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
cd backend && pytest tests/safety/ -v
python scripts/check-safety-trace-pairing.py audits/STAGE_17_traces.json
```

## Audit target

- Strict decrease (and crucially, zero new actuator paths without `safety.validate.*` pairing — CI enforces).

## Role

- Primary: `robotics-integration-engineer`
- Secondary: `agentic-governance-engineer` (ADR for SIL routing decisions), `compliance-engineer` (ISO 10218 evidence collation)

## Risks / unknowns

- PROFIsafe / OPC UA Safety profile integration depends on customer's certified PLC; `sil_bridge.py` is the integration point, not a replacement.
- PRD v2 carefully says the wrapper makes the system *amenable* to certification; actual TÜV/notified-body certification is Stage 23 + external assessor.

## Hand-off

- What is now true: no actuator path can be invoked without passing through `safety.validator`; CI enforces.
- Next stage (18) hardens PQC across all external boundaries.
