---
name: Causal Self-Healing Cognitive Engine
description: The additive innovation — upgrade the embodied coordinator from reactive coordination to a predict→causally-reason→verify→intervene self-healing loop (learned world model + causal digital twin + neuro-symbolic verification + RL recovery). Maps the LSTM/YOLO/RL/DL stack and the dynamic operator features.
type: spec
last-updated: 2026-06-13
---

# KB_25 — Causal Self-Healing Cognitive Engine

## Purpose

Define the genuinely-new capability that sits ON TOP of the existing `EmbodiedCoordinator` (which today only
*reacts* + coordinates): a loop that **predicts** failures, **reasons about cause** (root-cause + counterfactual
"what-if"), **verifies** the chosen fix against formal safety logic, and **intervenes** with a no-interruption
recovery. This is the differentiator beyond embodiment/EU-AI-Act/PQC. It also pins down where the DL/RL
algorithms live and how the operator's dynamic/interactive features work.

## Source of truth

- Research log §13 (2026-05-31) + cited papers: CausalTrace (arXiv 2510.12033), Causal Digital Twin
  (arXiv 2510.09616), Verifiable-logic planners (arXiv 2602.08373), LSTM-AE+Transformer PdM (PMC11125296).
- Existing code: `backend/agents/embodied_agent.py` (coordinator), `backend/simulation/` (world), KB_17 (safety),
  KB_22 (digital twin), KB_23 (evals). ADR 2026-05-31_causal_self_healing_engine.md.

## Body

### 1. The loop: predict → causally-reason → verify → intervene

```
   sensors / sim / OT  ──▶ (1) PREDICT  ── learned world model (LSTM-AE + Transformer; CNN-LSTM/Transformer-GRU)
                                   │            "machine M will fail in ~T minutes; confidence c"
                                   ▼
                          (2) CAUSALLY REASON ── Causal Digital Twin + neurosymbolic causal agent
                                   │            root cause + counterfactual: "what if backup online + slow neighbours?"
                                   ▼
                          (3) VERIFY ── neuro-symbolic grounding (LLM planner ⟂ formal constraint/logic engine)
                                   │            enforce pre/post-conditions + safety contracts (KB_17). Reject unsafe plans.
                                   ▼
                          (4) INTERVENE ── RL/optimization (PPO) picks the no-interruption recovery
                                   │            self-repair | dispatch robot-fixer | bring backup online | slow + catch-up
                                   ▼
                          EmbodiedCoordinator executes via domain heads ── every step signed to audit_chain + observable
```

Each step is **observable** (emits an agent-trigger event) and **ledged** (signed audit row). The difference
from today: today step (1)–(3) don't exist; the coordinator only reacts to an incident after it fires.

### 1b. Active diagnosis (probe → reason), not just passive prediction

Prediction can be **wrong or uncertain**. So the coordinator does not only forecast — it **actively
interrogates** a suspect agent before committing to a fix:

```
coordinator suspects agent A (low confidence / conflicting signals)
   ──▶ DIAGNOSE command to A: "run self-check; report sensor S, last N errors, health vector"
   ◀── A responds (or times out → A is the fault)
   ──▶ coordinator REASONS over the response (causal step 2): localize fault, confirm/deny the prediction
   ──▶ if confirmed → verify+intervene; if A healthy → widen probe to neighbours / revise the world model
```

This makes the loop **closed and self-correcting**: a wrong prediction is caught by the diagnostic round-trip
instead of triggering an unnecessary intervention. It adds two agent-message types to the coordination protocol
(KB_06): `diagnose.request` (coordinator/head → agent: run a named self-check) and `diagnose.report`
(agent → up the chain: result + health vector). Both are observable (G-021) and ledged. Misdiagnosis itself is
a recorded outcome the world model learns from. (G-026)

### 1c. Free-cost reasoning (Groq) — applies to the whole engine

