---
status: done
stage: 08
slug: world_model_causal_diagnose
created: 2026-06-13
---

# Stage 08 — Learned World Model (time-to-failure forecasting) + Causal Attribution v1

> Deepen the PREDICT step (KB_25 step 1, gap G-019) from an instantaneous failure-risk score to a **learned
> world model that forecasts time-to-failure (TTF)** — KB_25's own example is *"LSTM predicts M fails in ~8 min."*
> TTF is exactly the timing signal Stage 7's RL lacked (it could not tell *when* to act). And begin the
> CAUSALLY-REASON step (KB_25 step 2, gap G-020) with a **bounded, honest causal-attribution v1**: counterfactual
> root-cause classification (machine-local vs externally-influenced) over the KNOWN SimWorld structural causal
> model, behind the SAME `Diagnosis` interface. Honest scope: this is a known-structure SCM + a real trained TTF
> model — NOT learned causal discovery and NOT neuro-symbolic verification (those stay PLANNED → Stage 17 / a
> later spike, per the ledger's "research spike before" note on G-020). Replaces the theatrical `world_model.py`
> stub. Cross-links: KB_25 §1/§2 · Stage 7 hand-off · ml-engineer SKILL (weights + card + honest eval).

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–10 + §5)

- [x] Read `KB_24_System_Design_HLD_LLD.md` + `KB_25_Causal_SelfHealing_Engine.md` (§1 loop, §2 DL stack — world model = step 1, causal DT = step 2). Aligned.
- [x] Read `audits/OPEN_GAPS_LEDGER.md`. Folded for Stage 8: **G-019** (learned world model — THIS stage's core), **G-020** (causal DT + counterfactual — PARTIAL here: known-SCM counterfactual attribution v1; deep causal-discovery + neuro-symbolic VERIFY deferred → Stage 17/spike), **G-027** (free-cost — honoured: torch CPU, SimWorld rollouts, no paid services).
- [x] **Free-cost only:** torch CPU + numpy + SimWorld rollouts; no LLM in this stage's loop; OSS/local only. No committed keys.
- [x] **Stage explainer HTML:** before close, write `research/stage-explainers/STAGE_08/index.html` (self-contained, honest BUILT/PARTIAL/PLANNED, real file paths + measured numbers).

## Pre-requisites

- Stage(s) closed: 2–7 (SimWorld, WS broker, failure predictor, demand, slice v0, PPO intervene substrate).
- Decision logs honoured: `2026-05-31_causal_self_healing_engine.md` (KB_25 steps 1–2), `2026-06-12_rl_intervention_ppo.md` (the TTF signal Stage 7 lacked). New ADR: `2026-06-13_world_model_causal_diagnose.md`.
- KB files at minimum version: KB_25 (intervene BUILT), KB_05 (telemetry), KB_23 (Stage 4/5/6/7 evals).
- Gaps pulled in: **G-019** (resolved here), **G-020** (advanced/partial here).

## Acceptance criteria

- [x] **AC1 — Learned world model (G-019), trained, free + local.** `backend/training/stage_08_world_model/` (rollout generator from SimWorld + `train.py` + `config.yaml`) produces a real LSTM that forecasts **time-to-failure (TTF, minutes)** from a window of machine telemetry. Saves `models/world_model_ttf.{pt,metrics.json}` (seed, hyperparams, training curve, eval-vs-baseline). Verified by the committed metrics + `test_world_model.py`.
- [x] **AC2 — Measured win vs naive baseline.** TTF **MAE on held-out rollouts beats a naive baseline** (mean-TTF predictor) — recorded in metrics + KB_23. (Supervised regression; a genuine measurable win, unlike a near-trivial decision problem.)
- [x] **AC3 — Honest world-model inference glue.** `backend/ml/world_model.py` rewritten: `WorldModel.predict_ttf(window)` loads the trained net; raises `ModelUnavailableError` if torch/weights absent — NEVER fabricates (removes the `np.random.randn` theatrical fallbacks at the old `:267,:301`). Verified by `test_world_model.py`.
- [x] **AC4 — Causal attribution v1 (G-020 partial), same `Diagnosis` interface.** `services/diagnosis.py` gains a counterfactual root-cause classification — machine-local vs externally-influenced — over the KNOWN SimWorld structural causal model (do-operator on the candidate external cause). Adds a `causal_attribution` field to `Diagnosis` (interface back-compatible: existing fields unchanged). Verified by `test_diagnosis.py` additions (clean-vs-confounded cases).
- [x] **AC5 — Honest scope boundary documented.** Model card + ADR state explicitly: known-structure SCM (not learned causal DISCOVERY) + a real trained TTF model; neuro-symbolic VERIFY (KB_25 step 3) and learned causal discovery remain PLANNED (G-020 stays open → Stage 17 / research spike). No overclaim.
- [x] **AC6 — Tests green + no regression.** New `test_world_model.py` + `test_diagnosis.py` additions pass; the Stage-6/7 suites still pass; `test_models.py` WorldModel tests updated to the honest contract. Zero new theatrical patterns.
- [x] **AC7 — Model card + KB + explainer.** `compliance/model-cards/world_model_ttf.md`; KB_02/05/23/25 updated; explainer HTML.
- [x] **AC8 — Independent audit: PASS** (2026-06-13, fresh task-auditor agent → `audits/STAGE_08_independent_review.md`). 36+25 tests re-run green; fresh-seed eval (70–73) reproduced +97.7% (not seed-specific); TTF win judged real not leaky (ground-truth label, crack_proximity excluded, disjoint seeds, fair baseline); causal deferral + de-mock + `--no-baseline-drop` judged honest; `sim_world.py` untouched; no gaps blocking close.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/training/stage_08_world_model/rollouts.py` | Generate (telemetry-window → true TTF) dataset from seeded SimWorld crack rollouts |
| `backend/training/stage_08_world_model/train.py` | Train the LSTM TTF forecaster → `models/world_model_ttf.{pt,metrics.json}` |
| `backend/training/stage_08_world_model/eval.py` | TTF MAE vs naive baseline on held-out seeds |
| `backend/training/stage_08_world_model/config.yaml` | Hyperparameters + seeds |
| `backend/tests/test_world_model.py` | World-model load/forecast/honest-unavailable + causal-attribution tests |
| `compliance/model-cards/world_model_ttf.md` | Annex IV model card |
| `compliance/decision-logs/2026-06-13_world_model_causal_diagnose.md` | ADR: TTF world model + causal-attribution v1 scope/boundary |
| `research/stage-explainers/STAGE_08/index.html` | Stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/ml/world_model.py` | Rewrite to honest TTF forecaster (`predict_ttf`); remove `np.random.randn` theatre; `ModelUnavailableError` |
| `backend/services/diagnosis.py` | Add counterfactual `causal_attribution` (known-SCM, back-compatible) |
| `backend/tests/test_models.py` | Update `TestWorldModel` to the honest contract (no untrained-fabrication) |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | — |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_02_Models_Inventory.md` (new `world_model_ttf`)
- `knowledge-base/KB_05_Simulation_Spec.md` (rollout/TTF labelling note)
- `knowledge-base/KB_23_Evals_and_Benchmarks.md` (Stage 8 TTF eval, measured)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (PREDICT=world-model BUILT; CAUSAL step partial)

## Verification commands

```bash
bash scripts/audit.sh   # additive ML stage; holds at 396 (no in-lane grep-counted theatre; np.random.randn removed is grep-invisible)
cd backend && python training/stage_08_world_model/train.py --config training/stage_08_world_model/config.yaml
cd backend && python training/stage_08_world_model/eval.py --seeds 60,61,62,63,64
cd backend && python -m pytest tests/test_world_model.py tests/test_diagnosis.py -q
bash scripts/independent-audit.sh 8
```

## Audit target

- Pre-stage baseline: **396**.
- Target: **hold at 396 with `--no-baseline-drop`** — additive ML stage (adds a trained TTF world model + causal-attribution v1). It de-mocks `world_model.py` by removing its `np.random.randn` fallbacks, but those are NOT in the `audit.sh` grep pattern set (grep-invisible theatre, same class as G-047), so the counted baseline holds flat honestly. No in-lane grep-counted theatre exists to remove (the remaining counted hits live in Stage-9/10/11 files — explainability, neural_networks, robotics/supply-chain heads, frontend). Justified in `KB_TASK_LOG.md`.

## Role

- Primary: `ml-engineer` (world-model training, weights, model card — owns `backend/ml/`, `backend/training/`, `models/`).
- Secondary: `backend-engineer` (diagnosis causal-attribution wiring), `task-auditor` (AC8), `agentic-governance-engineer` (ADR).

## Risks / unknowns

- **TTF learnability**: telemetry monotonically reflects crack proximity, so TTF should be recoverable — but if the learned model only ties the naive baseline, report it honestly (the de-mock + honest glue still stand; do not force a win).
- **Causal headroom is limited at current sim fidelity** (external incidents barely perturb the AI4I risk features). The causal-attribution v1 is therefore deliberately bounded; deeper causal value needs richer telemetry confounding (future) — stated honestly, not oversold.
- CPU training-time budget: TTF is supervised regression (fast, reliable) — target < 3 min.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-requisites (pre-filled from STAGE_07_rl_policy_intervention.md hand-off)


- What is now true that wasn't before this stage:
  - A real RL intervention substrate exists: `InterventionEnv` (event-driven, capacity-constrained), a
    from-scratch auditable PPO (bandit-verified), train/eval scripts, and a trained model
    `models/rl_intervention_policy.{pt,metrics.json}` (learns: return −160.8→−134.0).
  - A safety shield (shielded RL) guarantees maintenance on critical-proximity machines regardless of the net.
  - **Honest measured result (CRN-paired, 95% CI; G-046 RESOLVED):** rules near-optimal (0.375 crack-breakdowns);
    PPO+shield 0.875; PPO does NOT beat rules → **rules remain the default chooser** (`DEFAULT_CHOOSER="rules"`).
  - `select_chooser("rules"|"rl")` seam; `sim_world.py`/`slice_runner.py` unchanged (zero Stage-6 regression).
  - Audit held at 396 (`--no-baseline-drop`, additive ML stage).
- What the next stage starts with:
  - Stage 8 (world model + causal diagnose): replace the deterministic ranking in `services/diagnosis.py` behind
    the same `Diagnosis` interface; AND use the Stage-7 RL substrate for the richer recovery action space
    (self-repair / robot-fixer dispatch / backup-online / slow+catch-up) where RL can genuinely beat rules.
- Open items deferred to a future stage (name the stage if known):
  - Full multi-action RL win → Stage 8/11 (G-025 advanced, not fully resolved). Real-telemetry re-fit → Stage 22 (G-035).
  - Robot-navigation `rl_policy.py` + `decision_engine.py` de-mock → Stage 11 (ADR D6). G-044 legacy test debt → Stage 11.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*
