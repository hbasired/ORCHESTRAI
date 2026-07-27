# ADR — Stage 17: Functional safety wrapper + agentic zero-trust (G-063/G-064) + self-healing

**Date**: 2026-06-21
**Status**: Accepted (Stage 17 — follows Stage 16 VDA 5050)
**Author personas**: `robotics-integration-engineer` (primary) + `agentic-governance-engineer` (zero-trust) + `compliance-engineer` (ISO mapping)
**Relates**: KB_17 (safety wrapper), KB_13 (PQC), KB_16 (MCP). Research §27. Hard Rule 1a (real gates, honest
deferrals), Rule 9 (free/local), Rule 11 (research-first), Rule 2 (ML-DSA-65, no classical), Rule 3 (no LLM-direct actuator).

---

## Context

After the actuator surfaces exist (Stage 16 VDA 5050 orders), Stage 17 builds the **functional safety wrapper** (KB_17:
LLM-planner / SIL-rated-classical-executor / formal-contract gate) so no actuator path can be invoked without passing
the validator, pays the CTO #3 **zero-trust** remediation (G-063/G-064), and adds the KB_17 **self-healing** extension.

## Decisions

**D1 — Safety-contract DSL + SIL-routing validator (KB_17; research §27.1).** `safety/contract.py` (Pydantic
Precondition/Invariant/Postcondition/SafetyContract/Action/Decision); `safety/contracts/` (the 5 named contracts with
real checks); `safety/validator.py::validate(action, world_state, contract) -> Decision` — precondition+invariant gate
→ **SIL routing** (SIL≥2→`sil_bridge`, SIL 1→`operator_confirm`, SIL 0→`direct`); a failed/raising check BLOCKS
(fail-safe), records a signed `audit_chain` row, names the contract's `fail_safe_path`. `sil_pl_map.py` (IEC 61508 SIL
↔ ISO 13849-1 PL; ISO 10218-1:2025 PL d/SIL 2 Class II).

**D2 — `sil_bridge` is the only actuator emitter + no bypass.** `safety/sil_bridge.py::execute()` is the ONLY emitter
of `actuator.*` spans and **refuses any non-allowing / mis-routed Decision** (defence-in-depth — even a caller that
skipped the gate is rejected). It is the **integration point** for the customer's certified PLC (OPC UA Safety /
PROFIsafe) — NOT a replacement (no SIL cert claimed; cert = Stage 23 + assessor). `safety/sto_ss1.py` — STO/SS1
(IEC 61800-5-2); every trigger writes a signed `audit_chain` row (best-effort: safety is never blocked by an audit outage).

**D3 — Trace-pairing as a hard CI invariant.** `scripts/check-safety-trace-pairing.py` fails CI if any `actuator.*`
span lacks a preceding `safety.validate.*` span. Wired on the VDA dispatch (`master.dispatch_order` emits
`actuator.vda5050.order` after `validate_order`) + the runtime `execute` node (routes through `validate()`). CI gate
`safety-contract-tests`.

**D4 — CTO #3 zero-trust (G-063/G-064; research §27.2).** `backend/security/`: adopted **NIST SP 800-207** (+ CSA
Agentic Trust / MAESTRO / OWASP NHI) with the 5 pillars mapped (`zero_trust.py`); **per-internal-agent ML-DSA-65
non-human identity** extending the Stage-13.5 KeyProvider beyond the single org alias (`agent_identity.py`); MCP tool
**least-privilege capability authz + argument sanitisation + rate-limiting** (`mcp_authz.py`) + an **ML-DSA-65 signed
tool manifest** that detects a rogue/injected tool (`tool_manifest.py`); composed in `ZeroTrustGateway`. The A2A interim
`X-A2A-Peer-Key` gate → live mTLS-client-cert→`peer_state` binding (Network pillar) is **Stage 18** (KB_13) —
honestly deferred. Fixed a cross-platform keystore bug en route (alias `:` invalid as a Windows dir name → sanitised).

**D5 — Self-healing (KB_17 extension; research §27.3).** `safety/self_healing/`: a robust rolling-Z joint-torque
anomaly detector (>3σ) → a YAML behaviour-tree (`amr.yaml` + `manipulator.yaml`) `self_diagnose_calibrate` routine →
resume (the resume action ITSELF passes `validator.validate()` — we never skip safety during self-repair) OR, on
calibration failure, **STO + quarantine**; every transition writes a signed `audit_chain` row. KubeEdge pod-healing =
KB_21 / Stage 21+ (out of scope).

## Why
- Rule 3 (no LLM-direct actuator) becomes a *mechanically enforced* invariant (the trace-pairing CI gate), not a
  convention — this is what makes the system amenable to certification. The zero-trust pillars give each agent a
  verifiable identity + least-privilege tool access, shrinking a compromised/rogue agent's blast radius (NIST SP 800-207).

## Consequences
- New: `backend/safety/{contract,validator(+),sil_bridge,sto_ss1,sil_pl_map}.py` + `safety/contracts/` +
  `safety/self_healing/{torque_anomaly,behavior_tree,self_repair}.py` + `behavior_trees/{amr,manipulator}.yaml`;
  `backend/security/{zero_trust,agent_identity,mcp_authz,tool_manifest}.py`; `scripts/check-safety-trace-pairing.py`;
  `backend/tests/{safety,security}/` (6 files); CI gate `safety-contract-tests`; `audits/STAGE_17_traces.json` (sample).
  Modified: `agents/runtime/nodes.py` (execute → validator), `integrations/vda5050/master.py` (actuator span),
  `crypto/software_provider.py` (alias→dir sanitisation), KB_17/KB_12, risk-register.
- New deps: **none** (scikit-learn + pyyaml + jcs already present).
- Verified live: `tests/safety/` + `tests/security/` **33 pass**; runtime canned-decision **7 pass** (execute now
  validator-gated); crypto+vda regression **13 pass**; trace-pairing gate OK; audit holds **364**.

## Honest residual / ledger
- No SIL certification (architecture amenable only); `sil_bridge` is the certified-PLC integration point (no real PLC here).
- A2A live mTLS-client-cert→peer_state binding + device/workload attestation = **Stage 18** (the ZT Network/Device pillars).
- The self-repair `calibrate_fn`/`dock_fn` are injectable hooks (no physical robot here) — the orchestration, safety
  gating, STO, and audit trail are real; the physical calibration is wired to the robot routine in deployment.

## References
- `backend/safety/**` · `backend/security/**` · `scripts/check-safety-trace-pairing.py` · `backend/tests/{safety,security}/**`
  · `backend/agents/runtime/nodes.py` · `backend/integrations/vda5050/master.py` · `.github/workflows/ci.yml`. KB_17/13/16.
  Research §27. ISO 13849-1:2023 / IEC 61508 / ISO 10218-1/2:2025 / ISO/TS 15066; NIST SP 800-207 + CSA Agentic Trust.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:32+00:00 -->
<!-- signature: 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 -->