All reasoning runs on a **free** LLM by default: **Groq free tier** (`default_llm_provider="groq"`,
`GROQ_API_KEY` in `backend/.env`), with **Ollama (local)** as the offline/zero-network fallback. The causal,
neuro-symbolic, and planning steps must work within free-tier limits (small prompts, cached context, batched
calls) — no paid API is a build-time dependency through the final stage. See memory `feedback_free_cost_groq`.

### 2. Where the DL / RL / DL algorithms live (answering "why aren't LSTM/YOLO/RL here?")

| Algorithm | Role in the engine | Stage | Status |
|---|---|---|---|
| **YOLOv8/v10** (vision) | quality/defect/object detection; safety video monitoring | 5/9 | BUILT (YOLOv8 pretrained) / retrain planned |
| **LSTM-Autoencoder + Transformer encoder** | asset-failure prediction (step 1) + world-model forecast | 4, 8 | PLANNED (scaffold at `backend/training/stage_04_predictive_maintenance/`) |
| **CNN-LSTM / Transformer-GRU hybrids** | higher-accuracy failure/RUL forecasting | 4 | PLANNED |
| **PPO (reinforcement learning)** | recovery + throughput optimization (step 4) | 7 | PLANNED |
| **Causal discovery + counterfactual models** | root-cause + "what-if" (step 2) | NEW (this KB) | PLANNED |
| **Neuro-symbolic constraint/logic engine** | verify plans against formal pre/post-conditions (step 3) | NEW + 17 | PLANNED |
| Demand/energy forecasting | supply-chain + energy heads | 6, 6.5 | PLANNED |

They were never "missed" — they are the building blocks; KB_25 gives them a unifying purpose.

### 3. Worked example (the operator's scenario, generalised)

`machine_M.health↓` → MachineAgent emits trigger → **ManufacturingHead** → **EmbodiedCoordinator**.
Coordinator: (1) LSTM predicts M fails in ~8 min; (2) Causal DT finds root cause = bearing wear + counterfactual
shows "bring backup B online + slow stages S3–S4 by 15% → zero line stop"; (3) neuro-symbolic verify: plan
satisfies SIL contract + throughput floor → APPROVED; (4) PPO selects "dispatch robot-fixer R7 to M, B online,
S3–S4 throttled". Coordinator messages RoboticsHead (dispatch R7), ManufacturingHead (throttle/backup),
SupplyChainHead (hold inbound). M self-repairs/repaired, then catches up to nominal; system restores full
speed. Every message + decision is live-observable and signed. **One of infinite scenarios — the loop is
scenario-agnostic.**

### 4. Dynamic / interactive operator features (spec; staged)

- **Live agent-trigger observability** — a real-time graph of the message cascade
  (agent→head→embodied→head→agent) with latency + the decision at each hop, all ledged. KB_06 + KB_15 +
  operator dashboard. Stages 11–12.5. (G-021)
- **Chatbot ("ask the factory")** — conversational MCP/LLM interface to query agent status, history, and "why
  did X happen?" (causal trace). Stage 12+. (G-022)
- **NL problem injection** — operator describes a problem in natural language → LLM parses → mutates state
  (`SimWorld.inject` / DB write) → engine detects, reasons, re-plans. Stage 11+. (G-023)
- **Bidirectional DB-edit-triggers-problem** — operator edits a DB value to make an agent "problematic" → CDC
  (Stage 13) detects the change → engine finds the induced problem, reasons, changes state, self-optimizes.
  (G-024)

### 5. N-domain embodiment (beyond robots/manufacturing/supply-chain)

The coordinator is designed for N head agents. New domains (research §13.4): **Quality & Inspection** (G-016),
**Workforce & Safety** (G-017), **Facilities/Building energy** (G-018) — in addition to Energy (KB_20). Each is
a head agent the loop above operates over.

### 6. Honest status

