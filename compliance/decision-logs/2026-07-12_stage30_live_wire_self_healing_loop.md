# ADR — Stage 30: Live-wire the self-healing loop (repair dispatch + RL shadow + forecaster serving)

- **Date:** 2026-07-12
- **Status:** Accepted
- **Stage:** 30 (`tasks/STAGE_30_live_wire_self_healing_loop.md`) — second of the operator-chosen post-Stage-28 arc
  (29 conversational → **30 live-wire loop** → 31 detector hardening → 32 pilot-prep → CTO #6).
- **Roles:** `backend-engineer` (sim + runtime) + `ml-engineer` (RL shadow, forecaster serving) +
  `robotics-integration-engineer` (repair safety contract) + `agentic-governance-engineer` (traceability).
- **Research:** `research/initial-research.md §41` (repair-robot dispatch MRTA + shadow-mode/shielded RL deployment +
  forecaster serving SOTA) — appended BEFORE implementing (Hard Rule 11).

## Context

Several pieces of the KB_25 self-healing loop were trained/proven but NOT wired into the live loop: there was no real
recovery ACTION (a downed machine only waited out a passive MTTR timer, G-005); the Stage-7 MaskablePPO that beat the
rule was never consulted by the runtime (G-025-tail); and the operator-facing demand forecast was a hardcoded
placeholder disconnected from the trained model (G-036). Stage 30 wires all three, honestly and free/local.

## Decisions & outcomes (every number a live command this session)

1. **G-005 — repair-robot dispatch (KB_25 step-4 recovery action).** `agents/repair/dispatch.py`: on a breakdown the
   coordinator runs a deterministic **Contract-Net** — each AVAILABLE robot bids a REAL cost from its live state
   (availability/battery/queue; fault/charging/flat robots don't bid), min-cost wins (stable tie-break) — and the
   award is routed through `safety/validator.validate()` under a new `repair_dispatch` **SafetyContract** (SIL-1,
   Hard Rule 3) BEFORE any effect, signed to `audit_chain`. The winning robot "travels" (delay = its real bid cost)
   then applies `Stage.repair_assist(reduction_frac)`, which I made possible by turning the `_failure_loop` repair
   wait **interruptible**: on assist the remaining repair time is cut by the reduction fraction. **Paired A/B (10
   seeds, identical cracks, only the recovery policy differs, `scripts/run_repair_ab.py`): total downtime −47.9%
   (mean 10,215 s saved), 95% CI [7696, 12733] s, excludes 0** (`training/evals/results/repair_ab.json`).
2. **G-025-tail — MaskablePPO as a SHADOW recommender.** `agents/runtime/rl_shadow.py` runs the Stage-7 policy on its
   OWN fleet-scheduling distribution (the 30-dim group-env observation built from real degrading/crack-proximity/
   broken signals — NOT the out-of-distribution single-incident state), returns an RL recommendation + RL-vs-rule
   **agreement**, and is wired into the runtime `decide` node behind `RUNTIME_RL_SHADOW=1` (off by default). It is
   **SHADOW** — the recommendation is logged into the decision provenance + trace and **NEVER actuates** (the SOTA
   safe-deployment pattern, research §41.2); the rule's decision stands and the neuro-symbolic verifier + safety
   validator remain the post-decision shield; promotion shadow→active is Stage-28 autonomy-ladder + HITL gated.
   Honest-unavailable (`available=False`) when SB3/policy is absent — never a fabricated action.
3. **G-036 — demand forecaster SERVED into the operator path.** `services/demand_forecast_service.py` produces the
   7-day forecast from the best available REAL source: schema-compatible hourly history → the trained LSTM (next-step
   → daily via persistence, bounds from the model's REAL held-out MAE 32.9); an observed daily series → transparent
   empirical mean±std; else an HONESTLY LABELLED planning baseline with `model_loadable` surfaced and **NO fabricated
   confidence**. `state_manager._create_initial_supply_chain` now uses it, and the state carries
   `demand_forecast_source`/`_served` provenance.

## Honesty notes (Rule 1a — verified against the actual code path)

- **Removed an audit-invisible fabrication:** the legacy `state_manager` 7-day forecast carried a synthetic per-day
  `confidence = max(0.7, 0.92 - i*0.03)` — a fake-confidence constant the audit grep can't see (Rule 1a class). It is
  **gone**; the forecast now serves the real model or an honestly-labelled baseline with real (MAE/empirical) bounds.
- **No fabricated benefit in the sim:** `repair_assist` is a no-op unless the stage is genuinely in a broken repair
  wait; passive (no-dispatch) downtime is byte-for-byte unchanged; the A/B measures the REAL delta.
- **The RL never acts:** shadow-only; the actuator boundary is unchanged. Robots have no physical position in the
  SimWorld, so dispatch cost uses real availability, NOT a fabricated distance (disclosed; proximity routing = pilot).

## Consequences

- New: `backend/agents/repair/{__init__,dispatch}.py` + `backend/agents/runtime/rl_shadow.py` +
  `backend/services/demand_forecast_service.py` + `backend/scripts/run_repair_ab.py` + `backend/tests/repair/` +
  `tests/runtime/test_rl_shadow.py` + `tests/services/test_demand_forecast_service.py` (13 new tests). Modified:
  `simulation/entities/stage.py` (interruptible repair + `repair_assist`), `simulation/sim_world.py`
  (`request_repair`), `agents/runtime/nodes.py` (shadow wiring), `services/state_manager.py` (served forecast).
  **New deps: none** (Rule 9). KB_25/05/07 updated; G-005/G-025-tail/G-036 marked RESOLVED.
- **Audit holds 3** (`--no-baseline-drop`: additive real code — zero new `random.*`/mock; the fabricated `confidence`
  removal is audit-invisible, a net honesty gain). Regression **74 passed / 1 skipped** across sim/runtime/supply/
  repair/services; runtime determinism holds (shadow gated off). `verify-audit-chain.py` exit 0.
- Deferred honestly (all G-035, buyer-blocked): real-fleet repair validation + physical-proximity routing; RL
  shadow→active promotion validated on real data; real hourly-demand re-fit of the forecaster.

## References
- research §41 · `research/stage-explainers/STAGE_30/index.html` · `backend/agents/repair/dispatch.py` ·
  `backend/agents/runtime/rl_shadow.py` · `backend/services/demand_forecast_service.py` ·
  `backend/training/evals/results/repair_ab.json` · KB_25 (step 4) · G-005/G-025/G-036 (`audits/OPEN_GAPS_LEDGER.md`) ·
  ADR `2026-07-03_stage26_supply_chain_automation.md` (Contract-Net reused) · standardbots industrial-maintenance-2026 ·
  arxiv 2604.03497 (Sim2Real shadow-mode) · sciencedirect S0098135425005241 (MPC shielding).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-13T04:57:59+00:00 -->
<!-- signature: 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 -->
