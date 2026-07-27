---
name: Evals & Benchmarks
description: Evaluation suites, datasets, baselines, quantitative thresholds and CI gates per stage; the measurable contract behind PRD success criteria
type: spec
last-updated: 2026-06-13
---

# KB_23 — Evals & Benchmarks

## Purpose

Own the *measurable* contract for the product: which evaluation suites exist, what datasets/baselines they run
against, what numeric thresholds gate a stage close, and where each is enforced in CI. This is the operational
backing for [PRD v2.1 §v2.1.2](../PRD-ai-embodied-agent-v2.1.md) and v2.0 §11 success criteria. KB_10 owns the
latency budget; this file owns the eval methodology that proves we meet it.

## Source of truth

- PRD v2.1 §v2.1.2 (headline SLO tables) and v2.0 §11 (base success criteria).
- Per-stage acceptance criteria in `tasks/STAGE_NN_*.md` (each criterion must be testable).
- Eval corpora + results land in `backend/training/evals/<suite>/` with `results.json` (Stage 20 onward).
- CI gates in `.github/workflows/` (`audit`, `safety-contract-tests`, `a2a-conformance`, `mcp-conformance`,
  `phoenix-evals`). Where a suite is not yet implemented, the row is marked **(spec; Stage NN)**.

> Honesty rule (`docs/honesty-accuracy-prompt.md`): every threshold here is a **target we commit to verify**.
> A target is only "measured" once a `results.json` exists and the stage that owns it has closed. Until then it
> is labelled a design target.

## Body

### 1. Evaluation taxonomy

| Class | Question it answers | Primary metric(s) | Where |
|---|---|---|---|
| Performance / latency | Is it fast and high-throughput enough? | p50/p95 latency, units/hr, OEE | KB_10 budget + `tests/test_sim_calibration.py`, OTel spans |
| Model quality | Are the ML models accurate? | task-specific (F1, MAE, mAP, RUL error) | model cards + `backend/training/evals/` |
| Safety | Does every actuator path go through the gate? | gate coverage %, fail-safe correctness | `safety-contract-tests` CI |
| Security / robustness | Does it resist prompt injection / abuse? | block-rate on adversarial corpus | Phoenix `phoenix-evals` CI |
| Compliance | Can we produce regulator-grade evidence? | Annex IV gen time, chain-verify pass | `generate-annex-iv-doc.py`, `verify-audit-chain.py` |
| Crypto-agility | Can we rotate/swap keys & providers safely? | rotation time, downtime, swap-with-no-code-change | rotation + HSM-swap drills |
| Interop | Do we conform to the standards & federate? | VDA 5050 schema pass %, A2A round-trip | conformance suites |
| Dashboard / ops | Can an operator see & act in time? | event→view latency, alarm latency | Stage 12.5 e2e |

### 2. Headline thresholds (mirror of PRD v2.1 §v2.1.2 — single source for both)

Performance/SLO: simulator throughput ~500 units/hr (±10%); inject→WS p95 ≤ 250 ms; agent decision p50 ≤ 2 s /
p95 ≤ 5 s; uptime ≥ 99.5%; pilot cycle-time −25–30%, carbon −15–20% (design targets).
Trust/safety/compliance: audit-chain verify passes end-to-end; Annex IV pack ≤ 60 s; **safety-gate coverage
100%**; prompt-injection block **≥ 99%** (OWASP LLM01 + NIST RMF Agentic); **0** cross-namespace memory reads;
VDA 5050 conformance **100%**; A2A federation 2-instance signed round-trip.
Crypto-agility: hybrid ML-KEM-768+X25519 on 100% external boundaries; rotation ≤ 15 min, **0** data-plane
downtime; **HSM provider swap with no code change** (config only), chain still verifies; algorithm swap drill
(Stage 25). Dashboard: event→view p95 ≤ 1 s; alarm p95 ≤ 2 s; 100% events tagged `actor_class`; signed report
export ≤ 10 s.

### 3. Datasets & baselines (real, license-pinned via DVC; verify in KB_03)

Evals must run against pinned datasets/corpora, not ad-hoc samples:
- **Prompt-injection / agentic-abuse:** OWASP LLM Top-10 LLM01 corpus + NIST AI RMF Agentic Profile attack
  vectors (assembled into `backend/training/evals/prompt_injection/`). Baseline = unguarded model block-rate.
