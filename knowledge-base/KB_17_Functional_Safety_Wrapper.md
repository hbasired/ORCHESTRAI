---
name: Functional Safety Wrapper
description: LLM-as-planner / SIL-rated-classical-controller-as-executor architecture; safety contract DSL; STO/SS1 paths; ISO 10218 + IEC 61508 + ISO 13849-1 + IEC 62061 mapping
type: spec
last-invariant: never let an LLM directly command a SIL 2+ actuator
last-updated: 2026-05-18
---

# KB_17 — Functional Safety Wrapper

## Purpose

Define the architectural pattern that makes this control plane *amenable* to TÜV / notified-body certification: LLM = planner only; classical SIL-rated controller = executor; formal Pydantic contract gates every actuator command. Specify the safety contract DSL, the SIL routing, the STO/SS1 paths.

## Source of truth

- ISO 10218-1/2:2025 (industrial robot safety, third edition).
- ISO/TS 15066 (collaborative robot safety — speed/force/separation).
- IEC 61508 (functional safety of E/E/PE systems, parts 1–7).
- ISO 13849-1:2023 (machinery — safety-related parts of control systems).
- IEC 62061:2021 (programmable electronic safety for machinery).
- This file is the contract for `backend/safety/`.

## Body

### The architectural principle

**LLM is a planner. Classical SIL-rated controller is the executor. A formal contract gates every actuator command.**

An LLM is non-deterministic; it cannot provide the validation that ISO 10218 / IEC 61508 / ISO 13849-1 / IEC 62061 require. The wrapper architecturally enforces that the LLM contributes plans only; a classical controller (PLC-bridged) is the actual actuator. This makes the system *amenable* to certification — actual certification is a Stage 23 + external-assessor activity, not a code-only claim.

### SIL routing

| SIL | Examples | Path |
|---|---|---|
| SIL 0 | LLM planning, monitoring, dashboarding, KPI calculation | LLM direct |
| SIL 1 | Routing recommendations (advisory), throughput throttling (advisory) | LLM → `validator` → operator UI for confirmation → executor |
| SIL 2+ | Robot motion command, conveyor start/stop, machine state change, any actuator | LLM → `validator` → `sil_bridge` → classical SIL-rated controller → actuator. **LLM CANNOT bypass.** |
| SIL 3+ | Emergency stop interlocks, safety-rated speed limits, light-curtain triggers | Hardwired safety circuit; LLM only OBSERVES the state, never commands. STO/SS1 paths. |

CI gate `safety-contract-tests`:

- Every test that exercises an actuator path must produce a `safety.validate.*` OpenTelemetry span IMMEDIATELY before the `actuator.*` span. CI parses traces; fails on missing pair.

### Component shape

- `backend/safety/contract.py` — Pydantic safety-contract DSL.
- `backend/safety/validator.py` — pre-flight check; `validate(action, world_state, contract) -> Decision`.
- `backend/safety/sil_bridge.py` — bridge to PLC / safety controller (OPC UA Safety profile or PROFIsafe placeholder).
- `backend/safety/sto_ss1.py` — emergency stop paths.

### Safety contract DSL

```python
# backend/safety/contract.py
from pydantic import BaseModel, Field
from typing import Literal, Callable

class Precondition(BaseModel):
    name: str
    description: str
    check: Callable[[dict], bool]   # against world_state

class Postcondition(BaseModel):
    name: str
    description: str
    check: Callable[[dict, dict], bool]   # (world_state_before, world_state_after)

class Invariant(BaseModel):
    name: str
    description: str
    check: Callable[[dict], bool]   # must hold continuously during action

class SafetyContract(BaseModel):
    name: str
    sil: Literal[0, 1, 2, 3, 4]
    iso_clauses: list[str]          # e.g. ["ISO 10218-2:2025 §5.4.2", "ISO/TS 15066 §5.5.5"]
    preconditions: list[Precondition]
    postconditions: list[Postcondition]
    invariants: list[Invariant]
    fail_safe_path: Literal["STO", "SS1", "SS2", "SLS", "operator_confirm", "no_action"]
```

Each actuator-bound action references a named contract. Example contracts:

- `move_amr_to_charging_station` — SIL 2; preconditions include "battery > 5%", "path clear (YOLO + lidar agree)", "AMR not currently in zone-restricted operation". Invariant: "max speed ≤ ISO/TS 15066 §5.5.5 limit for current zone".
- `start_conveyor_segment` — SIL 2; precondition "light curtain unbroken", "no person detected in immediate vicinity". Fail-safe: STO.
- `expedite_supplier_order` — SIL 0 (commercial, not safety-critical); preconditions advisory only.

### Validator flow

```python
# backend/safety/validator.py
def validate(action: Action, world_state: dict, contract: SafetyContract) -> Decision:
    # 1. Precondition gate
    for p in contract.preconditions:
        if not p.check(world_state):
            audit_chain.append(actor="safety.validator", action="precondition_fail",
                               payload={"action": action.dict(), "contract": contract.name,
                                        "failed": p.name})
            return Decision(allow=False, reason=f"precondition_fail:{p.name}",
                            fail_safe_path=contract.fail_safe_path)

    # 2. SIL routing
    if contract.sil >= 2:
        # Route through classical executor; LLM cannot bypass
        return Decision(allow=True, route="sil_bridge", contract=contract)
    if contract.sil == 1:
        # Advisory; needs operator confirmation
        return Decision(allow=True, route="operator_confirm", contract=contract)
    return Decision(allow=True, route="direct", contract=contract)

    # 3. Postcondition + invariant checks happen during execution (executor calls back)
```

### STO / SS1 paths

`backend/safety/sto_ss1.py`:

- `trigger_sto()` — Safe Torque Off; cuts motor torque immediately. Hardwired in real deployment; software trigger for simulation.
- `trigger_ss1(deceleration_profile)` — Safe Stop 1; controlled stop then STO.
- Both ALWAYS write to `audit_chain` with `actor=safety.sto`, `action=trigger`, full world state at trigger time, ML-DSA-65 signed.

### What the LLM never does

- Issue raw `actuator.*` calls.
- Decide SIL level (the contract defines it).
- Modify contracts at runtime.
- Suppress validator decisions.

The LangGraph runtime structurally separates planning nodes from execution nodes; only execution nodes are wired to `sil_bridge.py`.

### Mapping to standards

| Standard | Clause | Where covered |
|---|---|---|
| ISO 10218-1:2025 | Robot safety requirements | `SafetyContract.iso_clauses` per-action mapping; risk register row |
| ISO 10218-2:2025 | Robot system integration | Wrapper architecture; Stage 23 risk assessment |
| ISO/TS 15066 | Collaborative robot speed/force limits | Invariants embedded in contracts; tests under `backend/tests/safety/test_iso15066.py` |
| IEC 61508 parts 1–7 | SIL classification + lifecycle | `SafetyContract.sil`; safety lifecycle documented in compliance/ |
| ISO 13849-1:2023 | Performance Level (PL) routing | Mapped to SIL in `backend/safety/sil_pl_map.py` |
| IEC 62061:2021 | SIL claim for machinery | Stage 23 conformity dry-run pack |

### What this design does NOT claim

- **No SIL certification claim.** The architecture is *amenable* to certification. Actual certification = Stage 23 + external assessor. PRD v2 §6 carefully avoids overclaim.
- **No certified PLC.** `sil_bridge.py` is the integration point with the customer's existing certified PLC; we don't replace it.
- **No coverage of process-safety standards (IEC 61511).** Process industries are post-v2 wedge.

### Test gates

- `pytest backend/tests/safety/` — contract conformance, validator decisions, STO/SS1 round-trip.
- CI: every test producing an `actuator.*` span must have a preceding `safety.validate.*` span. Enforced by `scripts/check-safety-trace-pairing.py` (Stage 17 ships this).

---

## Self-Healing Robotics (extension 2026-05-24, inspired by Project Aether §4.3)

"Self-healing" in software-defined robotics = **introspection on actuator state + automated remediation** before the failure cascades to safety.

### Mechanism

The Stage 17 functional safety wrapper is extended with three layers of self-healing:

1. **Joint-torque anomaly detection (per robot).**
   - Subscribed via `backend/integrations/sparkplug/payload.py` (Sparkplug B device metrics).
   - Lightweight on-edge model: Isolation Forest or Conv-AE trained on per-joint torque variance windows.
   - Threshold: per-joint torque-variance Z-score > 3σ over rolling window.

