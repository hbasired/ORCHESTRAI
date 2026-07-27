# ISO 10218-2:2025 Risk Assessment — Agent Control Plane (Stage 23 dry-run)

> Risk assessment for the integration of this AI agent control plane into an industrial robot application / robot cell,
> following **ISO 10218-2:2025 §6** (which now absorbs ISO/TS 15066 for collaborative workspaces). Research §33.2.
> **Scope boundary (honest):** we are the **agent decision/actuation-gate layer**, NOT the robot OEM or the cell
> integrator. The integrator owns the *complete robot system* risk assessment (ISO 10218-2 §6); this document covers the
> hazards our layer can introduce or mitigate, and how the Stage-17 functional-safety wrapper is the risk-reduction
> measure at the AI→actuator boundary. Pairs with `compliance/dr-runbook.md` + `compliance/pilot-deployment-runbook.md`.

## 1. Method (ISO 12100 / ISO 10218-2 §6)

Identify significant **hazards → hazardous situations → hazardous events** for **intended use AND reasonably foreseeable
misuse**, across the lifecycle (design → integration → commissioning → operation → maintenance → decommissioning); assess
risk (severity × probability × avoidance); apply the 3-step risk-reduction hierarchy (inherently-safe design → safeguarding
→ information for use); re-assess residual risk. SIL/PL per IEC 61508 / ISO 13849-1 (the Stage-17 `sil_pl_map`).

## 2. Hazard catalogue (AI-layer-introduced or AI-layer-mitigated)

| # | Hazard / hazardous event | Lifecycle phase | Cause | Risk-reduction measure (in this system) | Residual |
|---|---|---|---|---|---|
| H1 | Unsafe actuator command reaches the robot (LLM-driven action) | operation | An agent/LLM emits an actuation that violates a safety constraint | **Inherent:** no LLM-direct actuator (Rule 3). **Safeguard:** every `actuator.*` is gated by `safety/validator.validate()` (SIL routing) + emitted only by `sil_bridge`; CI trace-pairing invariant fails any unpaired actuator span | Low — gated; G-075 first-real-PLC hardening pending (pilot §4) |
| H2 | Actuation on stale/incorrect world state (TOCTOU) | operation | A decision acts on out-of-date telemetry | Validator re-checks pre/observations; VDA `connection` ONLINE+fresh check before dispatch (Stage 16); G-075 self-validation from contract+world_state | Low-Med — fully load-bearing at first real PLC caller |
| H3 | Robot dispatched to an offline/ghost AGV | operation | Spoofed/stale `state`/`connection` | `Vda5050Master` verifies connection fresh + routes through validator; Sparkplug payloads HMAC-SHA-384 (Stage 15) | Low |
| H4 | Collaborative-workspace contact exceeds biomechanical limits (ISO/TS 15066) | operation (HRC) | Speed/force above the power-and-force limit | The agent layer does NOT set robot speed/force — that is the cell's safety-rated control (integrator). Our layer's `safety_disable`/`speed_limit` red-team patterns + validator refuse commands that *request* exceeding limits | Integrator-owned; our layer refuses unsafe requests |
| H5 | Loss of human oversight on a SIL-1+ action | operation | Autonomy without approval | HITL gate (`runtime/hitl.py`) pauses SIL-1+ decisions for operator approval (Stage 17); Art-14 oversight | Low |
| H6 | Maintenance performed on a live line (LOTO bypass) | maintenance | Agent recommends action during lockout/tagout | Red-team `loto_violation` detection + the validator refuses; runbook LOTO step | Low |
| H7 | Wrong decision from a mis-fit model on real data | commissioning/operation | Proxy/benchmark model not re-fit to the site | Pilot onboarding kit real-fleet re-fit plan + shadow→assisted canary (no autonomous actuation until A/B sane) | Med — until site re-fit (G-035) |
| H8 | Safe-state failure on fault | operation | Torque anomaly / fault | Self-healing torque-anomaly → STO/SS1 (Stage 17) drives a safe state + signed audit row | Low |
| H9 | Decommissioning leaves stale credentials/keys | decommissioning | Keys/roles not revoked | A2A revocation poller + key rotation (`rotate-pqc-keys.sh`); pilot offboarding (runbook) | Med — pilot offboarding checklist owed |

## 3. Risk-reduction measures summary

- **Inherently safe design:** no LLM-direct actuation (Rule 3); deterministic loop; least-privilege governance (Stage 23 MAC/RBAC).
- **Safeguarding:** SIL-rated `safety/validator` + `sil_bridge` STO/SS1 (Stage 17); CI trace-pairing invariant; VDA freshness/anti-spoof gate (Stage 16); OT message HMAC (Stage 15).
- **Information for use:** the pilot deployment runbook (Art-26 deployer checklist), this RA, the safety case.

## 4. SIL / PL determination boundary

The Stage-17 `sil_pl_map` maps IEC 61508 SIL ↔ ISO 13849-1 PL for the contracts. **HONEST:** these are SIL-*amenable*
contracts validated in simulation; they are **NOT a certified SIL rating** — certification requires an accredited
assessor + a certified-PLC integration (G-011, §5). `sil_bridge` is the certified-PLC integration POINT, not a certified
component today.

## 5. Certification path (G-011 — the credibility objection, addressed honestly)

To move from "amenable to" → "certified":
1. **Functional safety:** engage an accredited body (e.g., TÜV) for an IEC 61508 / ISO 13849-1 assessment of the
   `validator`+`sil_bridge`+STO/SS1 path; integrate with a **certified safety PLC** (the `sil_bridge` is the seam) so the
   SIL-rated executor is the certified component and the LLM planner stays outside the safety boundary.
2. **Robot cell:** the integrator completes the ISO 10218-2 §6 RA for the *complete* system; our layer supplies the
   AI-boundary evidence (this RA + the safety case + audit_chain).
3. **EU AI Act:** the Annex-VI internal-control conformity file (Annex IV pack + QMS + post-market plan) — Stage 23 dry-run
   rehearses it; a notified body is only required for Annex-III point-1 (biometrics), which this system is not (research §33.1).
4. **Timeline:** binding high-risk date 2 Aug 2026; harmonised AI standards not yet published → no presumption of
   conformity yet → maintain the evidence file + re-assess as standards land.

## 6. Residual-risk statement

With the Stage-17 safeguards live + the governance layer (Stage 23) + the pilot shadow→assisted canary (no autonomous
actuation pre-A/B), the residual risk of the AI layer is assessed **acceptable for a CLOSED, human-supervised pilot**.
It is **not** assessed for unsupervised autonomous operation or for an uncertified SIL claim — those require G-011 §5.
Reviewed at Stage 23 dry-run; to be re-reviewed before any real actuation (pilot go-live, runbook §4).
