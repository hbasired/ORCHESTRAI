---
name: Datasets Catalog
description: Every approved dataset with source URL, license, size, download command, target model, sanity-check notebook
type: catalog
last-updated: 2026-06-13-stage9
---

# KB_03 — Datasets Catalog

## Purpose
Every dataset we are licensed to use, with everything needed to reproduce a training run: source URL, license, size, download command, target model, and a sanity-check notebook entry point.

## Source of truth
- `data/datasets/<name>/CARD.md` per dataset
- `<name>.dvc` files in the data folder (Stage 1 introduces DVC)
- Training notebooks under `backend/training/`

## Versioning protocol

Every dataset must have:
1. `data/datasets/<name>/CARD.md` — license, source URL, size, SHA256, mirror URL (HuggingFace Hub or Kaggle), download command, intended model, known limitations.
2. `data/datasets/<name>.dvc` — DVC tracking pointer with content hash; CI rejects training runs that reference an un-versioned dataset.
3. An entry in this table.

## Catalog

### Stage 4 — Predictive maintenance

| Dataset | License | Target model | Size | Source | Mirror | Status |
|---|---|---|---|---|---|---|
| **NASA C-MAPSS Turbofan RUL** | CC0 | LSTM RUL | ~50 MB | https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data | https://www.kaggle.com/datasets/behrad3d/nasa-cmaps | not-downloaded |
| **AI4I 2020 Predictive Maintenance** | CC BY 4.0 | ANN failure classifier | <5 MB | https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset | https://www.kaggle.com/datasets/stephanmatzka/predictive-maintenance-dataset-ai4i-2020 | not-downloaded |
| **SECOM (optional)** | UCI standard | imbalanced fault detection demo | small | https://archive.ics.uci.edu/ml/datasets/SECOM | https://www.kaggle.com/datasets/paresh2047/uci-semcom | not-downloaded |
| **Bosch CNC Machining** (real industrial vibration) | Open (Bosch Research) | 1D-CNN vibration anomaly (extension) | medium | https://github.com/boschresearch/CNC_Machining | https://archive.ics.uci.edu/dataset/752/bosch+cnc+machining+dataset | not-downloaded |

### Stage 5 — Defect / anomaly detection

| Dataset | License | Target model | Size | Source | Mirror | Status |
|---|---|---|---|---|---|---|
| **NEU-DET / NEU-CLS** | Public research | CNN defect classifier (ResNet-18 transfer) | small (1800 images) | https://www.kaggle.com/datasets/kaustubhdikshit/neu-surface-defect-database | — | not-downloaded |
| **Real-IAD** (NEW per refresh — **primary** AD dataset) | Commercial-friendly | Convolutional autoencoder anomaly detection | medium | Project page (TBD; mirror to HF Hub on first download) | — | not-downloaded |
| **KSDD2 (Kolektor Surface Defect Dataset 2)** | Commercial-friendly | fallback / fast-iteration AD | small | https://www.vicos.si/Downloads/KolektorSDD2 | — | not-downloaded |
| **AITEX Fabric Defect** | CC BY | textile-vertical AD | small | public | — | not-downloaded |
| **MVTec AD** (now **secondary**, research-only) | Research-only | benchmark comparison only | medium | https://www.mvtec.com/company/research/datasets/mvtec-ad | — | not-downloaded |
| **MVTec AD 2** | Research-only | v2 benchmark | larger | https://www.mvtec.com/company/research/datasets/mvtec-ad-2 | — | not-downloaded |

> **License note**: pilot deployments cannot rely on MVTec AD due to its research-only license; Real-IAD is the production primary. See refresh in `research/initial-research.md` §6.2 and `compliance/risk-register.md`.

### Stage 6 — Demand forecasting

| Dataset | License | Target model | Size | Source | Mirror | Status |
|---|---|---|---|---|---|---|
| **M5 Walmart Forecasting** | Public (Kaggle competition rules) | LSTM + Informer/PatchTST | large (3,049 series × 5.4 yrs) | https://www.kaggle.com/competitions/m5-forecasting-accuracy | — | not-downloaded |

### Stage 9 — Robot detection

| Dataset | License | Target model | Size | Source | Mirror | Status |
|---|---|---|---|---|---|---|
| **Isaac Sim synthetic warehouse** (NEW per refresh — **primary**) | Apache 2.0 (Isaac Sim) | YOLOv8 fine-tune | self-generated | https://developer.nvidia.com/isaac/sim · https://github.com/isaac-sim/IsaacSim | — | pipeline-not-built |
| **Aggregated logistics imagery** (optional) | Mixed; track per-source | YOLOv8 fine-tune | medium | https://pmc.ncbi.nlm.nih.gov/articles/PMC12031185/ | — | not-collected |

### Industrial-datasets master lists (for future sourcing)

- Fraunhofer: https://www.bigdata-ai.fraunhofer.de/s/datasets/index.html
- Curated GitHub list (Nicolas Jourdan): https://github.com/nicolasj92/industrial-ml-datasets
- DLR review paper: https://elib.dlr.de/211380/1/Review%20Publicly%20Available%20Datasets%20Manufacturing%20Systems.pdf