2. **Behaviour-tree-driven self-repair routine.**
   - When anomaly fires, the robot's behaviour tree (`backend/safety/behavior_trees/<robot_class>.yaml`) triggers a `self_diagnose_calibrate` branch.
   - Robot navigates to a maintenance bay (VDA 5050 instantAction `dock_to_maintenance`); runs a built-in calibration routine; reports back via Sparkplug B.
   - If calibration restores baseline torque: robot resumes; `audit_chain` row written with `action=self_repair.success`.
   - If calibration FAILS: STO triggered; robot quarantined; maintenance ticket auto-created; `audit_chain` row written with `action=self_repair.failed; severity=high`.

3. **Pod-level self-healing via KubeEdge (software path).**
   - Containerised ROS 2 nodes run as Kubernetes pods on EdgeCore (KB_21 KubeEdge).
   - KubeEdge's pod liveness probe auto-restarts crashed nodes.
   - Persistent crashes (>3 restarts in 5 min) → quarantine robot; audit_chain row.

### Acceptance criteria (Stage 17 extension)

- Joint-torque anomaly detector trained on simulated noise + degradation traces.
- Behaviour trees authored for at least two robot classes (AMR + manipulator).
- Test: inject synthetic torque anomaly; verify (a) anomaly detected; (b) `self_diagnose_calibrate` branch fires; (c) on calibration failure, STO triggers; (d) `audit_chain` rows present at every transition; (e) the actuator-safety-validate trace pairing remains intact across the self-repair sequence.

### Why this exceeds Project Aether's self-healing description

Project Aether describes self-healing in conceptual terms (joint torque anomaly → diagnostic calibration). Where we extend further:

- The self-repair action itself goes through `backend/safety/validator.py` — we cannot skip safety even during self-repair.
- Every state transition (anomaly detected → repair initiated → calibration succeeded/failed → STO) writes a ML-DSA-65 signed `audit_chain` row, giving cryptographic provenance for the entire self-healing decision tree. EU AI Act Art. 12 evidence.
- Pod-level self-healing (KubeEdge) AND robot-state self-healing (behaviour tree) layered — not just one.

## Capability-token actuation authorization (Stage 33, 2026-07-13 — G-075 CLOSED)

The `sil_bridge` previously trusted a caller-settable `Decision.allow`/`route`, so a FORGED
`Decision(allow=True, route="sil_bridge")` could actuate, and a stale genuine Decision was a TOCTOU risk (open through
CTO #4/#5/#6). **Now closed** with the capability-token pattern (research §44.1):

- `backend/safety/capability_token.py` — `validate()` MINTS an unforgeable, action-bound, time-limited token on every
  ALLOW: `HMAC-SHA-256(per-process secret, canonical{allow, route, contract, sil, action_hash, nonce, issued_at})`,
  where `action_hash = sha256(canonical(action))` binds the token to the EXACT action.
- `sil_bridge.execute()` actuates ONLY via one of two forgery/TOCTOU-resistant paths: **(a)** authoritative
  RE-VALIDATION when passed `contract` + `world_state` (re-runs `validate()` against CURRENT state, ignores the passed
  verdict) or **(b)** a valid, FRESH token bound to THIS action. A forged (no token), stale (replay/TOCTOU),
  wrong-action, or tampered Decision is rejected (`SafetyBypassError`).
- The `Decision` model gained `token`/`nonce`/`issued_at`. Defence-in-depth wording narrowed in `safety/__init__.py` +
  the `sil_bridge` docstring. Binding gate remains the validator. Verified: `tests/safety/test_capability_token.py`
  (7 tests) + the full safety suite (26) pass. No new deps (stdlib `hmac`/`os.urandom`). ADR
  `2026-07-13_stage33_safety_oversight_hardening.md`.

## Last verified

2026-06-21 (Stage 17), by robotics-integration-engineer + agentic-governance-engineer: the **functional safety wrapper
is BUILT** — `backend/safety/`:
- `contract.py` — the Pydantic safety-contract DSL (Precondition/Invariant/Postcondition/Action/SafetyContract/Decision).
- `contracts/` — the 5 named contracts (`move_amr_to_charging_station`, `start_conveyor_segment`,
  `expedite_supplier_order` [SIL 0], `change_machine_state`, `dispatch_amr_to_zone`) with real checks.
- `validator.py` — `validate(action, world_state, contract) -> Decision`: precondition + invariant gate → **SIL routing**
  (SIL≥2 → `sil_bridge`; SIL 1 → `operator_confirm`; SIL 0 → `direct`); a failed/raising check BLOCKS (fail-safe) +
  records a signed `audit_chain` row + names the `fail_safe_path`. (Plus the Stage-16 `validate_order` VDA gate.)
- `sil_bridge.py` — the ONLY emitter of `actuator.*` spans; refuses any non-allowing / mis-routed **validator-produced**
  Decision, and is **self-validating** (re-runs `validate()` from contract+world_state) when given them — forgery/TOCTOU-proof
  (G-075; the first real PLC caller @18 MUST pass them). Honest placeholder for the customer's certified PLC (OPC UA
  Safety / PROFIsafe) — no SIL cert claimed.
