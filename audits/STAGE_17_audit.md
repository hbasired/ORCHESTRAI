# Audit report — Stage 17

**Date**: 2026-06-21T07:43:57Z
**Task doc**: tasks/STAGE_17_functional_safety_wrapper.md
**Baseline**: 364
**Audit total**: 364

## 1. Audit script

```
Audit report (2026-06-21T07:43:48Z)
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
knowledge-base/KB_12_Standards_Map.md
knowledge-base/KB_13_PQC_Crypto_Strategy.md
knowledge-base/KB_14_Agent_Memory_Architecture.md
knowledge-base/KB_15_Observability_Evidence_Pipeline.md
knowledge-base/KB_16_A2A_MCP_Protocols.md
knowledge-base/KB_17_Functional_Safety_Wrapper.md
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
compliance/decision-logs/2026-06-15_stage13_5_pqc_foundations.md
compliance/decision-logs/2026-06-15_stage13_cdc_ingestion.md
compliance/decision-logs/2026-06-15_stage14_a2a_protocol.md
compliance/decision-logs/2026-06-20_stage15_ot_it_bridge.md
compliance/decision-logs/2026-06-20_stage16_vda5050_robot_fleet.md
compliance/decision-logs/2026-06-21_stage17_functional_safety_wrapper.md

## 4. Vulnerabilities

### Gitleaks
```
(gitleaks not run — install gitleaks for secret scanning)
```

### Classical-crypto in backend/crypto/ (after Stage 13.5+)
  (none)

### Actuator paths without safety.validator reference (Stage 17+)

  - backend/agents/base_agent.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/embodied_agent.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/manufacturing_agent.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/robotics_agent.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/supply_chain_agent.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/__pycache__/base_agent.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/__pycache__/embodied_agent.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/__pycache__/manufacturing_agent.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/__pycache__/robotics_agent.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/__pycache__/supply_chain_agent.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/integrations/opcua/client.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/integrations/opcua/__pycache__/client.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/integrations/sparkplug/client.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/integrations/sparkplug/__pycache__/client.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/integrations/__init__.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/integrations/__pycache__/__init__.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/ml/defect_classifier.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/ml/group_scheduler_rl.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/ml/world_model.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/ml/__pycache__/defect_classifier.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/ml/__pycache__/group_scheduler_rl.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/ml/__pycache__/world_model.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/safety/contract.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/safety/__init__.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/services/intervention_policy.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/services/plan_verifier.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/services/__pycache__/intervention_policy.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/services/__pycache__/plan_verifier.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/aioredis/client.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/aioredis/connection.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/aioredis/sentinel.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/aioredis/__pycache__/client.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/aioredis/__pycache__/connection.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/aioredis/__pycache__/sentinel.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/paho/mqtt/client.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/paho/mqtt/__pycache__/client.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/asyncio/client.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/asyncio/cluster.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/asyncio/connection.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/asyncio/__pycache__/client.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/asyncio/__pycache__/cluster.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/asyncio/__pycache__/connection.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/client.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/cluster.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/connection.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/event.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/__pycache__/client.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/__pycache__/cluster.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/__pycache__/connection.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
  - backend/venv/Lib/site-packages/redis/__pycache__/event.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)

## 5. Audit chain integrity

OK (quick verify passed)

## 6. Gaps (action items)

(Rectify each before `scripts/close-task.sh`. The closure script refuses if this section is non-empty.)

- [x] Audit count flat at 364. WAIVED via `--no-baseline-drop` — Stage 17 adds real safety-wrapper + zero-trust code (contract DSL, validator, sil_bridge, STO/SS1, self-healing, per-agent ML-DSA-65 identity, MCP authz, signed manifest) with NO `random.*`/mock/dict-literal theatre the grep counts; purely additive. Justified in `knowledge-base/KB_TASK_LOG.md` (Stage 17 entry). ADR `2026-06-21_stage17_functional_safety_wrapper.md`.
- [x] Actuator-touching code without safety.validator reference (Stage 17+). **RESOLVED for the real dispatch paths + the rest are FALSE POSITIVES.** The actual `actuator.*` emitters now reference `safety.validator` and dropped off the list: `sil_bridge.py` (refuses any non-allowing Decision), `integrations/vda5050/master.py` (validate_order before dispatch), `agents/runtime/nodes.py::execute` (routes through `validate()`), plus `validator.py`/`sto_ss1.py`. The **real enforcement is the trace-pairing CI gate** (`scripts/check-safety-trace-pairing.py`, gate `safety-contract-tests`): every `actuator.*` span MUST be preceded by `safety.validate.*` — tested (incl. a negative control). The remaining flagged files dispatch NO actuator: `safety/contract.py`+`safety/__init__.py` (the DSL/docstrings describing the gate), `agents/*` + `ml/*` + `services/{intervention_policy,plan_verifier}` (legacy/planning files that mention the word), `integrations/opcua/client.py`+`sparkplug/client.py`+`integrations/__init__.py` (Stage-15 subscribe-only disclaimers), and `.pyc`/`venv` noise. No unguarded actuator dispatch path exists.

