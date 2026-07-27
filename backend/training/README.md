# backend/training/ — ML training workflow (Stages 4–10 + Stage 20)

> **Purpose:** train the real ML models that replace the theatrical fallbacks in `backend/ml/`. Training happens OFFLINE (Colab / local GPU), then artefacts land in `models/` for the runtime to consume.

## The seven training stages

| Stage | Model | Replaces theatrical at | Dataset | Notebook dir |
|---|---|---|---|---|
| 4 | Predictive maintenance (Transformer / MsFormer) | `backend/ml/world_model.py:216-247` (partial) | C-MAPSS NASA Turbofan | `backend/training/stage_04_predictive_maintenance/` |
| 5 | Defect detection (Conv-AE backstop + classifier) | `backend/ml/neural_networks.py:289-307` | Real-IAD (primary), NEU-DET (secondary), KSDD2 | `backend/training/stage_05_defect_detection/` |
| 6 | Demand forecasting (TFT / Informer) | `backend/ml/neural_networks.py:114-124,175-176` | M5 Walmart competition | `backend/training/stage_06_demand_forecasting/` |
| 7 | RL Policy (PPO with safety reward shaping) | `backend/ml/rl_policy.py:267-335` | Isaac Sim synthetic (heavy GPU) OR gymnasium-warehouse (lightweight) | `backend/training/stage_07_rl_policy/` |
| 8 | World model (Dreamer-V3 lite / LeWorldModel) | `backend/ml/world_model.py` (full) | Generated from SimPy traces (Stage 2 outputs) | `backend/training/stage_08_world_model/` |
| 9 | Vision (YOLOv10 fine-tune + obstacle CNN) | `backend/ml/neural_networks.py:381-388` | Isaac Sim synthetic warehouse + optional Real-IAD overlay | `backend/training/stage_09_vision/` |
| 10 | Explainability (real SHAP + DiCE) | `backend/ml/explainability.py:73-147` | N/A (uses models from Stages 4-9) | `backend/training/stage_10_explainability/` |
| 20 | Red-team eval harness | (CI gate, not weights) | OWASP LLM01 + NIST AI RMF Agentic corpus | `backend/training/evals/redteam/` |

## Colab workflow ("free GPU" path)

Each stage directory contains a `train.py` written in **cell-style** format (using `# %%` separators) so it converts cleanly to a Jupyter notebook. To run on Colab:

1. Open [https://colab.research.google.com/](https://colab.research.google.com/) → New notebook.
2. Runtime → Change runtime type → **T4 GPU** (free tier) for Stages 4/5/6/9/10; **CPU** is fine for Stage 4/6 if you want to save GPU quota.
3. In the first cell, paste:
   ```python
   !git clone https://github.com/<your-repo>.git ai-embodied-agent
   %cd ai-embodied-agent/backend/training/stage_<NN>_<slug>
   !pip install -q -r requirements.txt
   ```
4. Open `train.py` in a Colab cell (`File → Upload` or paste) and split into cells by the `# %%` markers.
5. Run all cells. Training completes in 15–120 minutes depending on stage.
6. Output artefacts (`<model>.pt`, `<model>.metrics.json`) save to the Colab session storage. Download via `files.download()` or push to a DVC remote.
7. **Drop into the local repo:**
   ```
   ai-embodied-agent/models/<model>.pt
   ai-embodied-agent/models/<model>.metrics.json
   ai-embodied-agent/compliance/model-cards/<model>.md   # write this from the template
   ```
8. Add to DVC:
   ```bash
   dvc add models/<model>.pt
   git add models/<model>.pt.dvc models/<model>.metrics.json compliance/model-cards/<model>.md
   ```

## Stage-specific GPU sizing

| Stage | Free Colab (T4) sufficient? | Notes |
|---|---|---|
| 4 (Transformer for RUL) | YES | C-MAPSS is small (~10 MB); 30-60 min on T4 |
| 5 (Conv-AE on Real-IAD) | YES with sampling | Full Real-IAD is ~80 GB; use the per-category subset (~2-5 GB) |
| 6 (TFT on M5) | YES | M5 is moderate; 60-90 min on T4 |
| 7 (PPO Isaac Sim) | **NO** — Isaac Sim needs Omniverse + RTX GPU | **Alternative:** use `gymnasium-warehouse` env + `stable-baselines3` PPO on T4 |
| 8 (Dreamer-V3) | YES with reduced horizon | Use the "Dreamer-V3 lite" config; full version needs A100 |
| 9 (YOLOv10 fine-tune) | YES | Ultralytics YOLOv10 has Colab examples; T4 works |
| 10 (SHAP + DiCE) | YES (CPU works) | These are interpretability libs, not new training |

## What lands back in the repo

After each Colab training run, you (the operator) put these files in the working tree:

```
models/<model>.pt                              # Git LFS-tracked
models/<model>.metrics.json                    # JSON: hyperparams, eval metrics, training data SHA, seed
compliance/model-cards/<model>.md              # Annex IV minimum fields (see template)
```

Then the runtime (Stage 11+ LangGraph + Stage 11.5 model_inference_server) picks them up automatically via the model registry in `backend/ml/model_registry.py` (Stage 11).

## Pickle vs `.pt` vs `.safetensors`

| Format | Used for | Security |
|---|---|---|
| `.pt` (PyTorch state dict) | All neural networks | Safe ONLY if you trust the source (pickle allows arbitrary code on load) |
| `.safetensors` | All NEW models from Stage 13.5 forward | **Required by policy** — no arbitrary code; PQC-signable |
| `.pkl` (Python pickle) | NOT ALLOWED for runtime weights | Allowed only for transient training intermediates in `backend/training/` |

The PreToolUse hook blocks new `.pkl` files in `backend/ml/` or `models/`. Use `.safetensors`.

## Dataset access — see [data/datasets/CATALOG.md](../../data/datasets/CATALOG.md)

That catalog has per-dataset download command, license, size, SHA-256, and target stage.

## CI integration

When you push a new model:
- `scripts/check-model-cards.sh` verifies the three siblings (`.pt`, `.metrics.json`, model card) are present.
- `scripts/audit.sh` runs and verifies the theatrical-fallback count strictly decreased.
- `pytest backend/tests/training/test_<model>_inference.py` smoke-tests inference on a fixture input.

## Reproducibility

Every model card MUST record:
- Training data SHA-256 (from DVC).
- Random seed.
- Library versions (PyTorch, transformers, Ultralytics).
- Hardware (Colab T4 / RTX 4090 / etc.).
- Eval metrics on a frozen held-out set.

This is EU AI Act Article 11 / Annex IV evidence. The Annex IV pack generator (Stage 19) reads model cards to assemble the conformity bundle.