Most of §1–§5 is **PLANNED/PARTIAL**. Built today: the reactive coordinator + SimPy world + YOLOv8, **and (Stage
4, 2026-06-01) the PREDICT step (step 1): `backend/ml/failure_predictor.py` — an AI4I-2020 failure-risk MLP
(ROC-AUC 0.972 / PR-AUC 0.679 on 3.4%-positive data, no leakage; honest first-cut proxy, re-fit on real
telemetry = G-035).** Stage 5 (2026-06-01) adds the supply-chain **demand forecaster** (`backend/ml/demand_forecaster.py`, LSTM,
MAE 32.9 / MAPE 21% / +59% vs persistence) — an input to the optimization/intervene step.

**Stage 6 (2026-06-12) closes the loop for the first time (Vertical Slice v0):** PREDICT is now **BUILT-live**
(real sim telemetry → the XGBoost brain inside `services/slice_runner.py`); DIAGNOSE is **v0 BUILT**
(deterministic AI4I-rule root-cause with evidence trails — `services/diagnosis.py`; the causal twin stays
Stage 8 / G-019–G-020); INTERVENE is **v0 BUILT, sim-only** (shared deterministic policy
`services/intervention_policy.py` + `EmbodiedAgent.decide_intervention` → `Stage.start_maintenance`; PPO stays
Stage 7 / G-025); VERIFY was then **PLANNED** but is now **BUILT** (Stage 8 depth-hardening, 2026-06-14 —
`services/plan_verifier.py`; see below). Full HITL/durable-workflow integration of VERIFY stays Stage 11/17.

**Stage 10 (2026-06-13) — Explainable / auditable decisions (the trust leg).** `backend/ml/explainability.py`
de-mocked from random-fabricated SHAP/attention/counterfactuals to REAL explanations via new
`backend/ml/failure_explainer.py`: **exact TreeSHAP** for the XGBoost failure predictor (XGBoost native
`pred_contribs`, no `shap` lib; invariant `sum(shap)+base == model raw margin` holds exactly) + a **real
counterfactual** (guided minimal-change search scored by the actual model — "what would make this machine safe").
Honest-empty for generic decisions with no model behind them; honest `ModelUnavailableError`. **Audit 383 → 364**
(removed ~19 `random.uniform` sites). SHAP is exact for the model, but the model is AI4I-proxy (G-035). ADR
`2026-06-13_explainability_shap_counterfactual.md`.

**Stage 9 (2026-06-13) — Quality & Inspection vision capability (N-domain, G-016 ADVANCED).** `backend/ml/vision_model.py`
de-mocked to **real pretrained YOLOv8n** inference (honest `ModelUnavailableError`, no fabricated detections; the
`video_processor` mock loop removed). New **defect classifier** (`backend/ml/defect_classifier.py` +
`training/stage_09_defect/`) trained on the real **NEU-CLS** benchmark — **88.2% test acc / 0.881 macro-F1 vs
16.7% baseline**. Honest scope: NEU-CLS steel surfaces are a PROXY for warehouse imagery (re-fit before pilot,
G-035); the Quality **head-agent** integration + real-time reject path stay Stage 11+/17. **First strict audit
decrease since Stage 6: 396 → 383.** ADR `2026-06-13_vision_defect_detection.md`.

**Stage 8 (2026-06-13) — PREDICT deepened to a learned WORLD MODEL + CAUSAL step begun.** `backend/ml/world_model.py`
is now a real LSTM **time-to-failure (TTF) forecaster** (G-019 RESOLVED): TTF MAE **0.067 min vs naive 2.979 (+97.8%)**,
trained on SimWorld rollouts (`backend/training/stage_08_world_model/`). This is the timing signal Stage-7 RL lacked
("LSTM predicts M fails in ~N min"). The CAUSALLY-REASON step (step 2) begins with **causal attribution v1** in
`services/diagnosis.py::attribute_cause` — a do-operator counterfactual over the KNOWN SimWorld SCM classifying
machine-local vs externally-influenced (G-020 PARTIAL). **Honest boundary:** known-structure counterfactual + a real
TTF model — NOT learned causal discovery and NOT neuro-symbolic VERIFICATION (step 3), which stay PLANNED
(G-020 → Stage 17 / research spike). ADR `2026-06-13_world_model_causal_diagnose.md`.

