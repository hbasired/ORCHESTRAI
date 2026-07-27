---
name: Models Inventory
description: Every ML model with class file, weights file, training script, dataset, status, last metrics, hyperparameters
type: catalog
last-updated: 2026-06-13-stage9
---

# KB_02 — Models Inventory

## Purpose
The canonical list of every ML model in the system. If a model is shipping in production, its row here is authoritative — including the path to its trained weights and the metrics card that backs the deploy decision.

## Source of truth
- `backend/ml/*.py` (model classes)
- Git-LFS-tracked `*.pt` / `*.pth` / `*.onnx` files (the weights)
- Sibling `*.metrics.json` + `*.card.md` per weights file (training git SHA, dataset hash, eval metrics)
- MLflow tracking server (Stage 14)

## Status legend
- **untrained** — class exists, no weights, currently using mock/heuristic fallback
- **trained-experimental** — weights exist, off-production (Colab artifact, no metrics card)
- **trained-staging** — weights + metrics card, gated behind feature flag
- **production** — weights + metrics card + drift monitor, serving real traffic

## Inventory (current — May 2026)

| Model | Class file | Weights file | Training script | Dataset | Status | Last metrics | Replaces fallback at |
|---|---|---|---|---|---|---|---|
| LSTM RUL (predictive maintenance) | `backend/ml/world_model.py` | `weights/cmapss_lstm.pt` (planned) | `backend/training/predictive_maintenance/cmapss_lstm.ipynb` (Stage 4) | NASA C-MAPSS | **untrained** | n/a | `world_model.py:216-247` |
| ANN failure classifier | `backend/ml/neural_networks.py` | `weights/ai4i_ann.pt` (planned) | `backend/training/predictive_maintenance/ai4i_ann.ipynb` (Stage 4) | AI4I 2020 | **untrained** | n/a | `neural_networks.py:114-124` |
| MsFormer (multi-scale Transformer PdM) | `backend/ml/world_model.py` (new) | `weights/msformer_pdm.pt` (planned) | `backend/training/predictive_maintenance/msformer.ipynb` (Stage 4 — added per refresh) | C-MAPSS + AI4I | **untrained** | n/a | n/a (new) |
| CNN defect classifier (ResNet-18 transfer) | `backend/ml/neural_networks.py` | `weights/neu_det_resnet18.pt` (planned) | `backend/training/defect/neu_det.ipynb` (Stage 5) | NEU-DET | **untrained** | n/a | `neural_networks.py:289-307` |
| Conv-AE anomaly detector | `backend/ml/neural_networks.py` | `weights/real_iad_cae.pt` (planned) | `backend/training/defect/real_iad_cae.ipynb` (Stage 5 — Real-IAD primary per refresh) | Real-IAD (primary) / MVTec AD (secondary) | **untrained** | n/a | n/a (new) |
| ANN demand predictor | `backend/ml/neural_networks.py` | `weights/m5_lstm.pt` (planned) | `backend/training/demand/m5_lstm.ipynb` (Stage 6) | M5 Walmart subset | **untrained** | n/a | `neural_networks.py` (demand) |
| Transformer demand (Informer / PatchTST) | `backend/ml/neural_networks.py` (new) | `weights/m5_patchtst.pt` (planned) | `backend/training/demand/m5_patchtst.ipynb` (Stage 6 — added per refresh) | M5 Walmart subset | **untrained** | n/a | n/a (new) |
| PPO factory policy | `backend/ml/rl_policy.py` | `weights/ppo_factory.zip` (planned) | `backend/training/rl/ppo_factory.ipynb` (Stage 7) | SimPy env (Stage 2) | **untrained** | n/a | `rl_policy.py:267-335` |
| LSTM world model | `backend/ml/world_model.py` | `weights/world_model_lstm.pt` (planned) | `backend/training/world_model/lstm.ipynb` (Stage 8) | SimPy histories (100K+ steps) | **untrained** | n/a | `world_model.py:216-247` |
| YOLOv8 (pretrained baseline) | `backend/ml/vision_model.py` | `backend/yolov8n.pt` (in repo) | n/a (pretrained) | n/a | **trained-staging** (pretrained, not fine-tuned) | `vision_model.py` random fallback |
| YOLOv8 warehouse fine-tune | `backend/ml/vision_model.py` | `weights/yolov8_warehouse.pt` (planned) | `backend/training/vision/yolov8_isaac.ipynb` (Stage 9 — Isaac Sim primary per refresh) | Isaac Sim synthetic + optional real video | **untrained** | n/a | `vision_model.py` |
| SHAP/IG/DiCE explainability | `backend/ml/explainability.py` | n/a (inference-time) | n/a (Stage 10) | n/a | **untrained** (`random.uniform(0.3,0.5)` mock) | `explainability.py:73-147` |
| Whisper STT (small) | `backend/voice/voice_interface.py` | downloaded at runtime | n/a (pretrained) | n/a | **production-conditional** (works if `openai-whisper` installed) | n/a |
| Piper TTS Hindi | `backend/voice/voice_interface.py` | `models/hi_IN-priyamvada-medium.onnx` | n/a (pretrained) | n/a | **trained-staging** | n/a |
| Piper TTS Telugu | `backend/voice/voice_interface.py` | `models/te_IN-padmavathi-medium.onnx` | n/a (pretrained) | n/a | **trained-staging** | n/a |

