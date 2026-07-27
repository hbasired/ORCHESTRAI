# Audit report — Stage 15

**Date**: 2026-06-20T17:33:51Z
**Task doc**: tasks/STAGE_15_ot_it_bridge.md
**Baseline**: 364
**Audit total**: 364

## 1. Audit script

```
Audit report (2026-06-20T17:33:33Z)
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
  - backend/agents/runtime/nodes.py (mentions actuator-like operation; no safety.validator reference detected)
  - backend/agents/runtime/__pycache__/nodes.cpython-311.pyc (mentions actuator-like operation; no safety.validator reference detected)
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

- [x] Audit count flat at 364. WAIVED via `--no-baseline-drop` — Stage 15 adds real OT-integration code (asyncua OPC UA, real Sparkplug B protobuf + lifecycle, ISA-95 population) with NO `random.*`/mock/dict-literal theatre the grep counts; purely additive. Justified in `knowledge-base/KB_TASK_LOG.md` (Stage 15 entry). ADR `2026-06-20_stage15_ot_it_bridge.md`.
- [x] Actuator-touching code without safety.validator reference (Stage 17+). **FALSE POSITIVE / known pre-Stage-17 condition — verified no actuator path added.** The heuristic word-greps `actuator|send_command|execute_action` across `backend/` (incl. `venv/` third-party libs). In the NEW Stage-15 files the word "actuator" appears ONLY in safety-boundary disclaimers (`opcua/client.py`, `sparkplug/client.py`, `integrations/__init__.py` — "subscribe-only; the actuator/write path is the Stage-17 safety wrapper"; "NOT used to drive real actuators"): the OPC UA client is subscribe-only, and inbound Sparkplug NCMD/DCMD are parsed + dispatched to a callback (only `Node Control/Rebirth` is acted on — a protocol re-sync, not a physical command). The other hits are pre-existing `agents/*`/`ml/*`/`services/*` files + `venv/*` libs. **`backend/safety/` does not exist until Stage 17 by design (KB_17)** — the `safety.validate`-before-actuator CI gate activates at Stage 17+ (CLAUDE.md §6). No actuator command path was introduced this stage.