**Stage 8 DEPTH-HARDENING (2026-06-14) — PREDICT benchmark-grade, learned causal discovery BUILT, VERIFY BUILT.**
Operator depth mandate. Three deepenings: (1) **PREDICT** — `backend/ml/rul_transformer.py`, a Transformer
encoder trained on the REAL **C-MAPSS FD001** RUL benchmark → **test RMSE 13.80 / NASA 372** (beats the CNN 18.45
and LSTM 16.14 literature baselines, competitive with DCNN/Transformer SOTA; +66% vs naive). Real, comparable
benchmark number replacing the near-trivial SimWorld signal (the SimWorld TTF LSTM is retained for the live loop).
(2) **CAUSALLY-REASON** — `backend/ml/causal_discovery.py` runs **learned causal discovery** (causal-learn PC,
Fisher-Z) and **recovers crack_proximity as the common-cause hub** (skeleton F1 0.75, 4/5 hub edges, proximity =
max-degree node), empirically validating the known-SCM counterfactual in `diagnosis.attribute_cause` (now annotated
with that support). (3) **VERIFY (step 3) — now BUILT**: `backend/services/plan_verifier.py`, the symbolic
constraint engine (crew capacity / maintenance precondition / throughput floor / SIL critical-redundancy) that
**rejects unsafe plans** — the symbolic half of neuro-symbolic verification (neural proposer ⟂ symbolic verifier);
composes with the Stage-17 actuator wrapper. Audit holds 364 (`--no-baseline-drop`, additive). G-020 advances:
learned discovery + neuro-symbolic verify BUILT at sim scope (real-fleet re-discovery = G-035). ADR
`2026-06-14_depth_08_world_model_causal_verify.md`.

> **Stage 39 (2026-07-18, G-051) — the Stage-6 slice VERIFY gate is now BINDING (no longer a no-op).** The Stage-6
> `slice_runner._build_plant_state` previously RELAXED all rejecting contracts (unlimited crew, 0.0 throughput floor,
> unlimited critical-offline), so the verifier could only attach provenance. It now binds `throughput_floor_frac=0.6`,
> `max_concurrent_critical_offline=1` (SIL), and `available_crew = crew_total(2) − stages_in_maintenance`, so the slice
> path can GENUINELY REJECT an unsafe plan (proven for a throughput-floor breach AND a critical-redundancy breach), while
> the normal safe maintenance still passes (the measured Stage-6 A/B is preserved). Slice decisions also now persist to
> `decision_logs` (Art-12, G-045). ADR `2026-07-18_stage39_slice_persistence_verifier.md`.

**Stage 9 DEPTH-HARDENING (2026-06-14) — N-domain vision deepened (G-016 ADVANCED).** The defect classifier
(`backend/ml/defect_classifier.py`) is now **ResNet18 transfer learning** (pretrained ImageNet, fine-tuned on real
NEU-CLS RGB 128×128) → **test acc 99.3% / macro-F1 0.993** (was 88.2% toy CNN; +11.1 pt, SOTA-competitive), same
seed-9 held-out split (no leakage). Strengthens the Quality & Inspection leg of the N-domain self-healing capability
(head-agent integration + reject actuator stay Stage 11+/17; benchmark scope, real-image re-fit = G-035). ADR
`2026-06-14_depth_09_defect_transfer_learning.md`.