## Update protocol

Every time a new weight ships:
1. Drop `<name>.pt` (or equivalent) into `weights/` — Git LFS tracks it via `.gitattributes`.
2. Drop sibling `<name>.metrics.json` (eval metrics, dataset hash) and `<name>.card.md` (training git SHA, hyperparams, dataset URL, training command).
3. Update the row in this file's table — status, last metrics column, replaces-fallback column.
4. Bump `last-updated` in this file's frontmatter; commit in the same PR.
5. The stage's task doc must list this file in its "KB Updates Expected" block, or CI rejects.

## Promotion criteria (untrained → staging → production)

- **untrained → trained-experimental** — model class loads weights without error; smoke test passes.
- **trained-experimental → trained-staging** — `<name>.metrics.json` + `<name>.card.md` exist; metrics meet stage acceptance criterion in `tasks/STAGE_NN_*.md`.
- **trained-staging → production** — drift monitor enabled (Stage 14); 24-hour shadow deploy without incident; rollback path documented.

## Latency constraint

Every model's per-call inference must fit within the per-hop budget in `KB_10_Production_Hardening.md`. If a new model busts the budget, the PR must either (a) cache enough of the output to drop perceived latency below budget, (b) push it to async / off-critical-path, or (c) document the SLA impact in the stage's task doc.

### Stage 4 — `pdm_failure_predictor` (BUILT 2026-06-01, first real trained weight)

| Field | Value |
|---|---|
| Class | `backend/ml/failure_predictor.py::FailurePredictor` (tabular MLP 8→64→32→1, ReLU, dropout 0.3) |
| Weights | `models/pdm_failure_predictor.pt` (+ `.scaler.pkl`, `.meta.json`, `.metrics.json`) |
| Training | `notebooks/stage04_ai4i_tabular_colab.ipynb` (Colab free GPU; seed 42) |
| Dataset | AI4I 2020 (UCI, CC BY 4.0) — KB_03 |
| Status | BUILT (first cut). Honest: raises `ModelUnavailableError` if torch/brain absent — never fabricates. |
| Metrics | **XGBoost chosen (2026-06-01): ROC-AUC 0.971 / PR-AUC 0.847**, recall-tuned threshold 0.779 (G-034 + G-033 resolved). MLP superseded (PR-AUC 0.679). `failure_predictor.py` auto-selects arch from meta. |
| Card | `compliance/model-cards/pdm_failure_predictor.md` |
| Upgrades (ledgered) | recall-tune G-033 · XGBoost G-034 · re-fit on real telemetry G-035 |

### Stage 5 — `demand_forecaster` (BUILT 2026-06-01, second real trained weight)

| Field | Value |
|---|---|
| Class | `backend/ml/demand_forecaster.py::DemandForecaster` (LSTM, window 24, hidden 128, 1 layer, 15 features) |
| Weights | `models/demand_forecaster.*` (pt + scaler.pkl + meta.json + metrics.json) |
| Training | `notebooks/stage05_demand_forecasting_v2_colab.ipynb` (cyclical features + log1p target + grid search) |
| Dataset | UCI Bike Sharing #275 (CC BY 4.0) — KB_03 |
| Metrics | MAE 32.9 / RMSE 52.4 / MAPE 21.0% / **+59% vs persistence** (KB_23). Card: `compliance/model-cards/demand_forecaster.md` |
| Honest | raises `ModelUnavailableError` if absent; proxy (bike demand) → re-fit on real orders (G-035); live wiring G-036 |

### Stage 7 — `rl_intervention_policy` (BUILT 2026-06-12, third real trained weight; NOT the default chooser)

