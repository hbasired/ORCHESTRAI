# Audit report — Stage 07

**Date**: 2026-06-13T08:56:43Z
**Task doc**: tasks/STAGE_07_rl_policy_intervention.md
**Baseline**: 396
**Audit total**: 396

## 1. Audit script

```
Audit report (2026-06-13T08:56:39Z)
=============================================
  mock_predictions                  0
  hardcoded_responses_ts            0
  generate_mock_state               3
  hardcoded_models_ts               0
  random_uniform_py               141
  heuristic_actions                 3
  random_choices_py                 4
  random_choice_py                152
  generate_robots                   3
  get_demo_metrics                  0
  math_random_ts                   84
  mock_detections                   6
---------------------------------------------
  TOTAL                           396
---------------------------------------------
Baseline (from .audit-baseline): 396
NO PROGRESS: count is equal to baseline (396).
Did this stage actually replace any fakery? If not, the stage isn't done.
```

Gate: total (396) must be **<=** baseline (396). Strictly **<** unless stage is flagged `--no-baseline-drop`.

## 2. KB diff coverage

Working-tree modified KB files:
knowledge-base/KB_01_System_Architecture.md
knowledge-base/KB_02_Models_Inventory.md
knowledge-base/KB_04_Data_Schema.md
knowledge-base/KB_05_Simulation_Spec.md
knowledge-base/KB_11_Pitch_Strategy.md
knowledge-base/KB_23_Evals_and_Benchmarks.md
knowledge-base/KB_25_Causal_SelfHealing_Engine.md
knowledge-base/KB_26_Product_Market_Strategy.md
knowledge-base/KB_README.md
knowledge-base/KB_TASK_LOG.md

Cross-check this against the task doc's "KB files this stage updates" block. Every listed KB file must have a non-trivial diff.

## 3. Missing artefacts

### Model cards / metrics
  (none)

### New ADRs (untracked decision logs)
compliance/decision-logs/2026-06-11_strategic_product_reset.md
compliance/decision-logs/2026-06-12_rl_intervention_ppo.md

## 4. Vulnerabilities

### Gitleaks
```
(gitleaks not run — install gitleaks for secret scanning)
```

### Classical-crypto in backend/crypto/ (after Stage 13.5+)
  (none)

### Actuator paths without safety.validator reference (Stage 17+)
  (none)

## 5. Audit chain integrity

OK (quick verify passed)

## 6. Gaps (action items)

(Rectify each before `scripts/close-task.sh`. The closure script refuses if this section is non-empty.)

- [x] Audit count flat at 396. **Justified** in KB_TASK_LOG (2026-06-12 Stage 7 entry) + ADR `2026-06-12_rl_intervention_ppo.md` D6: additive RL stage; zero new theatrical patterns; intervention path already clean; the remaining RL-flavoured theatre (`ml/rl_policy.py` navigation stub + `decision_engine.py`) is Stage 11's subsystem (de-mocking here would entangle subsystems or game the metric). Closing with `--no-baseline-drop`.

