# ADR — Stage 9: Vision / Defect Detection (real YOLOv8n + NEU-CLS defect classifier)

**Date**: 2026-06-13
**Status**: Accepted
**Stage**: 9 (Vision / defect detection — Quality & Inspection, G-016; PRD v3 §18)
**Author personas**: `ml-engineer` (primary) + `backend-engineer` (video_processor) + `agentic-governance-engineer` (ADR)
**Relates**: PRD v3 §18 (Stage 9 = vision/defect); the honest de-mock pattern from Stages 7–8.

---

## Context

PRD v3 §18 places vision/defect detection at Stage 9; gap G-016 (Quality & Inspection: vision/YOLO real-time
defect reject) targets Stage 5/9. The repo had a theatrical `vision_model.py` that fabricated random robot
detections (`_generate_mock_detections`, audit-counted `mock_detections`) when ultralytics/weights were absent,
plus a `video_processor._mock_process_loop` that fed those fake detections into the state manager. ultralytics
8.3.40, torchvision, `yolov8n.pt`, and a working network were confirmed available locally.

## Decisions

**D1 — De-mock `vision_model.py` to real YOLOv8n.** Removed `_generate_mock_detections()`; `detect()`/
`detect_batch()` now run real pretrained YOLOv8n (`backend/yolov8n.pt`) and raise `ModelUnavailableError` if
ultralytics/weights are absent — never fabricate. Added `is_available()`/`_ensure_loaded()` (mirrors
`failure_predictor`/`world_model`). Verified: real YOLO executes (Results object) on a frame.

**D2 — Remove the fabricating `_mock_process_loop`.** `video_processor.py` no longer starts a loop that emits
random detections when OpenCV/video is unavailable; video processing is simply disabled honestly (no fabricated
robot positions ever reach the state manager). This also fixed a now-broken reference to the removed method.

**D3 — Real defect classifier on the NEU-CLS public benchmark.** `backend/training/stage_09_defect/` loads the
real `newguyme/neu_cls` dataset (6 steel-surface defect classes) via HuggingFace `datasets`, trains a small CNN
(grayscale 64×64, torch CPU), and saves `models/defect_classifier.{pt,metrics.json}`. **Measured: 88.2% test
accuracy / 0.881 macro-F1 on a held-out stratified split vs 16.7% majority-class baseline.** A genuine, real-data,
measurable result — consistent with the project's real-dataset pattern (AI4I, Bike-Sharing). Inference glue
`backend/ml/defect_classifier.py` is honest (`ModelUnavailableError`; `weights_only=True`).

**D4 — Honest proxy + scope boundary (no overclaim).** NEU-CLS steel surfaces are a PROXY for the deployment's
warehouse/line imagery — re-fit before pilot (G-035). Labels are positional (`class_0..5`; canonical NEU order
documented but the mapping is unverified). YOLOv8n is COCO-pretrained, not warehouse-fine-tuned. The Quality
**head-agent** integration + real-time reject/divert path are NOT built here — Stage 11+ (runtime) / Stage 17
(safety). The 88.2% is not 100% and that is stated, not hidden.

**D5 — Audit STRICTLY DECREASES (396 → 383).** Removing `_generate_mock_detections` (×6 `mock_detections`) +
its `random.uniform/randint` calls + the `_mock_process_loop` reference is a genuine de-mock the grep catches —
the **first strict baseline decrease since Stage 6**. **No `--no-baseline-drop`** (unlike Stages 7–8, which were
additive-only).

## Why

- The vision stub was real theatre feeding fake robot positions into the live state path; de-mocking it is both
  an honesty win and a genuine baseline decrease.
- A real public defect dataset (NEU-CLS) gives a genuine, measurable Quality & Inspection model — the right way
  to advance G-016 without fabricating, and feasible free/local on CPU (~35 s training).
- Honest proxy framing keeps the claim defensible: a real measured number on real (if proxy-domain) data, with
  re-fit gated by G-035.

## Consequences

- New: `backend/training/stage_09_defect/{dataset,train,config}.py`, `backend/ml/defect_classifier.py`,
  `models/defect_classifier.{pt,metrics.json}`, `backend/tests/test_vision_defect.py`,
  `compliance/model-cards/defect_classifier.md`, `research/stage-explainers/STAGE_09/`.
- Modified: `backend/ml/vision_model.py` (de-mock), `backend/pipeline/video_processor.py` (remove mock loop),
  `backend/tests/test_models.py` (`TestVisionModel` honest contract).
- Audit **396 → 383** (strict decrease). 67 tests pass across vision/defect/models/world/diagnosis/RL/slice/predictor (1 honest skip).
- **G-016 ADVANCED** (real detector + defect classifier; head-agent integration + reject path remain Stage 11+/17).
  G-035 still gates real-image claims.

## Alternatives rejected

1. **Synthetic defect images.** Rejected: a real public benchmark (NEU-CLS) is stronger and more honest than
   invented images, and it was feasible locally.
2. **Train a SOTA defect detector (~99%).** Rejected: needs a large net + GPU; the small CNN's honest 88.2% on
   CPU is the right free/local scope, with the proxy + re-fit caveats stated.
3. **Keep the mock fallback "for tests".** Rejected: fabricating detections into the live state path is exactly
   the theatre the project forbids; honest `ModelUnavailableError` + skipping when unavailable is correct.

## References

- Metrics: `models/defect_classifier.metrics.json`. Dataset: `newguyme/neu_cls` (NEU-CLS).
- KB_02 (model inventory), KB_03 (datasets), KB_23 (eval), KB_25 (Quality & Inspection).
- Tests: `backend/tests/test_vision_defect.py`, `backend/tests/test_models.py`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:29+00:00 -->
<!-- signature: 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 -->