- **Defect / vision (Stage 5):** dataset + baseline per its model card (e.g. NEU-DET / MVTec-class) — see KB_02/KB_03.
- **Forecasting / RL / energy (Stages 6, 6.5, 7):** per-model card datasets; baseline = naive/persistence model.
- **VDA 5050 conformance:** official VDA reference message fixtures (schema validation, not a learned metric).
- **Battery RUL (Stage 6.5):** BatteryLife dataset (CARD-attested per source; see research log §10).

Each ML threshold is meaningful only **relative to a stated baseline**; "X% accuracy" with no baseline is a
theatrical metric and is rejected at audit. New weights require `<model>.metrics.json` + a model card (CLAUDE.md
rule 7).

### 4. CI enforcement map

| Gate (CI job) | Enforces | Active from |
|---|---|---|
| `audit` | `.audit-baseline` non-increase (theatrical-fallback count) | Stage 1 |
| `safety-contract-tests` | every `actuator.*` span preceded by `safety.validate.*` span | Stage 17 |
| `phoenix-evals` | prompt-injection block-rate ≥ threshold | Stage 20 |
| `a2a-conformance` | signed agent-card round-trip between 2 instances | Stage 14 |
| `mcp-conformance` | every MCP tool has a schema test | Stage 11.5 |
| `check-model-cards` | new weights have metrics.json + model card | Stage 4+ |
| `verify-audit-chain` | hash-chain + signature integrity | Stage 13.5 |

### 5. Eval cadence

Per-PR: `audit`, model-cards, smoke. Per-stage-close: the stage's owned thresholds must pass (acceptance
criteria are the gate). Per-10-stages (CTO checkpoint): cross-cutting eval review. Pilot (Stage 22) and Stage 25:
the live drills (HSM swap, key rotation, algorithm swap, Annex IV dry-run).

### 6. Anti-gaming rules

- No eval may use `random.*` to manufacture a passing number (audit catches it).
- Thresholds tighten or hold across stages; loosening a threshold requires an ADR.
- A target with no dataset + baseline + test path is not a target — it's a wish; it does not gate a close.

### Stage 4 — Predictive Maintenance eval (MEASURED 2026-06-01)

| Metric | Value | Baseline | Notes |
|---|---|---|---|
| ROC-AUC | **0.972** | 0.5 (random) | held-out test, n=1500 |
| PR-AUC | **0.679** | 0.034 (= positive rate) | real skill; imbalanced (3.4% pos) |
| Recall @ F1 thr (0.934) | 0.61 | — | catches 31/51 failures; misses ~39% → recall-tune G-033 |
| Precision @ F1 thr | 0.61 | — | 20 false positives |
| Leakage | none | — | leaky cols dropped + stratified split (verified) |

Dataset AI4I 2020 (KB_03); model `pdm_failure_predictor` (KB_02). The "no metric without a baseline" rule is
honoured (baseline = positive rate). This is the first MEASURED row; earlier suites remain spec.

### Stage 5 — Demand Forecasting eval (MEASURED 2026-06-01)

| Metric | Value | Baseline | Notes |
|---|---|---|---|
| MAE (rides/h) | **32.9** | persistence 80.9 | held-out latest period |
| RMSE | 52.4 | — | — |
| MAPE | **21.0%** | — | v2 (cyclical+log+gridsearch) vs v1 23.4% |
| Improvement vs persistence | **+59.3%** | 0% | also beats seasonal-naive (81.1) |

Dataset UCI Bike Sharing (KB_03); model `demand_forecaster` (KB_02). Leakage-free chronological split. Baselines
stated (the "no metric without a baseline" rule honoured). Second MEASURED eval (after PdM).

### Stage 6 — Vertical Slice v0 closed-loop A/B (MEASURED 2026-06-12)

3 seeds (42/43/44) × 8 sim-hours per arm; identical seeds + 5-crack campaign on rotating machines; arms differ
ONLY by the `SliceLoop` (predict→diagnose→intervene) being attached. Harness: `backend/scripts/run_slice_ab.py`;
report: `backend/training/evals/stage06/results.{json,md}`.