**Stage 7 DEPTH-HARDENING (2026-06-14) — INTERVENE: RL now genuinely beats rules (G-025 ADVANCED++).** The v0
from-scratch PPO tied the near-optimal rules in the simple single-crew regime (honest negative, retained). The
deepened version — **SB3 sb3-contrib MaskablePPO with action masking** (`backend/ml/group_scheduler_rl.py`) on a
richer **group + opportunistic maintenance** scheduling MDP (`training/stage_07_rl_intervention/group_env.py`) —
**genuinely beats the best hand-coded rule**: CRN-paired held-out **−125.1 vs −137.4, +12.36 (95% CI [6.0,18.71])**,
36/50 wins. The regime (batching across zones + timing around demand windows) is where DRL provably beats greedy
(research §16.1). Scheduling-MDP scope; live-loop wiring + real plant = G-025/G-035. ADR
`2026-06-14_depth_07_maskable_ppo_group.md`.

**Stage 10 DEPTH-HARDENING (2026-06-14) — trust/recourse leg deepened.** `backend/ml/dice_explainer.py` adds
**DiCE diverse multi-feature counterfactuals** (dice-ml; several actionable recipes that each flip at-risk→safe,
varying only base physical features so derived features stay consistent — each re-verified vs the real model) +
**global SHAP** (mean |Shapley| over a reference sample). Wired into `failure_explainer.explain(..., diverse_cf=True)`
+ `global_importance()`, honest-unavailable. Deepens the explainable/auditable-decisions leg beyond the v0
single-feature counterfactual; no new weight (methods over the XGBoost model); AI4I-proxy (G-035). ADR
`2026-06-14_depth_10_dice_global_shap.md`.

**Stage 6 DEPTH-HARDENING (2026-06-14, increment 5/5) — the deepened loop is WIRED end-to-end.** The live slice
(`services/slice_runner.py::run_slice_step`) now runs the full loop: **predict → forecast TTF (Stage 8; on 90% of
at-risk predictions) → diagnose+causal (Stage 8B) → explain (Stage 10 exact-SHAP) → VERIFY (Stage 8C plan verifier,
in the execution path) → intervene**. Additive + availability-gated, so the measured A/B is preserved. **Honest
scope (independent review, G-051):** Stage 6 models *unlimited crew*, so its PlantState relaxes the
crew/throughput/redundancy contracts → in the slice's normal flow the verifier always approves (provenance + a
latent gate; it never actually rejects in Stage 6). The verifier's real REJECT behaviour is proven by
`test_plan_verifier.py` under a binding state and arms at Stage 7 (crew contention) / Stage 17. **Richer A/B (paired
bootstrap 95% CIs, 5 seeds/8 h):** unplanned downtime **−182 min, CI [93, 274] (significant)**; crack breakdowns
**−4.2, CI [3, 5] (significant)**; throughput −0.05 u/h, CI [−0.22, 0.12] (not significant — no cost). The VERIFY
leg is no longer built-but-unwired; the loop is genuinely predict→reason→verify→intervene. ADR
`2026-06-14_depth_06_slice_integration.md`. **This closes the Stages 6–10 depth-hardening pass (5/5 increments).**

**Stage 11 (increment 1, 2026-06-14) — the loop is now a DURABLE LangGraph runtime.** `backend/agents/runtime/`
runs the KB_25 loop as a deterministic, checkpointed `StateGraph` (observe → orient predict+TTF → diagnose
learned-causal → explain SHAP → decide → **verify (neuro-symbolic, now GENUINELY gating via a BINDING PlantState —
pays G-051 in the runtime)** → `interrupt()`-based HITL on SIL-1+ → execute (sim-only) → log), wiring the real
depth-hardened Stage-4-10 models as direct imports (they become MCP tools at 11.5). `EmbodiedAgent.coordinate(incident)`
is the thin public wrapper. Durable checkpointer (Postgres if available, else in-memory; honestly named). Stage 11
remains IN-PROGRESS (Postgres table + tracing + de-mock + remediations + independent review = continuation). ADR
`2026-06-14_stage11_langgraph_runtime_core.md`.

