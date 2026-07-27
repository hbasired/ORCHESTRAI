# Audit report — Stage 12_5

**Date**: 2026-06-15T15:33:55Z
**Task doc**: tasks/STAGE_12_5_observability.md
**Baseline**: 364
**Audit total**: 364

## 1. Audit script

```
Audit report (2026-06-15T15:33:52Z)
=============================================
  mock_predictions                  0
  hardcoded_responses_ts            0
  generate_mock_state               3
  hardcoded_models_ts               0
  random_uniform_py               115
  heuristic_actions                 3
  random_choices_py                 4
  random_choice_py                152
  generate_robots                   3
  get_demo_metrics                  0
  math_random_ts                   84
  mock_detections                   0
---------------------------------------------
  TOTAL                           364
---------------------------------------------
Baseline (from .audit-baseline): 364
NO PROGRESS: count is equal to baseline (364).
Did this stage actually replace any fakery? If not, the stage isn't done.
```

Gate: total (364) must be **<=** baseline (364). Strictly **<** unless stage is flagged `--no-baseline-drop`.

## 2. KB diff coverage

Working-tree modified KB files:
knowledge-base/KB_01_System_Architecture.md
knowledge-base/KB_02_Models_Inventory.md
knowledge-base/KB_03_Datasets_Catalog.md
knowledge-base/KB_04_Data_Schema.md
knowledge-base/KB_05_Simulation_Spec.md
knowledge-base/KB_06_Agent_Coordination_Protocol.md
knowledge-base/KB_07_API_Contracts.md
knowledge-base/KB_11_Pitch_Strategy.md
knowledge-base/KB_14_Agent_Memory_Architecture.md
knowledge-base/KB_15_Observability_Evidence_Pipeline.md
knowledge-base/KB_16_A2A_MCP_Protocols.md
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
compliance/decision-logs/2026-06-13_explainability_shap_counterfactual.md
compliance/decision-logs/2026-06-13_vision_defect_detection.md
compliance/decision-logs/2026-06-13_world_model_causal_diagnose.md
compliance/decision-logs/2026-06-14_depth_06_slice_integration.md
compliance/decision-logs/2026-06-14_depth_07_maskable_ppo_group.md
compliance/decision-logs/2026-06-14_depth_08_world_model_causal_verify.md
compliance/decision-logs/2026-06-14_depth_09_defect_transfer_learning.md
compliance/decision-logs/2026-06-14_depth_10_dice_global_shap.md
compliance/decision-logs/2026-06-14_stage11_langgraph_runtime_core.md
compliance/decision-logs/2026-06-14_stage11_runtime_complete.md
compliance/decision-logs/2026-06-15_security_zerotrust_survivability_review.md
compliance/decision-logs/2026-06-15_stage11_5_mcp_servers.md
compliance/decision-logs/2026-06-15_stage11_full_infra_verification.md
compliance/decision-logs/2026-06-15_stage12_5_observability.md
compliance/decision-logs/2026-06-15_stage12_agent_memory.md

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

- [x] Audit count flat at 364. WAIVED via `--no-baseline-drop` — justified in `knowledge-base/KB_TASK_LOG.md` (Stage 12.5 entry): the observability layer (`backend/observability/`, span instrumentation, compose overlay) WRAPS real OTel spans around real code — it adds no `random.*`/mock theatre the grep counts, and removes none. New code is additive. ADR `2026-06-15_stage12_5_observability.md`.