## DVC (initialised in Stage 1)

Stage 1 (2026-05-11) installed the bootstrap layout:

- `dvc.yaml` at repo root (no `stages:` entries yet — Stage 5 writes the first).
- `.dvc/config` with a `local` remote pointed at `../dvc-store/`. This is
  intentional: a real S3 / GCS remote is Stage 14 work. A local store is
  reproducible enough for the first round of dataset pulls without
  spending cloud budget pre-Series-A.
- `data/datasets/.gitkeep` + `data/datasets/CARD.template.md` checked in
  so the layout is visible.
- `dvc[s3]==3.58.0` pinned in `backend/requirements.txt`.

Recipe for the first real dataset (Stage 5):

```
# from repo root, with backend venv active
cd data/datasets
mkdir neu_det && cp CARD.template.md neu_det/CARD.md && $EDITOR neu_det/CARD.md
# download the archive into neu_det/, then:
cd ../..
dvc add data/datasets/neu_det/
git add data/datasets/neu_det.dvc data/datasets/.gitignore
git commit -m "feat(data): add NEU-DET via DVC"
```

CI rejects training runs that reference a dataset folder without a sibling `.dvc` pointer.

## License risk register (cross-reference)

The full license-risk register lives in `compliance/risk-register.md`. The two material items today:
1. **MVTec AD = research-only** — must not be the primary for any commercial pilot. Mitigation: Real-IAD primary.
2. **Logistics imagery aggregator** — mixed per-source license; if used, each source must be tracked separately and only commercial-friendly subsets shipped to production fine-tunes.

### AI4I 2020 Predictive Maintenance (added Stage 4, 2026-06-01) — FIRST real dataset used

| Field | Value |
|---|---|
| Source | UCI ML Repository #601 — `https://archive.ics.uci.edu/dataset/601` |
| License | **CC BY 4.0** (commercial-friendly with attribution) |
| Size | 10,000 rows tabular; ~3.4% machine failures (imbalanced) |
| Features used | Type(L/M/H), air/process temp [K], rotational speed [rpm], torque [Nm], tool wear [min] + engineered temp_diff, power |
| Dropped (leakage) | `TWF/HDF/PWF/OSF/RNF` (compose the target), `UDI`, `Product ID` |
| Target | `Machine failure` (binary) |
| Used by | `pdm_failure_predictor` (KB_02) via `notebooks/stage04_ai4i_tabular_colab.ipynb` |
| Caveat | First-cut PROXY (CNC-machine signals, not robots / not our SimPy telemetry). Re-fit on real data before pilot (G-035). |

### UCI Bike Sharing #275 (added Stage 5, 2026-06-01) — demand-forecasting proxy

| Field | Value |
|---|---|
| Source | UCI ML Repository #275 — `https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip` (hour.csv) |
| License | **CC BY 4.0** (commercial-friendly with attribution) |
| Size | ~17,400 hourly rows; target `cnt` (0–977) |
| Features | cnt + temp/atemp/hum/windspeed + cyclical hr/weekday/month + workingday/holiday/weathersit/season |
| Dropped (leakage) | `casual`, `registered` (sum to `cnt`) |
| Used by | `demand_forecaster` (KB_02) — **chronological** split (no leakage) |
| Caveat | PROXY (bike demand, not warehouse orders). Re-fit on real demand before pilot (G-035). |

### NEU-CLS surface defects (added Stage 9, 2026-06-13) — defect-classification proxy

| Field | Value |
|---|---|
| Source | HuggingFace `newguyme/neu_cls` (the NEU-CLS / NEU surface-defect benchmark; Northeastern University) |
| License | Public research benchmark (widely cited NEU-CLS). Pulled at train time via HF `datasets`; cached locally. |
| Size | ~1,800 grayscale images, 6 balanced defect classes (~300/class); we use the HF `train` split (1,440) re-split 1152/288 |
| Classes | canonical: crazing, inclusion, patches, pitted_surface, rolled-in_scale, scratches (labels positional in the HF set → `class_0..5`, mapping unverified) |
| Used by | `defect_classifier` (KB_02) — stratified 80/20 split, grayscale 64×64 |
| Caveat | PROXY (steel surfaces, not warehouse/line imagery). Re-fit on deployment images before pilot (G-035). |

## Last verified
- 2026-06-13 (Stage 9 close) — NEU-CLS (`newguyme/neu_cls`) added — defect-classification proxy; first image dataset used.
- 2026-06-01 (Stage 5 close) — UCI Bike Sharing #275 (CC BY 4.0) added — demand-forecasting proxy.
- 2026-06-01 (Stage 4 close) — AI4I 2020 (CC BY 4.0) added — first real dataset actually pulled + used (loaded from UCI at train time; license commercial-friendly).
- 2026-05-11 — Plan-mode session. No datasets downloaded yet; this is the bootstrap catalog. Stage 4 will be the first stage that actually pulls a dataset and adds a real CARD.md.
- **2026-05-11 (Stage 1 close)** — DVC bootstrap landed (`dvc.yaml`, `.dvc/config`, local remote). Every "not-downloaded" row above is still accurate; the dataset CARD template ships under `data/datasets/CARD.template.md`.