**Stage 7 (2026-06-12) — INTERVENE deepened with a real PPO substrate.** `backend/ml/intervention_rl.py` + `backend/training/stage_07_rl_intervention/` add a from-scratch PPO (torch CPU; capacity-constrained, event-driven `InterventionEnv`) with a hard SAFETY SHIELD (forces maintenance on a critical-proximity machine regardless of the sampled action). Honest measured result (CRN-paired, 95% CI; G-046): the deterministic rules are near-optimal at v0 (0.375 crack-breakdowns) and PPO+shield (0.875) does NOT beat them, so **rules remain the default chooser** — the PPO ships as the learnable substrate for the richer Stage-8/11 recovery action space (self-repair / robot-fixer dispatch / backup-online / slow+catch-up). "The better policy wins, not the fancier one." ADR `2026-06-12_rl_intervention_ppo.md`; advances G-025. Measured closed-loop value (KB_23 §Stage 6):
**−201 min unplanned downtime per 8 sim-hours (−42.8%), 92% of crack breakdowns prevented**, 3-seed A/B.
Diagnose/causal/verify/intervene deepenings (steps 1b–4) remain to build. This KB is the contract the Stages
7/8/11/13/16/17 implementations build to, folding in the gaps-ledger rows (G-005, G-006, G-016..G-024).

**Stage 29 (2026-07-12) — ACTIVE DIAGNOSIS (§1b) IMPLEMENTED (G-026 RESOLVED).** `backend/conversation/active_diagnosis.py`
turns the §1b probe→reason loop from a no-op into a principled **information-gain (entropy-reduction) test-selection**
policy (research §40.3, the SOTA active-diagnosis formulation): the coordinator maintains a belief over fault
hypotheses (one per candidate agent + `no_fault`), selects the `diagnose.request` with maximum mutual information
`I(hypothesis; probe_outcome)`, reads the `diagnose.report` (a real health vector; timeout/exception ⇒ anomalous =
fault), does an EXACT Bayes update, and COMMITS only when a posterior clears the confidence threshold — otherwise
ABSTAINS/escalates. A wrong prediction is caught by the round-trip; misdiagnosis is a recorded outcome. Wired over
the live sim at `POST /factory/diagnose`. Also Stage 29: **conversational operational QA** (`/factory/ask` — grounded
in Art-12 traces + GraphRAG + live sim, Verifier honest-empty, G-022) and **NL problem injection** (`/factory/inject`
— NL → validated `InjectedIncident` → the same validator-gated loop, Hard Rule 3 preserved, G-023). Free/local
(Groq→Ollama). ADR `2026-07-12_stage29_conversational_factory_intelligence.md`.

**Stage 30 (2026-07-12) — INTERVENE (step 4) LIVE-WIRED end-to-end (G-005 + G-025-tail + G-036 RESOLVED).** The loop
now has a real recovery ACTION and a live RL recommender: (1) **repair-robot dispatch** (`agents/repair/dispatch.py`)
— a broken machine triggers a deterministic Contract-Net award over REAL robot state (availability/battery/queue),
safety-gated (`repair_dispatch` contract, Hard Rule 3), and the robot applies `Stage.repair_assist` (interruptible
SimPy repair) cutting remaining downtime — **paired A/B: −47.9% downtime, CI [7696,12733]s excludes 0**; (2) the
Stage-7 **MaskablePPO** is consulted by the `decide` node as a **SHADOW recommender** (`agents/runtime/rl_shadow.py`,
`RUNTIME_RL_SHADOW=1`) — RL-vs-rule agreement logged, NEVER acted, the verifier/validator remain the shield (SOTA
shadow-mode deploy, research §41.2); (3) the operator-facing 7-day **demand forecast is SERVED** from the real LSTM /
empirical stats (`services/demand_forecast_service.py`), replacing a placeholder that carried a fabricated confidence.
Free/local; no new deps. ADR `2026-07-12_stage30_live_wire_self_healing_loop.md`.

