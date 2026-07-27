---
status: done
stage: 09
slug: vision_defect_detection
created: 2026-06-13
---

# Stage 09 — Vision / Defect Detection (real YOLOv8n + NEU-CLS defect classifier)

> Quality & Inspection capability (gap G-016, PRD v3 §18 Stage 9): (1) **de-mock `vision_model.py`** from a
> random-detection stub to **real pretrained YOLOv8n inference** with honest `ModelUnavailableError` (no
> fabrication) — and remove the fabricating `_mock_process_loop` in `video_processor.py`; (2) train a **real
> surface-defect classifier** on the **NEU-CLS** public benchmark (6 steel-surface defect classes) — a genuine,
> measurable model (88.2% test acc / 0.881 macro-F1 vs 16.7% majority baseline). Honest scope: NEU-CLS steel
> surfaces are a PROXY for the deployment's real warehouse/line imagery — re-fit before pilot (G-035); the
> Quality head-agent integration + real-time reject path stay later (Stage 11+/17). This is the first stage since
> Stage 6 to **strictly decrease** the audit baseline (396 → 383) by removing real theatrical fabrication.
> Cross-links: KB_25 (Quality & Inspection domain) · KB_02/KB_03 · ml-engineer SKILL.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–10 + §5)

- [x] Read `KB_24` + `KB_25` (Quality & Inspection is the N-domain head this vision capability feeds; G-016). Aligned.
- [x] Read `audits/OPEN_GAPS_LEDGER.md`. Folded for Stage 9: **G-016** (Quality & Inspection vision/defect — ADVANCED here: real detector + defect classifier; head-agent integration stays Stage 11+), **G-027** (free-cost — honoured: torch CPU, public CC dataset), **G-047-class** grep-invisible theatre (the vision de-mock removes both grep-counted AND a now-broken mock-loop reference).
- [x] **Free-cost only:** torch CPU + torchvision + ultralytics (already installed) + the public NEU-CLS dataset; no LLM in this stage's loop; OSS/local only. No committed keys.
- [ ] **Stage explainer HTML:** before close, write `research/stage-explainers/STAGE_09/index.html` (self-contained, honest BUILT/PARTIAL/PLANNED, real file paths + measured numbers).

## Pre-requisites

- Stage(s) closed: 2–8 (sim, broker, predictor, demand, slice v0, PPO substrate, world model).
- Decision logs honoured: `2026-06-11_strategic_product_reset.md` (PRD v3 §18 puts defect detection at Stage 9), `2026-06-13_world_model_causal_diagnose.md` (the honest de-mock pattern). New ADR: `2026-06-13_vision_defect_detection.md`.
- KB files at minimum version: KB_02 (model inventory), KB_03 (datasets), KB_25 (Quality & Inspection domain).
- Gaps pulled in: **G-016** (advanced here).

## Acceptance criteria

