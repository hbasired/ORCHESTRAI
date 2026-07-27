# Stage 4 — Predictive Maintenance (RUL Transformer)

Trains a compact Transformer for Remaining-Useful-Life (RUL) prediction on the C-MAPSS NASA Turbofan dataset.

## Files

- `train.py` — cell-style Python script (Colab-ready).
- `requirements.txt` — pinned deps for Colab.

## How to run on Colab (free T4 GPU)

1. https://colab.research.google.com/ → New notebook → Runtime → T4 GPU.
2. Cell 1:
   ```python
   !git clone <your-repo-url> ai-embodied-agent
   %cd ai-embodied-agent/backend/training/stage_04_predictive_maintenance
   !pip install -q -r requirements.txt
   ```
3. Cell 2 (download dataset):
   ```python
   !mkdir -p data && cd data && curl -L -o cmapss.zip "https://data.nasa.gov/download/ff5v-kuh6/application%2Fzip" && unzip -o cmapss.zip
   ```
4. Cell 3:
   ```python
   %run train.py
   ```
   Or: `File → Open notebook → Upload → train.py → Runtime → Run all` (uses `# %%` cell markers).
5. After ~30-60 minutes, you'll have:
   ```
   artefacts/
     stage_04_predictive_maintenance.safetensors   (or .pt fallback)
     stage_04_predictive_maintenance.metrics.json
   ```

## Drop into the local repo

```bash
# From the project root:
mkdir -p models compliance/model-cards
cp /path/to/colab/download/stage_04_predictive_maintenance.safetensors models/
cp /path/to/colab/download/stage_04_predictive_maintenance.metrics.json models/

# Author the model card (required for CI gate):
cp compliance/model-cards/TEMPLATE.md compliance/model-cards/stage_04_predictive_maintenance.md
# Fill in: intended use, limitations, training data license, eval method, known bias, version, contact.

# DVC-track:
dvc add models/stage_04_predictive_maintenance.safetensors
git add models/stage_04_predictive_maintenance.* compliance/model-cards/stage_04_predictive_maintenance.md
```

## Acceptance criteria

- Validation RMSE < 15 RUL units on FD001 (matches Heimes 2008 baseline; modern Transformer should achieve 10-13).
- Safetensors format (not pickle).
- All three siblings present: `.safetensors` + `.metrics.json` + model card.
- `scripts/audit.sh` count strictly less than baseline (the theatrical predictor in `backend/ml/neural_networks.py` is replaced by this model).

## What this replaces in the runtime

The Stage 11+ LangGraph `model_inference_server` (Stage 11.5) will register this model under tool name `predict_failure(equipment_id)`. Stage 11 `backend/ml/model_registry.py` reads `models/stage_04_predictive_maintenance.safetensors` on boot.

## Sim-to-real notes

C-MAPSS turbofans are aerospace engines. For warehouse / discrete manufacturing pilots, fine-tune on the customer's own MTBF data via DVC pipeline (Stage 4 hand-off block describes this).
