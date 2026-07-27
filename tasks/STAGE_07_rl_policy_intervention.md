---
status: done
stage: 07
slug: rl_policy_intervention
created: 2026-06-12
---

# Stage 07 — RL Intervention: PPO recovery policy over the Stage-6 decision contract

> Replace the deterministic v0 intervention chooser (`backend/services/intervention_policy.py`) with a PPO
> policy over the SAME `InterventionDecision` contract — deepening the INTERVENE step of the self-healing loop
> (KB_25 step 4, gap G-025) without changing any interface. The Stage-6 A/B harness
> (`backend/scripts/run_slice_ab.py`) is the ready-made training/eval environment; the measured Stage-6 baseline
> (−42.8% unplanned downtime with rules) is the number PPO must beat to earn its place — if it cannot, the rules
> stay (honesty rule: the better policy wins, not the fancier one). Safety: still sim-only; PPO never commands a
> real actuator (Stage 17 wrapper precedes any non-sim actuation). Cross-links: PRD v3 §12/§18 · KB_25 §2 ·
> Stage 6 hand-off below · ml-engineer SKILL (RL safety-reward documentation duty).

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–10 + §5)

- [x] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [x] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs). Surfaced for Stage 7: **G-025** (PPO intervene — THIS stage's core), **G-046** (A/B CRN pairing/CIs — folded into AC5), **G-027** (free-cost — ongoing, honoured: from-scratch PPO in torch, zero paid deps).
- [x] **Free-cost only:** from-scratch PPO in the already-pinned `torch` (CPU); no new heavy deps (no SB3/gymnasium); no LLM in this stage's loop; OSS/local only. No committed keys.
- [x] **Stage explainer HTML:** before close, write `research/stage-explainers/STAGE_07/index.html` (self-contained, honest BUILT/PARTIAL/PLANNED, real file paths + measured numbers).

## Pre-requisites

- Stage(s) closed: 2 (SimPy DES), 3 (WS broker), 4 (failure predictor), 5 (demand), 6 (Vertical Slice v0 — the rules intervention policy + A/B harness this stage extends).
- Decision logs honoured: `2026-05-31_causal_self_healing_engine.md` (KB_25 step 4 = intervene), `2026-06-11_strategic_product_reset.md` (slice-first sequencing). New ADR this stage: `2026-06-12_rl_intervention_ppo.md`.
- KB files at minimum version: KB_25 (2026-06-12, intervene=v0-BUILT), KB_05 (2026-06-12, telemetry+maintenance API), KB_23 (Stage 6 A/B measured).
- Gaps ledger rows pulled in: **G-025** (resolved-or-advanced here), **G-046** (resolved here: paired-seed CRN + CIs in the eval).

## Acceptance criteria

- [x] **AC1 — RL training environment.** `backend/training/stage_07_rl_intervention/env.py::InterventionEnv` — a headless, seeded, deterministic-per-seed SimWorld wrapper for the machine-crack scenario with a **maintenance-crew capacity constraint** (NEW, optional, backward-compatible: default unlimited preserves Stage-6 behavior). Discrete action space (no-op / dispatch crew to at-risk machine k); observation = fixed-size per-at-risk-machine features (p_fail, crack_proximity, tool_wear, queue_load) + crew/load context; dense, safety-shaped reward. Verified by `backend/tests/test_intervention_rl.py` (reset/step determinism, obs/action shapes, reward sign).
- [x] **AC2 — Real PPO, trained, free + local.** `backend/training/stage_07_rl_intervention/ppo.py` (compact from-scratch PPO: discrete actions, GAE-λ, clipped surrogate, value + entropy) + `train.py` + `config.yaml`. Training produces `models/rl_intervention_policy.pt` + `models/rl_intervention_policy.metrics.json` (seed, hyperparams, training-return curve, eval-vs-baselines). Mean episode return must **measurably improve over training** (recorded in metrics) — verified by `test_intervention_rl.py` (PPO reduces loss / improves return on a short seeded run) + the committed metrics file.
- [x] **AC3 — Inference glue + honest unavailability.** `backend/ml/intervention_rl.py::RLInterventionPolicy` loads the `.pt`, exposes `act(obs)`; raises `ModelUnavailableError` if torch/weights absent (NEVER fabricates an action — mirrors `failure_predictor`). Verified by `test_intervention_rl.py`.
- [x] **AC4 — Safety shield (ml-engineer mandate: "no policy that allows known-unsafe actions even at low probability").** At inference the learned policy is wrapped by a hard shield: if any at-risk machine's `crack_proximity ≥ critical` and the crew is free, maintenance is FORCED regardless of the sampled action. The shipped policy is provably safe even though the net is stochastic. Documented in the model card; verified by `test_intervention_rl.py` (a high-proximity state always yields a maintain action).
- [x] **AC5 — Honest 3-way eval with CRN pairing + CIs (resolves G-046).** `eval.py` runs none / rules / PPO+shield on the SAME paired seeds under the capacity-constrained multi-crack scenario; reports crack-breakdowns-prevented (robust metric) + downtime with **confidence intervals**; writes `backend/training/evals/stage07/results.{json,md}`. **The shipped default chooser flips to PPO ONLY if it is ≥ rules on crack-prevention with no regression; otherwise rules stay default and PPO ships as the proven-safe learnable substrate — the result is reported honestly either way.** Verified by `test_slice_ab`-style smoke + the committed report.
- [x] **AC6 — Pluggable chooser, contract unchanged.** `backend/services/intervention_policy.py` gains a `policy="rules"|"rl"` selector producing the SAME `InterventionDecision`; `slice_runner` can run either. Default per AC5. Verified by `test_intervention_rl.py` (RL path returns a valid `InterventionDecision`).
- [x] **AC7 — Model card + KB.** `compliance/model-cards/rl_intervention_policy.md` (Annex IV minimum: intended use, training env, reward + safety-shield design, limitations, seed, eval result, contact). KB_02/KB_05/KB_23/KB_25 updated.
- [x] **AC8 — Tests green + no regression.** New `test_intervention_rl.py` passes; the Stage-6 slice suite still passes (capacity constraint is backward-compatible). Audit introduces ZERO new theatrical patterns.
- [x] **AC9 — Independent audit PASS** (2026-06-12, fresh task-auditor agent → `audits/STAGE_07_independent_review.md`). Verdict **PASS**: 14 RL + 21 slice tests re-run green; fresh-seed eval (50–53) reproduced the honest negative result (PPO does not beat rules — not cherry-picked); PPO/shield/unavailability verified real; `sim_world.py` untouched; `--no-baseline-drop` + reward-shaping judged honest.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/training/stage_07_rl_intervention/env.py` | `InterventionEnv` — headless SimWorld RL wrapper (capacity-constrained multi-crack) |
| `backend/training/stage_07_rl_intervention/ppo.py` | Compact from-scratch PPO (discrete, GAE, clipped) — auditable, no heavy deps |
| `backend/training/stage_07_rl_intervention/train.py` | Train → `models/rl_intervention_policy.{pt,metrics.json}` |
| `backend/training/stage_07_rl_intervention/eval.py` | 3-way paired-seed eval (none/rules/PPO) + CIs → `training/evals/stage07/` |
| `backend/training/stage_07_rl_intervention/config.yaml` | Hyperparameters + seeds (reproducibility) |
| `backend/ml/intervention_rl.py` | `RLInterventionPolicy` inference glue + safety shield; honest `ModelUnavailableError` |
| `backend/tests/test_intervention_rl.py` | Env/PPO/shield/glue/contract tests |
| `compliance/model-cards/rl_intervention_policy.md` | Annex IV model card (incl. safety-shield doc) |
| `compliance/decision-logs/2026-06-12_rl_intervention_ppo.md` | ADR: PPO design, reward+shield, honest "better-policy-wins" gate |
| `research/stage-explainers/STAGE_07/index.html` | Stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/simulation/sim_world.py` | OPTIONAL maintenance-crew capacity (default unlimited = Stage-6 behavior preserved) |
| `backend/services/intervention_policy.py` | Pluggable `policy="rules"|"rl"` selector (same `InterventionDecision` contract) |
| `backend/services/slice_runner.py` | Allow the slice loop to use the RL chooser (rules default) |

> **As-built note (2026-06-12):** `sim_world.py` was NOT modified — the crew-capacity constraint lives in the RL env (`InterventionEnv`), preserving Stage-6 behaviour exactly (zero regression). `slice_runner.py` was NOT modified — the RL chooser is fleet-level and not the default, so wiring it into the per-machine slice would be show-wiring; the seam is `intervention_policy.select_chooser`. AC6 satisfied at fleet granularity (documented in ADR `2026-06-12_rl_intervention_ppo.md` D5).

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | The `ml/rl_policy.py` navigation stub + `decision_engine.py` heuristics are a SEPARATE subsystem owned by Stage 11; de-mocking them here would entangle unrelated code or game the audit metric (remove grep-counted lines while leaving grep-invisible untrained-model fabrication). Deferred honestly. |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_02_Models_Inventory.md` (new `rl_intervention_policy`)
- `knowledge-base/KB_05_Simulation_Spec.md` (maintenance-crew capacity)
- `knowledge-base/KB_23_Evals_and_Benchmarks.md` (Stage 7 eval, measured)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (intervene step: PPO BUILT)

## Verification commands

```bash
# Audit — additive ML stage; holds at 396 (no new fakery, intervention path already clean)
bash scripts/audit.sh

# Stage-specific: train (fast CPU), eval, tests
cd backend && python training/stage_07_rl_intervention/train.py --config training/stage_07_rl_intervention/config.yaml
cd backend && python training/stage_07_rl_intervention/eval.py --seeds 42,43,44,45,46
cd backend && python -m pytest tests/test_intervention_rl.py tests/test_slice_intervene.py tests/test_slice_ab.py -q

# Independent audit
bash scripts/independent-audit.sh 7
```

## Audit target

- Pre-stage baseline: **396** (`.audit-baseline`).
- Target: **hold at 396 with `--no-baseline-drop`** — Stage 7 is an additive RL stage: it adds a trained model + RL substrate and introduces ZERO new theatrical patterns; the intervention path (Stage 6) is already mock-free. The remaining RL-flavored theatre (`ml/rl_policy.py` untrained-actor + `random.*` heuristic, consumed only by the off-slice, still-theatrical `decision_engine.py` + its `test_models.py` tests) is a robot-navigation/decision-engine concern explicitly owned by **Stage 11**. De-mocking it here would entangle two subsystems or game the audit metric. Justification recorded in `KB_TASK_LOG.md`.

## Role

- Primary: `ml-engineer` (RL training, model card, weights — owns `backend/ml/`, `backend/training/`, `models/`).
- Secondary (hand-offs): `backend-engineer` (intervention_policy/slice_runner wiring), `robotics-integration-engineer` (safety-shield review — the actuator-safety dual), `task-auditor` (AC9), `agentic-governance-engineer` (ADR).

## Risks / unknowns

- **PPO may only MATCH (not beat) the near-optimal rules** on this scenario — the rules already prevent ~all breakdowns. This is an ACCEPTED honest outcome: the safety shield guarantees PPO is at least as safe; the stage's lasting value is the reusable RL substrate + a real trained policy + an honest paired-seed eval. The default chooser flips to PPO only on a measured win (AC5). The "better policy wins" rule is the law here, not "the fancier policy ships."
- CPU-only training-time budget: keep nets small + timesteps modest (target < 5 min). If a run underperforms, the honest fallback (rules stay default) still closes the stage.
- Crew-capacity constraint must be backward-compatible (default unlimited) so Stage-6 tests + A/B do not regress.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

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

## Pre-requisites (pre-filled from STAGE_06_vertical_slice_predict_diagnose.md hand-off)


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