| Metric (mean of 3 seeds) | Loop OFF (baseline) | Loop ON | Measured delta |
|---|---|---|---|
| Unplanned downtime (min / 8 h) | 470.27 | 268.83 | **−201.44 (−42.8%)** |
| Total downtime incl. planned maintenance (min) | 470.27 | 319.49 | **−150.78 (−32.1%)** |
| Crack-induced breakdowns | 4.33 | 0.33 | **92% prevented** |
| Planned maintenances (the prevention cost) | — | 4.67 | counted against ON |
| Throughput (completed orders/hr) | 6.96 | 6.92 | −0.04 (≈unchanged) |

Honest readings: the win is **availability**, not throughput (plant is order-arrival-limited at this calibration);
one crack in three runs slipped through; the −32.1% total-downtime figure already pays for the interventions.
**Variance caveat (independent review, 2026-06-12):** the downtime delta is high-variance — on auditor seed 77
(4 sim-h) it came out slightly NEGATIVE (−3.4 min) while crack prevention held at 100% (3/3). The **robust
headline is crack-breakdowns prevented (92–100%)**; downtime minutes need CRN pairing + confidence intervals
(G-046, Stage 7). All numbers are sim-measured under calibrated assumptions (G-035 gates real-world claims).
Telemetry is simulator-generated by construction (physics-motivated AI4I-unit mapping, KB_05); the brain is the
real Stage-4 XGBoost (proxy-trained — G-035 still gates production claims). Anti-gaming: the harness reports the
delta, never asserts its sign; both arms share seeds and code. Third MEASURED eval.

### Stage 7 — RL intervention policy, 3-way paired eval (MEASURED 2026-06-12; resolves G-046)

8 paired CRN seeds (same crack campaign per arm), capacity-1 maintenance crew, 5 cracks, 2 sim-hours, event-driven.
Harness: `backend/training/stage_07_rl_intervention/eval.py`; report `backend/training/evals/stage07/results.{json,md}`.

| Chooser | Mean crack-breakdowns (±95% CI) |
|---|---|
| no_intervention | 4.0 ± 0.52 |
| **rules_priority (default)** | **0.375 ± 0.36** |
| ppo_shield | 0.875 ± 0.25 |