| Field | Value |
|---|---|
| Class | `backend/ml/intervention_rl.py::RLInterventionPolicy` (PPO, shared-trunk actor-critic MLP 2×64; `training/stage_07_rl_intervention/ppo.py`) |
| Weights | `models/rl_intervention_policy.{pt,metrics.json}` (loaded `weights_only=True` — no pickle exec surface) |
| Training | `backend/training/stage_07_rl_intervention/train.py` (from-scratch PPO, torch CPU; seed 7; 24k steps; ~254 s) |
| Dataset | None — synthetic SimPy env (`InterventionEnv`, capacity-1 crew, multi-crack). Risk signal: ground-truth proximity (train) / predictor p_fail (inference) |
| Metrics | learns (return −160.8→−134.0); eval crack-breakdowns: none 4.0 / **rules 0.375** / ppo+shield 0.875 (CRN-paired, 95% CI; G-046). Card: `compliance/model-cards/rl_intervention_policy.md` |
| Honest | raises `ModelUnavailableError` if absent; **PPO does NOT beat the rules at v0 → rules stay default** (`intervention_policy.DEFAULT_CHOOSER="rules"`); ships as safety-shielded learnable substrate for Stage 8. Sim-only (G-035; Stage-17 wrapper before any real actuation) |

> Note: the old "PPO factory policy" row (`backend/ml/rl_policy.py`, **untrained**) is a SEPARATE robot-navigation
> stub used by `decision_engine.py` — distinct from this Stage-7 intervention policy. It remains untrained and is
> owned by Stage 11's runtime de-mock (ADR `2026-06-12_rl_intervention_ppo.md` D6).

### Stage 8 — `world_model_ttf` (BUILT 2026-06-13, fourth real trained weight)

| Field | Value |
|---|---|
| Class | `backend/ml/world_model.py::WorldModel.predict_ttf` (1-layer LSTM h48 → MLP head → scalar TTF minutes) |
| Weights | `models/world_model_ttf.{pt,metrics.json}` (loaded `weights_only=True`) |
| Training | `backend/training/stage_08_world_model/train.py` (SimWorld crack rollouts; seed 8; ~36 s CPU) |
| Dataset | None — synthetic SimWorld (KB_05); 3251 train / 852 val windows; ground-truth TTF from the crack schedule |
| Metrics | **TTF MAE 0.067 min vs naive 2.979 (+97.8%)**; fresh-seed 0.070 vs 3.230 (+97.8%). Card: `compliance/model-cards/world_model_ttf.md` |
| Honest | raises `ModelUnavailableError` if absent (replaced the old `np.random.randn` stub); proxy/sim only (G-035); sim-only (Stage-17 wrapper before real use) |

> The old "LSTM world model" / "LSTM RUL" rows above (status **untrained**) are superseded by `world_model_ttf`
> for the machine-crack TTF use case. `world_model.py` is now honest (no fabrication). The companion causal
> attribution v1 lives in `services/diagnosis.py` (G-020 partial — known-SCM counterfactual, not learned discovery).

### Stage 8 depth-hardening — `rul_transformer_cmapss` (BUILT 2026-06-14, sixth real trained weight)

| Field | Value |
|---|---|
| Class | `backend/ml/rul_transformer.py::RULTransformer.predict_rul` (Transformer encoder: Linear(14→64) → sinusoidal PE → 2×encoder layer (4 heads, FFN 128, GELU) → temporal mean-pool → MLP head → scalar RUL) |
| Weights | `models/rul_transformer_cmapss.{pt,metrics.json}` (loaded `weights_only=True`) |
| Training | `backend/training/stage_08_world_model/train_cmapss.py` (real C-MAPSS FD001; 17,731 train windows; MSE/Adam/cosine; seed 8; ~265 s CPU) |
| Dataset | **NASA C-MAPSS FD001** (real benchmark; KB_03) — cached `data/datasets/cmapss/` (git-ignored), 2 public mirrors recorded |
| Metrics | **FD001 test RMSE 13.80 / NASA score 372** (beats CNN 18.45 & LSTM 16.14 lit. baselines, competitive with DCNN/Transformer SOTA; +66% vs naive). Re-eval: `eval_cmapss.py`. Card: `compliance/model-cards/rul_transformer_cmapss.md` |
| Honest | raises `ModelUnavailableError` if absent; benchmark validates architecture, not the plant (real-fleet re-fit = G-035); single test eval after best-val selection (no peeking) |
| Companions | `backend/ml/causal_discovery.py` (learned PC discovery, skeleton F1 0.75, prox-hub — validates the SCM) · `backend/services/plan_verifier.py` (neuro-symbolic VERIFY step). ADR `2026-06-14_depth_08_world_model_causal_verify.md` |

### Stage 9 — `defect_classifier` + real YOLOv8n (BUILT 2026-06-13, fifth real trained weight)

