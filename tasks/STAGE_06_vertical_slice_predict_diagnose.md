---
status: done
stage: 06
slug: vertical_slice_predict_diagnose
created: 2026-06-01
---

# Stage 06 — Vertical Slice v0: predict → diagnose → intervene (sim-closed-loop, machine-failure scenario)

> The stage CTO Checkpoint #1 demanded: *"freeze new spec expansion … build ONE end-to-end vertical slice
> (predict→diagnose→intervene on the machine-failure scenario) before widening."* This stage converts the two
> existing predictors (Stage 4 XGBoost PdM, Stage 5 LSTM demand) from passive brains into the first **closed
> loop**: live SimPy telemetry feeds the failure predictor; a deterministic diagnosis service identifies the
> root cause; the coordinator executes a sim-only intervention; and a measured A/B (intervention vs
> no-intervention) proves the loop's value with a real number. This is also the **fundability artifact**
> (PRD v3 §19, KB_26 §9): the demo that converts "spec-deep" into "working closed loop."
> Cross-links: PRD v3 §1/§12/§17-A/§18 · KB_25 (the engine) · KB_24 §flows · ADR `2026-06-11_strategic_product_reset.md`.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–10)

- [x] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [x] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [x] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys. *(Note: diagnose v0 is deterministic — no LLM call is required for this stage's core loop.)*
- [x] **Stage explainer HTML (operator mandate, 2026-06-11; added mid-stage):** before close, write `research/stage-explainers/STAGE_06/index.html` — self-contained, explaining what this stage built and why, how the slice works (real file paths), the measured A/B numbers, and what changed. This requirement is now seeded for all future stages via `tasks/TASK_TEMPLATE.md`.

## Pre-requisites

- Stage(s) closed: 2 (SimPy DES), 3 (WS broker + Redis), 4 (failure predictor), 5 (demand forecaster).
- **Owed audits run at stage open (before implementation):**
  - [x] Independent CTO Checkpoint #1 pass — completed 2026-06-12 by a fresh cto-reviewer agent (the script's documented fallback) → `audits/CTO_1_independent_review.md`. Verdict: REVISED (slice changes the picture; ON TRACK, risk high→moderate). **G-031 retired.** Refuted remediation #2 (ledger surfacing) wired into `scripts/start-task.sh` within this stage.
  - [x] Stage 3 independent re-audit — completed 2026-06-12 by a fresh task-auditor agent (the script's documented Agent-tool fallback) → `audits/STAGE_03_independent_review.md`, verdict PASS-WITH-GAPS. **G-001 retired**; new finding ledgered G-047.
- Decision logs honoured: `2026-05-31_causal_self_healing_engine.md` (the loop), `2026-05-31_free_cost_active_diagnosis_carryforward.md` (active diagnosis is Stage 11 — v0 here is deterministic), `2026-06-11_strategic_product_reset.md` (this stage's mandate; D4).
- KB files at minimum version: KB_25 (2026-05-31+), KB_24 (2026-05-31+), KB_02 (2026-06-01+, lists both brains).
- Gaps ledger rows acknowledged (NOT resolved here — they deepen this slice at their target stages): **G-005** (repair-dispatch, →11/16/17), **G-014** (durable HITL workflow, →11), **G-025** (PPO intervene, →7/11), **G-026** (active diagnosis protocol, →11), **G-036** (demand forecaster live wiring, →11), **G-019/G-020** (learned world model / causal twin, →8).

## Acceptance criteria

(Each independently testable via §Verification commands. The slice is sim-only — no real actuator paths exist yet, so the Stage-17 safety wrapper is NOT required; the intervention path is confined to `SimWorld`.)

- [x] **AC1 — Live predict path.** SimPy telemetry windows (per-machine health/wear features from `sim_world.py`) stream into `backend/ml/failure_predictor.py` during a run; predictions (machine_id, P(failure), horizon) are emitted as events on the existing Redis→WS fan-out. No placeholder, no `random.*`, honest `ModelUnavailableError` if the brain is absent. Verified by `backend/tests/test_slice_predict_live.py`.
- [x] **AC2 — Diagnose v0.** New `backend/services/diagnosis.py`: deterministic root-cause analysis for the `machine_crack` scenario — given a failure prediction + the machine's recent telemetry window + sim topology, it returns a ranked cause hypothesis (e.g., wear-threshold breach vs upstream-overload vs power-dip aftermath) with the evidence trail. Pure function over inputs (testable, explainable); no LLM. Verified by `backend/tests/test_diagnosis.py` (≥6 cases incl. ambiguous/no-cause).
- [x] **AC3 — Intervene v0 (sim-only).** The `EmbodiedCoordinator` consumes diagnosis output and executes a recovery inside `SimWorld` via the existing inject/apply machinery: preemptive maintenance scheduling (take machine offline at the optimal low-load moment) and/or slow-and-catch-up on adjacent stages. The decision + rationale are persisted to `decision_logs`. Verified by `backend/tests/test_slice_intervene.py`.
- [x] **AC4 — Measured A/B (the headline number).** A reproducible experiment script runs N seeded sim-hours twice — loop ON vs loop OFF — on the machine-failure scenario and reports throughput loss + downtime minutes for both arms. The **measured delta** (not a target) is recorded in KB_23 §measured and in this doc's Hand-off. Verified by `backend/tests/test_slice_ab.py` (smoke: both arms run, report emitted; the delta is reported honestly, never fabricated).
- [x] **AC5 — Event surface.** Slice events (`prediction`, `diagnosis`, `intervention`, `ab_report`) ride the existing canonical envelope (KB_04) over `/ws` — no new UI pages this stage (dashboard work is Stage 12.5 per G-006). Verified by `backend/tests/test_slice_events.py`.
- [x] **AC6 — Audit baseline strictly decreases.** Pre-stage baseline 402; run `bash scripts/audit.sh --json` at stage open, name the patterns this stage's touched paths will remove (candidates: remaining `heuristic_actions` / `mock_predictions` in `backend/agents/` + `backend/ml/rl_policy.py` stubs the coordinator path touches), and close with TOTAL < 402.
- [x] **AC7 — Independent audit: PASS-WITH-GAPS** (2026-06-12, fresh task-auditor agent → `audits/STAGE_06_independent_review.md`). 32/32 tests re-run green; anti-cherry-pick A/B on auditor seed 77 confirmed the harness reports honestly (downtime delta slightly negative there; crack prevention 100%); audit 396 confirmed; theatrical scan clean. Gaps ledgered: G-045 (decision_logs DB persistence → 11), G-046 (A/B CRN pairing/CIs → 7); claim framing corrected in KB_23 (robust metric = crack prevention, not downtime minutes).
- [x] **AC8 — KB updated.** KB_01 (slice architecture), KB_05 (scenario + intervention semantics), KB_02 (no new weights expected; note if any), KB_23 (A/B measured row), KB_25 (mark predict=BUILT-live, diagnose=v0-BUILT, intervene=v0-BUILT, verify=PLANNED), KB_TASK_LOG entry.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/services/diagnosis.py` | Deterministic root-cause v0 for machine_crack (ranked hypotheses + evidence trail) |
| `backend/services/slice_runner.py` | Wires predict→diagnose→intervene over a live SimWorld run; emits slice events |
| `backend/scripts/run_slice_ab.py` | Seeded A/B experiment: loop ON vs OFF, N sim-hours, JSON+markdown report |
| `backend/tests/test_diagnosis.py` | Diagnose v0 unit tests (≥6 cases) |
| `backend/tests/test_slice_predict_live.py` | Live telemetry→predictor path test |
| `backend/tests/test_slice_intervene.py` | Coordinator intervention path test |
| `backend/tests/test_slice_ab.py` | A/B harness smoke test |
| `backend/tests/test_slice_events.py` | Envelope conformance for slice events |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/simulation/sim_world.py` | Expose per-machine telemetry windows + a safe intervention API (preemptive maintenance / throttle) |
| `backend/agents/embodied_agent.py` | Consume diagnosis output; choose + execute sim-only intervention; persist decision + rationale |
| `backend/services/ws_broker.py` | Add slice event types to the canonical envelope (KB_04-conformant) |
| `backend/ml/failure_predictor.py` | Accept streaming telemetry windows (batch→online adapter) if needed |

## Files to DELETE

| Path | Reason |
|---|---|
| `backend;C\` (junk dir at repo root) | G-040 hygiene — artifact of a malformed shell command; no references (verified by grep) |
| 6 `random.*` fabrication lines in `backend/agents/manufacturing_agent.py` | AC6 — replaced by real SimWorld observation (`_sync_from_world`); audit 402 → 396 |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_01_System_Architecture.md`
- `knowledge-base/KB_05_Simulation_Spec.md`
- `knowledge-base/KB_23_Evals_and_Benchmarks.md`
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md`

## Verification commands

```bash
# Audit baseline strictly decreases
bash scripts/audit.sh

# Tests pass
cd backend && pytest -q

# Stage-specific: the slice A/B (seeded, reproducible)
cd backend && python scripts/run_slice_ab.py --seed 42 --sim-hours 8 --scenario machine_crack
# → prints/records: downtime_minutes_on, downtime_minutes_off, throughput_delta, report path

# Independent audit
bash scripts/independent-audit.sh 6
```

## Audit target

- Pre-stage baseline: **402** (`.audit-baseline` at stage open; re-confirm with `bash scripts/audit.sh`)
- Target: **< 402** — patterns named at stage open from `audit.sh --json` over the touched paths (coordinator/agents heuristics, rl_policy stub calls in the slice path)

## Role

- Primary: `ml-engineer` (slug keyword `predict`; the predictor-integration + diagnosis logic is model-adjacent)
- Secondary (hand-offs): `backend-engineer` (coordinator/services/WS wiring), `task-auditor` (AC7), `cto-reviewer` (pre-req CTO pass)

## Risks / unknowns

- Proxy-trained brain (AI4I) may produce weak signal on SimPy-generated telemetry — if feature distributions diverge, document honestly and (if needed) re-fit on sim telemetry via the Stage-4 Colab pipeline (free), recording it as a new brain version with card + metrics. Do NOT tune the sim to flatter the model.
- A/B effect size may be small at default calibration — report the honest number; a small-but-real delta beats a tuned demo (the number is the artifact, not the marketing).
- The intervention API must not let the coordinator violate sim invariants (negative queues, teleporting AMRs) — property tests in AC3.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The first CLOSED predict→diagnose→intervene loop runs on real sim telemetry + the real XGBoost brain.
    **Measured A/B (3 seeds × 8 sim-h): unplanned downtime 470.3 → 268.8 min (−42.8%); 92% of crack breakdowns
    prevented; total downtime incl. planned maintenance −32.1%; throughput unchanged (arrival-limited plant).**
    Report: `backend/training/evals/stage06/results.{json,md}`.
  - Stages expose AI4I-unit `telemetry()` + a planned-maintenance intervention API with honest downtime accounting.
  - Latent Stage-2 crack-ETA bug fixed (SimPy interrupt); regression-covered.
  - Manufacturing head de-mocked (observes the REAL SimWorld); audit baseline 402 → 396.
  - Slice events (`prediction/diagnosis/intervention/ab_report`) ride the canonical envelope on `/ws`.
  - Per-stage explainer HTML is now mandatory (TASK_TEMPLATE + CLAUDE.md §6); first one: `research/stage-explainers/STAGE_06/`.
- What the next stage starts with:
  - Stage 7 (RL intervene): replace `services/intervention_policy.decide_intervention` with PPO over the SAME
    decision contract; `backend/scripts/run_slice_ab.py` is the ready-made training/eval environment.
  - Stage 8 (world model + causal twin) later replaces the rule ranking in `services/diagnosis.py` behind the
    same `Diagnosis` interface.
  - `LiveSliceRunner` (built, unwired) is the seam for Stage 11's runtime/HITL work.
- Open items deferred to a future stage (name the stage if known):
  - Active diagnosis protocol (`diagnose.request/report`) → Stage 11 (G-026); repair-robot dispatch → 11/16/17 (G-005); HITL/durable workflow → 11 (G-014); demand-forecaster live wiring → 11 (G-036); PdM dashboard → 12.5 (G-006).
  - Legacy local test debt (pre-existing, verified via git-stash on the pre-Stage-6 tree): `tests/test_api.py`
    21 failures + `tests/test_websocket_smoke.py` hang block a clean full-suite `pytest -q` locally without the
    compose stack → **G-044**, target Stage 11 (API/runtime rework).
  - Robotics + supply-chain heads still fabricate internal state (`random.*`) — same de-mock pattern as the
    manufacturing head → Stage 11 (part of the 396-baseline reduction there).

---

*Template version: 2026-05-18 (PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-requisites (pre-filled from STAGE_05_demand_forecasting.md hand-off)


- What is now true: a real LSTM demand forecaster with `forecast(...)`; baseline < 404.
- What the next stage starts with: predict (Stage 4) + demand (Stage 5) feeding the world/optimization → toward diagnose (Stage 8/11).
- Open items deferred: re-fit on real order data; probabilistic forecasting; energy forecaster (Stage 6.5).

---

*Authored 2026-06-01 (agentic-governance-engineer, for ml-engineer). Replaces the start-task.sh TBD seed.*
*Re-authored 2026-06-11 as Vertical Slice v0 per the Strategic Product Reset (ADR `2026-06-11_strategic_product_reset.md`, decision D4) — CTO Checkpoint #1's vertical-slice mandate, pulled to Stage 6 as v0; the production slice remains Stage 11.*