## Last verified

2026-05-31, system-designer + agentic-governance-engineer. Research-grounded (§13); no engine code yet.

## N-domain extension: supply chain (Stage 26, 2026-07-03)

The engine's loop now runs a SECOND domain beyond the production line. `backend/agents/supply_chain/` maps the
KB_25 steps onto supply-chain operations over the REAL SimWorld + ISA-95 graph:

| KB_25 step | Supply-chain realisation |
|---|---|
| PREDICT | demand estimate — real `demand_forecaster.pt` (proxy, G-035) or labelled empirical stats; (s,S) reorder policy with the full stochastic-lead ROP |
| DIAGNOSE | disruption monitor: supplier-failure (→ quarantine), streaming latency robust-Z (2x-median guard), persistent-starvation stockout, demand spike |
| REASON/COORDINATE | deterministic Contract-Net (announce → sealed bids from OBSERVED supplier stats → min-cost award + counter-based exploration rounds) |
| VERIFY | the static `supply_chain_order` SafetyContract through `safety/validator.validate()` BEFORE any order effect (Hard Rule 3) |
| INTERVENE | real `supplier.order(on_fulfil=...)` effects; genuine fulfilments feed stage buffers (`SimWorld.deliver_material`) |
| EVIDENCE | every CFP/award = signed `audit_chain` row + OTel span; disruptions → incidents via the Stage-25 exactly-once router into the runtime |

Measured (10 paired seeds x 160 ticks, mid-run disruption; `backend/training/evals/results/supply_ab.json`):
vs the greedy baseline — stockouts −51% (106.3→52.2), bullwhip −98% (74.3→1.21), material −73% (4918→1305),
equal holding; all CIs exclude 0. HONEST: SimWorld study, not real-supply-chain evidence (G-035). Research §37.

## N-domain extension: facilities / energy (Stage 38, 2026-07-18) — G-018 RESOLVED

The engine's loop now runs a THIRD domain. `backend/agents/facilities/` maps the KB_25 steps onto industrial energy
management over the sim's REAL per-stage `nominal_kw` (`simulation/calibration.py` — intake 2.0 → machining 22.0 kW):

| KB_25 step | Facilities/energy realisation |
|---|---|
| PREDICT | the naive-schedule demand curve from real per-stage kW + a documented HVAC/lighting baseline (`signals.py`) |
| DIAGNOSE | an approaching **demand-charge breach** (the naive-schedule peak > the contracted `demand_cap_kw`); no cap ⇒ run proactively (we do NOT invent an "anomaly" from peak>process_kw — that would be theatre) |
| REASON/OPTIMISE | a **real MILP** (`scipy.optimize.milp`/HiGHS, `optimizer.py`): minimise `Σ(kW·h·ToU_price) + demand_charge·peak` s.t. the production floor (`Σ_t x[j,t]=required_slots[j]`) + per-load windows + `peak ≥` every slot's aggregate |
| VERIFY | the static `energy_load_shift` SafetyContract through `safety/validator.validate()` — preconds: production floor met, windows respected, peak-not-increased; invariant: energy conserved (Hard Rule 3) |
| INTERVENE | the gated day-ahead schedule (peak-shave + load-shift); honest 0% when a facility is fully constrained |
| EVIDENCE | every cycle = signed `audit_chain` row (`energy.load_shift`) + the `POST /facilities/optimize-energy` surface (Art-12) |

Measured (parametric scenario sweep, `backend/training/evals/results/energy_ab.json`): MILP vs naive-baseline —
**peak −22.1% mean (max 58.9%), cost −7.6% mean (max 18.8%), all production floors held** (min 0% where a load is
fully constrained — honest, no fabricated saving). HONEST: SimWorld study over documented tariff numbers, not
real-facility/metered evidence (real utility tariff + meter = G-035, buyer-blocked). Research §49. No new deps.