| Field | Value |
|---|---|
| Class | `backend/ml/defect_classifier.py::DefectClassifier.classify` (**v2: ResNet18 transfer learning**, RGB 128×128 → 6 classes; arch auto-detected from ckpt, tiny-CNN back-compat) |
| Weights | `models/defect_classifier.{pt,metrics.json}` (`weights_only=True`) |
| Training | **v2** `backend/training/stage_09_defect/train_transfer.py` (pretrained ResNet18, layer4+fc fine-tune, seed 9; ~4.3 min CPU). v1 baseline `train.py` retained |
| Dataset | **real NEU-CLS** (`newguyme/neu_cls`, KB_03) — 6 steel-surface defect classes; same seed-9 split (no leakage) |
| Metrics | **v2 (2026-06-14): test acc 99.3% / macro-F1 0.993** (best val 1.000) vs v1 tiny-CNN 88.2% (+11.1 pt) — SOTA-competitive. Per-class + confusion in metrics.json. Card: `compliance/model-cards/defect_classifier.md` |
| Honest | raises `ModelUnavailableError` if absent; benchmark scope — PROXY domain (steel ≠ warehouse) → re-fit before pilot (G-035); positional labels. ADR `2026-06-14_depth_09_defect_transfer_learning.md` |

> **`vision_model.py` de-mocked (Stage 9):** the `YOLOv8 (pretrained baseline)` row above now runs **real**
> YOLOv8n inference (`backend/yolov8n.pt`) and raises `ModelUnavailableError` — the random-detection fallback
> (`_generate_mock_detections`) + the fabricating `video_processor._mock_process_loop` are REMOVED.
> Audit 396 → 383 (genuine strict decrease).

### Stage 7 depth-hardening — `rul_intervention_maskable_ppo` (BUILT 2026-06-14, RL beats rules)

| Field | Value |
|---|---|
| Class | `backend/ml/group_scheduler_rl.py::GroupSchedulerRL.act` (loads SB3 sb3-contrib **MaskablePPO**; action masking) |
| Weights | `models/rl_intervention_maskable_ppo.{zip,metrics.json}` |
| Training | `backend/training/stage_07_rl_intervention/train_sb3.py` on `GroupMaintenanceEnv` (group batching + opportunistic demand + crew contention); 250k steps, ~11 min CPU, seed 7 |
| Env | Gymnasium maintenance-scheduling MDP (documented model, not SimWorld telemetry); rule baselines greedy/threshold-batch |
| Metrics | **CRN-paired held-out: MaskablePPO −125.1 vs best rule −137.4, +12.36 (95% CI [6.0,18.71]), 36/50 wins** — first RL to genuinely beat the best rule. Re-eval `eval_sb3.py`. Card: `compliance/model-cards/rl_intervention_maskable_ppo.md` |
| Honest | raises `ModelUnavailableError` if SB3/policy absent; scheduling-MDP scope (live-loop wiring + real plant = G-025/G-035); not actuator-wired. v0 from-scratch PPO + its honest "rules tie" negative RETAINED. ADR `2026-06-14_depth_07_maskable_ppo_group.md` |

## Last verified
- 2026-06-13 (Stage 9 close) — `defect_classifier` (NEU-CLS CNN) added — fifth real trained weight; `vision_model.py` de-mocked to real YOLOv8n (audit 396→383).
- 2026-06-13 (Stage 8 close) — `world_model_ttf` (LSTM TTF forecaster) added — fourth real trained weight; `world_model.py` de-mocked; causal attribution v1 in `diagnosis.py`.
- 2026-06-12 (Stage 7 close) — `rl_intervention_policy` (PPO) added — third real trained weight; rules remain default (honest negative-vs-rules result).
- 2026-06-01 (Stage 5 close) — `demand_forecaster` (LSTM) added — second real trained weight.
- 2026-06-01 (Stage 4 close) — `pdm_failure_predictor` added — the project's first real trained weight (AI4I 2020, no leakage).
- 2026-05-11 — Plan-mode session. All "untrained" rows verified via `grep -n` against the cited line ranges.
- **2026-05-11 (Stage 1 close)** — No models were trained in this stage; every "untrained" row above remains accurate. The `_get_demo_metrics` shim in `backend/api/metrics_routes.py` that was returning fabricated MAE/R²/accuracy values has been deleted; `/api/metrics/models` and `/api/metrics/embodied` now return HTTP 503 until real metrics arrive in Stage 4. The Git LFS attribute file `.gitattributes` is now in place so the next stage that lands a weight file does so via LFS without further setup.