- [x] **AC1 — `vision_model.py` de-mocked to real YOLOv8n.** Removed `_generate_mock_detections()` (random boxes) + the fabricating `_mock_process_loop` in `video_processor.py`. `detect()`/`detect_batch()` run real pretrained YOLOv8n (`backend/yolov8n.pt`) and raise `ModelUnavailableError` if ultralytics/weights absent — NEVER fabricate. Verified by `test_vision_defect.py` (+ `test_models.py::TestVisionModel`).
- [x] **AC2 — Real defect classifier, trained, free + local.** `backend/training/stage_09_defect/` (HF-`datasets` loader for the real **NEU-CLS** benchmark + `train.py` + `config.yaml`) trains a CNN → `models/defect_classifier.{pt,metrics.json}`. Verified by committed metrics + `test_vision_defect.py`.
- [x] **AC3 — Measured win vs baseline.** Test **accuracy 88.2% / macro-F1 0.881** on a held-out stratified split, vs **16.7% majority-class baseline** (recorded in metrics + KB_23). Real public dataset, real measured result (not 100% — an honest tiny-CNN number; SOTA ~99% needs bigger nets).
- [x] **AC4 — Honest inference glue.** `backend/ml/defect_classifier.py::DefectClassifier.classify(image)` → `{label, confidence, probabilities}`; raises `ModelUnavailableError` if torch/weights absent (mirrors `failure_predictor`/`world_model`); `weights_only=True` load. Verified by `test_vision_defect.py`.
- [x] **AC5 — Honest scope/proxy boundary.** Model card + ADR state: NEU-CLS steel surfaces are a PROXY for deployment imagery (re-fit before pilot, G-035); the Quality head-agent integration + real-time reject path are NOT built (Stage 11+/17); label names are positional (class_0..5). No overclaim.
- [x] **AC6 — Tests green + no regression.** New `test_vision_defect.py` passes; `test_models.py::TestVisionModel` updated to the honest contract; Stage-6/7/8 suites still pass (67 passed, 1 honest skip).
- [x] **AC7 — Audit strictly decreases.** 396 → **383** (removed `mock_detections` ×6 + `random.*` in the vision mock). First strict decrease since Stage 6 — **no `--no-baseline-drop`**.
- [x] **AC8 — Model card + KB + explainer.** `compliance/model-cards/defect_classifier.md`; KB_02/03/23/25 updated; explainer HTML.
- [x] **AC9 — Independent audit: PASS** (2026-06-13, fresh task-auditor agent → `audits/STAGE_09_independent_review.md`). 25 Stage-9 + 42 regression tests re-run green; audit 383<396 confirmed (mock_detections 0); classifier spot-check 0.85 on a held-out slice with **0 train/test leakage** (hashed), believable-not-leaky; de-mock genuine; proxy caveats verified; no overclaim. One cosmetic wording note (stale 'mock mode' log) fixed.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/training/stage_09_defect/dataset.py` | Load real NEU-CLS via HF `datasets`; cache, grayscale 64×64, stratified split |
| `backend/training/stage_09_defect/train.py` | Train CNN → `models/defect_classifier.{pt,metrics.json}` |
| `backend/training/stage_09_defect/config.yaml` | Hyperparameters + seeds |
| `backend/ml/defect_classifier.py` | `DefectClassifier` inference glue; honest `ModelUnavailableError` |
| `backend/tests/test_vision_defect.py` | Real-YOLO + defect-classifier + honest-unavailable tests |
| `compliance/model-cards/defect_classifier.md` | Annex IV model card (real dataset, metrics, proxy caveat) |
| `compliance/decision-logs/2026-06-13_vision_defect_detection.md` | ADR |
| `research/stage-explainers/STAGE_09/index.html` | Stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/ml/vision_model.py` | De-mock → real YOLOv8n inference + `ModelUnavailableError`; remove `_generate_mock_detections` |
| `backend/pipeline/video_processor.py` | Remove fabricating `_mock_process_loop`; disable video honestly when OpenCV/source absent |
| `backend/tests/test_models.py` | Update `TestVisionModel` to the honest contract |

## Files to DELETE

| Path | Reason |
|---|---|
| (none — methods removed in-file) | — |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_02_Models_Inventory.md` (defect_classifier row + vision de-mock note)
- `knowledge-base/KB_03_Datasets_Catalog.md` (NEU-CLS dataset entry)
- `knowledge-base/KB_23_Evals_and_Benchmarks.md` (Stage 9 defect eval, measured)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (Quality & Inspection / vision capability)

## Verification commands

```bash
bash scripts/audit.sh   # strictly decreases: 396 -> 383
cd backend && python training/stage_09_defect/train.py --config training/stage_09_defect/config.yaml
cd backend && python -m pytest tests/test_vision_defect.py tests/test_models.py -q
bash scripts/independent-audit.sh 9
```

## Audit target

- Pre-stage baseline: **396**.
- Target: **383** (strict decrease). Removed: `mock_detections` ×6 and the `random.uniform/randint` calls in `vision_model._generate_mock_detections` + the now-broken `video_processor._mock_process_loop` reference. No `--no-baseline-drop` — Stage 9 genuinely de-mocks.

## Role

- Primary: `ml-engineer` (vision/defect model work, weights, card — owns `backend/ml/`, `backend/training/`, `models/`).
- Secondary: `backend-engineer` (`video_processor.py`), `task-auditor` (AC9), `agentic-governance-engineer` (ADR).

## Risks / unknowns

- **Proxy dataset (G-035):** NEU-CLS steel-surface ≠ this project's warehouse/line imagery. The 88.2% is a real but proxy-domain number; re-fit before pilot. Stated, not oversold.
- **YOLOv8n is COCO-pretrained** (people/forklift/box-class detection), not warehouse-fine-tuned — genuine inference, but warehouse fine-tune (Isaac Sim synthetic per KB_03) is a later refinement.
- The Quality & Inspection **head-agent** (G-016 full) + real-time reject path are NOT built here — that's Stage 11+ runtime / Stage 17 safety. This stage delivers the two real models + the de-mock.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-requisites (pre-filled from STAGE_08_world_model_causal_diagnose.md hand-off)


- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*