Paired PPO−rules breakdown diff: **+0.5 ± 0.37** (PPO slightly MORE breakdowns; CI excludes 0). PPO training return
improved −160.8 → −134.0 (`training_learned=True`; beats no-intervention). **Honest finding:** the rules are
near-optimal at v0 scope and PPO does NOT beat them → **rules remain the default chooser** ("the better policy
wins, not the fancier one"). PPO ships trained + safety-shielded as the Stage-8 substrate. G-046 RESOLVED
(CRN pairing + CIs implemented here); the harness reports the measured delta, never asserts a winner; risk signal
= ground-truth proximity in this sim eval (real-telemetry re-fit gated by G-035). Fourth MEASURED eval.

### Stage 8 — World model TTF forecasting (MEASURED 2026-06-13; G-019)

LSTM time-to-failure forecaster trained on SimWorld crack rollouts (`backend/training/stage_08_world_model/`);
report `backend/training/evals/stage08/results.{json,md}`.

| Metric | Learned | Naive baseline (mean-TTF) | Improvement |
|---|---|---|---|
| TTF MAE — held-out val (min) | **0.067** | 2.979 | **+97.8%** |
| TTF MAE — fresh seeds 60–64 (min) | **0.070** | 3.230 | **+97.8%** |

Genuine, reproducible win on held-out AND disjoint fresh seeds (not seed-specific). Honest: crack ETA is
randomised so TTF is under-determined by a snapshot — the LSTM reads the degradation *rate* across a 6-sample
window (legitimate temporal inference, not leakage). Clean low-noise simulator → the 0.067-min figure is a sim
number, not a real-world claim (G-035). Companion causal attribution v1 (`diagnosis.py`) is known-SCM
counterfactual (G-020 partial; learned discovery + neuro-symbolic verify deferred → Stage 17). Fifth MEASURED eval.

### Stage 9 — Surface-defect classifier (MEASURED 2026-06-13; G-016)

CNN on the real NEU-CLS benchmark (`newguyme/neu_cls`, 6 steel-surface defect classes), grayscale 64×64;
training `backend/training/stage_09_defect/`.

| Metric | Learned | Baseline (majority class = 1/6) |
|---|---|---|
| Test accuracy | **0.882** | 0.167 |
| Test macro-F1 | **0.881** | — |

Held-out stratified split (1152 train / 288 test). Real public dataset, real measured result — **not** 100%
(an honest tiny-CNN number; NEU-CLS SOTA ~99% needs larger nets), gap stated not hidden. PROXY domain (steel ≠
warehouse imagery) → re-fit before pilot (G-035). Companion: `vision_model.py` de-mocked to real YOLOv8n
inference (audit 396→383). Sixth MEASURED eval.

### Stage 10 — Explainability: exact TreeSHAP verification (MEASURED 2026-06-13)

Not an accuracy metric — a correctness invariant. The failure-predictor explanations
(`backend/ml/failure_explainer.py`) use XGBoost native TreeSHAP; the exactness invariant is asserted in CI:

| Check | Result |
|---|---|
| `sum(shap_values) + base_value == model raw margin` | **exact** (1.3735 ≈ output_margin 1.3736; tol 1e-3) — `test_shap_is_exact_sum_equals_margin` |
| Top driver for a worn machine | **Tool wear [min]** (increases_risk) — physically correct |
| Counterfactual flip | **verified by the real predictor** (applying the minimal change drops p_fail < threshold) |
| Honest-empty for generic (no-model) decisions | `[]`, no fabrication |

XGBoost applies a `base_score` offset so `sigmoid(margin) ≈ p_fail` within ~0.02 (stated, not hidden). SHAP is
exact for the model; the model is AI4I-proxy (G-035). No `shap`/`dice-ml` dependency. Seventh MEASURED/verified eval.

### Stage 8 depth-hardening — RUL Transformer (real C-MAPSS) + learned causal discovery (MEASURED 2026-06-14)

**(a) RUL Transformer on real C-MAPSS FD001** (`ml.rul_transformer`; eval `eval_cmapss.py`):

| Metric | Value | Reference |
|---|---|---|
| Test RMSE (official 100 engines) | **13.80** | naive mean-RUL baseline 40.55 (+66%) |
| Test NASA score | **372** | naive 18,366 |
| Literature FD001 RMSE (cited, not reproduced) | CNN 18.45 · LSTM 16.14 · DCNN 12.61 · Transformer 11.27 | our 13.80 beats CNN/LSTM, competitive with SOTA |

Single eval on the official test set after best-val selection (no test peeking); piecewise RUL cap 125; 14
sensors; window 30. Real public benchmark — validates the architecture, not the plant (real-fleet = G-035).

**(b) Learned causal discovery** (`ml.causal_discovery`, causal-learn PC + Fisher-Z; report
`training/evals/stage08/causal_discovery.json`):

| Metric | Value | Notes |
|---|---|---|
| Skeleton F1 vs known SCM | **0.75** | 100 seeds / 8,364 samples |
| Proximity hub edges recovered | **4 / 5** | rpm, torque, wear, air_temp |
| Proximity = max-degree node | **True** | robust invariant (stable across sample sizes) |

Empirically validates the known-SCM counterfactual in `diagnosis.attribute_cause`. Honest limits: ~3 K
temperature edges near the noise floor; linear Fisher-Z can't fully screen semi-nonlinear couplings. Eighth
MEASURED eval. Companion VERIFY step (`services.plan_verifier`) is unit-verified (`test_plan_verifier.py`).

### Stage 9 depth-hardening — defect classifier transfer learning (MEASURED 2026-06-14)

`ml.defect_classifier` v2 (`training/stage_09_defect/train_transfer.py`): pretrained ResNet18 fine-tuned on real
NEU-CLS (RGB 128×128, layer4+fc), SAME seed-9 held-out split as v1 (no leakage).

| Metric | v2 (ResNet18 transfer) | v1 (tiny CNN) | baseline |
|---|---|---|---|
| Test accuracy | **0.993** | 0.882 | majority 0.167 |
| Test macro-F1 | **0.993** | 0.881 | — |
| Best val accuracy | 1.000 | — | — |

**+11.1 pt** genuine held-out gain → SOTA-competitive (NEU-CLS deep-model SOTA ~99%). Per-class P/R + confusion
matrix in `models/defect_classifier.metrics.json`. Benchmark scope; real-fleet re-fit = G-035. Ninth MEASURED eval.

### Stage 7 depth-hardening — MaskablePPO beats rules, CRN-paired (MEASURED 2026-06-14)

`ml.group_scheduler_rl` / `training/stage_07_rl_intervention/train_sb3.py` — SB3 sb3-contrib **MaskablePPO** on the
richer `GroupMaintenanceEnv` (group batching + opportunistic demand + crew contention); 50 held-out seeds, CRN-paired.

| Policy | Mean return | vs best rule (paired) |
|---|---|---|
| **MaskablePPO** | **−125.1** | — |
| threshold/batch rule (best) | −137.4 | RL **+12.36**, 95% CI **[6.0, 18.71]**, 36/50 wins |
| greedy-urgent rule | −167.6 | RL +42.51, CI [36.6, 48.4], 48/50 wins |
| no-op (floor) | −828.9 | — |

**First RL in the project to genuinely beat the best hand-coded rule** (paired 95% CI lower bound > 0) — the depth
payoff over the v0 from-scratch PPO (which honestly tied rules in the simpler regime; retained). Scheduling-MDP
scope (live-loop wiring + real plant = G-025/G-035). Re-eval `eval_sb3.py`. Tenth MEASURED eval.

### Stage 10 depth-hardening — DiCE diverse counterfactuals + global SHAP (MEASURED 2026-06-14)

`ml.dice_explainer` (dice-ml): diverse multi-feature actionable counterfactuals over the XGBoost predictor, varying
only base physical features (derived features recomputed → physically consistent), each re-verified vs the real model.

| Check | Result |
|---|---|
| At-risk machine (p_fail 0.966) → DiCE recipes | **4 diverse**, all verified `flips=True` (e.g. torque −35% AND tool-wear −62% → p 0.030) |
| Multi-feature recourse (vs v0 single-feature) | present in the diverse set |
| Global SHAP top drivers (mean abs Shapley) | power_w, rotational speed, torque |

Deepens the trust/recourse leg beyond the v0 single-feature counterfactual. No new weight (methods over the existing
XGBoost model); still AI4I-proxy (G-035). 13 DiCE/explainability tests pass. Eleventh MEASURED/verified eval.

### Stage 6 depth-hardening — deepened loop A/B with paired bootstrap 95% CIs (MEASURED 2026-06-14)

The deepened slice loop (`predict→forecast_ttf→causal_diagnose→shap_explain→neuro_symbolic_verify→intervene`),
5 seeds × 8 sim-hours, CRN-paired bootstrap (5000 resamples) over per-seed OFF−ON differences:

| metric (OFF−ON; throughput ON−OFF) | mean | 95% CI | significant? |
|---|---|---|---|
| unplanned downtime (min) | **−182.4 saved** | [93.4, 274.0] | **yes** |
| total downtime incl. planned (min) | −132.4 saved | [47.4, 222.0] | yes |
| crack-induced breakdowns | −4.2 prevented | [3, 5] | yes |
| throughput (units/hr) | −0.05 | [−0.22, 0.12] | no (no cost) |

The deepened loop significantly cuts unplanned downtime + crack breakdowns with **no significant throughput cost**;
the neuro-symbolic verifier approves the single-machine maintenance so the measured win is preserved. Sign reported,
not asserted (honesty rule). Twelfth MEASURED eval — closes the Stages 6–10 depth-hardening pass.

### Stage 11 / 11.5 / 12 — runtime, MCP, memory (VERIFIED 2026-06-14/15)

Not accuracy metrics — **conformance + integrity + behavioural** checks, all live-verified against the real Docker
stack (Postgres/pgvector@5544 + Neo4j@7687 + Redis):

| Suite | Check | Result |
|---|---|---|
| Stage 11 runtime | durable PostgresSaver: checkpoint/super-step persists + fresh-saver reload; full suite | `test_postgres_checkpointer_persists_when_available` passes vs real PG; **186→208→221 passed** across 11/11.5/12 |
| Stage 11.5 MCP (`mcp-conformance`) | tools/list == documented manifest; input/output schema validates; real tool calls; real Postgres decision-log round-trip; 14-tool runtime mount | **22 passed / 1 skipped** (real stdio client) |
| Stage 12 memory — isolation | 0 cross-namespace reads (`CrossNamespaceAccessError` before any I/O) — **the PRD "0 cross-namespace memory reads" target, now MEASURED** | enforced + tested (`test_namespace_isolation.py`) |
| Stage 12 memory — audit integrity | append-only (UPDATE/DELETE blocked by triggers) + `hash=SHA-256(prev_hash‖payload)` chain verifies | `verify-audit-chain.py` **OK (29 rows)**; independent code path confirms |
| Stage 12 memory — episodic recall | real semantic search (sentence-transformers) ranks the relevant memory first | score 0.744 on a held query; runtime run-2 recalls run-1's memory |

These move three PRD trust/safety targets from **spec → measured**: 0 cross-namespace reads, audit-chain verify
end-to-end, and MCP per-tool schema tests. Real ML-DSA-65 audit signing is still Stage 13.5 (placeholder until then).

### Owed: agentic + security eval suites (still SPEC — Stage 20)

The **runtime-behaviour + adversarial** evals remain design targets, owed at Stage 20 (`phoenix-evals`):
prompt-injection / OWASP-LLM01 + NIST-RMF-Agentic + **OWASP Top-10 for Agentic Apps** block-rate **≥99%**;
**safety-gate coverage 100%** (Stage 17 wrapper); tool-selection / action-completion / reasoning-coherence
(**Galileo-depth, G-008**); and the MCP/agent **zero-trust** controls (per-tool capability authz, agent-identity
verification — G-063/G-064). Headline product SLOs (decision p50≤2 s, inject→WS p95≤250 ms, uptime 99.5%, pilot
−25-30% cycle-time) remain **design targets** until a pilot measures them (G-035 gates real-world claims).

## Detector hardening (Stage 31, 2026-07-13) — G-077 + G-064-tail + CTO-#5 R5

The Stage-20 prompt-injection detector (heuristic + semantic-kNN) is hardened with a LEARNED third tier
(`security/injection_classifier.py` — logistic-regression over bge-small embeddings, trained on the real 217-example
OWASP-LLM01 corpus), which becomes the PRIMARY calibrated semantic decision in `prompt_guard.inspect()` (the kNN is an
honest fallback), plus an optional free-LLM judge escalation for the uncertain band.

| detector | detection rate | false-positive rate | protocol |
|---|---|---|---|
| Stage-20 baseline (heuristic + kNN) | 0.9935 | 0.0156 | full corpus |
| learned tier alone | 0.9935 | **0.0** | **held-out 5-fold CV** |
| **combined (heuristic OR learned)** | **1.0** | **0.0** | **held-out 5-fold CV** |

The learned tier caught the 1 indirect-injection miss AND removed the 1 benign false-positive. Numbers are held-out CV
(the deployment artefact `models/injection_classifier.joblib` is fit on all data; metrics in
`models/injection_classifier.metrics.json` + card `compliance/model-cards/injection_classifier.md`). Persisted by
`training/evals/redteam/detector_hardening_eval.py` → `training/evals/results/detector_hardening.json`.

**Continuous behavioural anomaly monitor (G-064-tail)** — `security/behavioral_monitor.py`: the ONLINE (streaming)
counterpart of the Stage-25 nightly post-market sweep. Rolling robust-Z (median/MAD) over the runtime's real
per-incident behavioural features + explicit trajectory checks (loops / redundant actions / invalid tool args /
actuation>decisions), signed `behavior.anomaly` rows, honest `insufficient_history` below warmup; labelled eval
detection 1.0 / FPR 0.0. The binding actuation gate remains `safety/validator` (Rule 3) — detectors are defence-in-depth.

## Last verified

2026-07-13 (Stage 31 detector-hardening rows added; learned injection tier + continuous behavioural monitor measured by
held-out CV / labelled eval; `training/evals/results/detector_hardening.json`).
2026-06-15 (Stage 11/11.5/12 runtime+MCP+memory conformance/integrity rows added; agentic/security evals reaffirmed
owed at Stage 20 — research §20). Prior: 2026-05-31 + 2026-06-01 (Stage 4 PdM + Stage 5 demand evals measured) + **2026-06-12 (Stage 6 closed-loop A/B
measured)**, by agentic-governance-engineer + ml-engineer. The `audit` gate + Stage 2 calibration + Stage 4 PdM +
Stage 5 demand + Stage 6 slice A/B evals are live; other suites remain spec.