- `sto_ss1.py` — STO / SS1 (IEC 61800-5-2); every trigger writes a signed `audit_chain` row (best-effort; safety never
  blocked by an audit outage). `sil_pl_map.py` — IEC 61508 SIL ↔ ISO 13849-1 PL (ISO 10218-1:2025: PL d/SIL 2 Class II).
- `self_healing/` — joint-torque anomaly detector (robust rolling-Z >3σ) → behaviour-tree (`behavior_trees/amr.yaml` +
  `manipulator.yaml`) `self_diagnose_calibrate` → resume (the resume itself passes `validator.validate()`) OR STO +
  quarantine; every transition writes a signed `audit_chain` row.

**CI invariant (`scripts/check-safety-trace-pairing.py`):** every `actuator.*` span is preceded by a `safety.validate.*`
span — wired on the VDA dispatch path (`master.dispatch_order`) + the runtime `execute` node; CI gate
`safety-contract-tests`. **Verified live:** `tests/safety/` + `tests/security/` **33 tests pass**; runtime canned-decision
**7 pass** (execute node now routes through `validate()`); audit holds **364**.

**Zero-trust (CTO #3 G-063/G-064) — `backend/security/`:** adopted **NIST SP 800-207** (+ CSA Agentic Trust / MAESTRO /
OWASP NHI), pillars mapped (`zero_trust.py`); **per-internal-agent ML-DSA-65 non-human identity** (`agent_identity.py`);
**MCP tool authz** — least-privilege capability grants + argument sanitisation + rate-limiting (`mcp_authz.py`) + an
**ML-DSA-65 signed tool manifest** that detects a rogue/injected tool (`tool_manifest.py`). The A2A interim
`X-A2A-Peer-Key` gate → live mTLS-client-cert→`peer_state` binding is **Stage 18** (KB_13) — honestly deferred.

**Does NOT claim:** SIL certification (architecture is *amenable*; cert = Stage 23 + external assessor); a certified PLC
(`sil_bridge` is the integration point); KubeEdge pod-healing (KB_21 / Stage 21+). ADR `2026-06-21_stage17_functional_safety_wrapper.md`.

**Stage 23 (conformity dry-run) — the cert path is now written down (G-011).** `compliance/iso-10218-risk-assessment.md`
(ISO 10218-2:2025 §6, absorbs ISO/TS 15066) catalogues the AI-boundary hazards H1-H9, maps this safety wrapper as the
risk-reduction measures, and §5 lays out the explicit certification path: accredited IEC-61508 / ISO-13849-1 assessment
of the `validator`+`sil_bridge`+STO/SS1 path **integrated with a certified safety PLC** (the `sil_bridge` seam), the
integrator's complete-cell RA, and the EU-AI-Act **internal-control (Annex-VI)** conformity file (our Annex-III category
is points 2-8 → no notified body mandated; research §33.1). Still amenable-not-certified — but the objection (G-011) is
now answered with a concrete path. ADR `2026-06-22_stage_23_dry_run_outcome.md`.

Prior: 2026-05-18, agentic-governance-engineer + robotics-integration-engineer review (contract only; no code existed yet).
