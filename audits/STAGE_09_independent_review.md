# Stage 09 — Independent Review (Vision / Defect Detection)

**Reviewer**: fresh `task-auditor` agent (read-only). **Date**: 2026-06-13.
**Target**: `tasks/STAGE_09_vision_defect_detection.md` (ACs 1–9; AC9 is this review).
**Verdict**: **PASS**

---

## Independence statement

I did NOT implement Stage 9. I am a separate agent invoked solely to verify it. I read only the
files named in the audit scope, ran the named commands myself, and independently re-derived the
classifier's held-out accuracy and the train/test disjointness from the cached dataset. I edited
exactly one file: this review. I fixed nothing and ledgered nothing (no later-stage gaps found).

## What I ran (real output)

**1. Stage 9 tests** — `cd backend && python -m pytest tests/test_vision_defect.py tests/test_models.py -q`
```
25 passed, 1 skipped, 5 warnings in 15.19s
```
The 1 skip is `test_vision_detect_raises_when_unavailable` — it skips *because* the in-repo
`yolov8n.pt` is genuinely resolvable, i.e. real YOLO IS available (honest skip, not a hidden failure).

**2. No-regression (Stages 4/6/7/8)** — `pytest tests/test_world_model.py tests/test_diagnosis.py tests/test_intervention_rl.py tests/test_slice_intervene.py tests/test_failure_predictor.py -q`
```
42 passed, 1 warning in 10.38s
```
No regressions from the de-mock.

**3. Mechanical audit** — `bash scripts/audit.sh`
```
  mock_detections                   0
  ...
  TOTAL                           383
Baseline (from .audit-baseline): 396
OK: count decreased from 396 to 383.
```
`.audit-baseline` file = `396`. TOTAL **383 < 396** — genuine strict decrease; `mock_detections == 0`.

**4. Independent classifier spot-check** (deterministic, real cached NEU-CLS):
```
available: True
n_test: 288 n_train: 1152 labels: ['class_0'..'class_5']
holdout spot-check acc on 120 samples: 0.85
test class counts: {0:48,1:48,2:48,3:48,4:48,5:48}   # perfectly stratified
```

**5. Leakage / determinism probe** (hashed image content across the two splits):
```
train: 1152 test: 288 image-content overlap (leakage): 0
deterministic split: True
```
Zero image-content overlap between train and test → **no leakage**. Split is reproducible.

## Findings per acceptance criterion

| AC | Claim | Independently confirmed? | Evidence |
|---|---|---|---|
| AC1 | `vision_model.py` de-mocked → real YOLOv8n; `_generate_mock_detections` gone; `ModelUnavailableError` on absence; never fabricates | **YES** | `vision_model.py:66-83` `_ensure_loaded` raises `ModelUnavailableError`; `:98,:180` `detect`/`detect_batch` gate before real `model.predict`. grep: `_generate_mock_detections` exists only in comments/test-assertions, never as a method. No `random.*` in the file. |
| AC1 (video) | `_mock_process_loop` removed; video disabled honestly | **YES** | `video_processor.py:150-152` documents removal; `start()` `:89-93` sets `is_running=False` on ImportError, no fake detections. `_process_loop` `:104-148` only reads real frames or sleeps. (See minor note below re: a stale log string.) |
| AC2 | Real NEU-CLS classifier trained, free + local | **YES** | `dataset.py:19,41` loads `newguyme/neu_cls` via HF `datasets`; `train.py` writes `models/defect_classifier.{pt,metrics.json}` (both present; `.pt` 193 KB). Re-loaded the real dataset myself: 1440 real images. |
| AC3 | 88.2% acc / 0.881 macro-F1 vs 16.7% baseline | **YES** | `metrics.json`: `test_accuracy 0.8819`, `test_macro_f1 0.8813`, `majority_class_baseline_acc 0.1667`. My own 120-sample held-out check = 0.85 (consistent). `test_curve` rises 0.32→0.88 over 18 epochs (real learning, not leaky). |
| AC4 | Honest inference glue; `ModelUnavailableError`; `weights_only=True` | **YES** | `defect_classifier.py:48,50` raise on missing torch/weights; `:54` `torch.load(..., weights_only=True)`; `:86` `classify` calls `_load()` first. `test_defect_honest_unavailable` passes. |
| AC5 | Honest proxy/scope boundary, no overclaim | **YES** | Model card `:32-38` (PROXY/G-035, positional labels, not actuator-wired, head-agent deferred Stage 11+/17); ADR D4 `:37-41`; metrics `honest_note`. Card explicitly states 88.2% "does not transfer" and SOTA ~99% needs larger nets. |
| AC6 | Tests green + no regression | **YES** | 25 passed/1 honest skip (Stage 9); 42 passed (no-regression). |
| AC7 | Audit strictly decreases 396→383, no `--no-baseline-drop` | **YES** | audit.sh output above; ADR D5 confirms no flag. Genuine theatre removal, not metric-gaming (see scan). |
| AC8 | Model card + KB + explainer HTML | **YES (artifacts present)** | `compliance/model-cards/defect_classifier.md` present; `research/stage-explainers/STAGE_09/index.html` present (10 KB). KB diffs flagged in mechanical audit §2. |
| AC9 | Independent audit PASS | **THIS FILE** | PASS. |

## Theatrical-work scan

- grep `_generate_mock_detections|_mock_process_loop|mock_detections` across `backend/` → matches only in
  (a) removal comments, (b) `test_models.py:25` and `test_vision_defect.py:59` assertions that the method is
  *gone*. No live fabrication path.
- grep `random.(uniform|randint|choice)` in `vision_model.py` → **no matches**.
- `defect_classifier.py`, `dataset.py`, `train.py` contain no `random.*`/mock literals (training seeds via
  `np.random.default_rng`/`torch.manual_seed` are legitimate reproducibility, in `training/`).
- No `--no-verify` / `--force` / `--no-baseline-drop` used. No hard-rule violation (no LLM-actuator path here;
  no new crypto).

## Judgement

- **De-mock genuine?** Yes. The random-detection method and the fabricating video loop are truly removed (not
  renamed/hidden); both `detect` paths and the video pipeline now either run real YOLOv8n or fail honestly. The
  396→383 drop is a real removal of audit-counted theatre, not gaming. `ModelUnavailableError` is correctly
  reused from `failure_predictor` (imported at `vision_model.py:20`; `test_models.py:31` resolves it through
  the module binding — works).
- **Classifier real, not leaky?** Yes. Real public NEU-CLS (`newguyme/neu_cls`), stratified 80/20 (1152/288,
  48/class), independently verified **zero image-content overlap** between splits. 88.2% is believable and
  appropriately *below* NEU-CLS SOTA (~99%) for a tiny 3-conv CPU CNN on 64×64 grayscale — not suspiciously
  perfect. My re-run reproduced 0.85 on a held-out slice.
- **Honest unavailability?** Yes. `DefectClassifier` raises `ModelUnavailableError` (never fabricates) when
  torch/weights absent; `weights_only=True` load.
- **Honest proxy caveats?** Yes. Card + ADR + metrics all state: NEU-CLS is a PROXY (G-035, re-fit before
  pilot), labels positional/unverified, YOLOv8n COCO-pretrained not fine-tuned, Quality head-agent + reject
  path deferred to Stage 11+/17. No overclaim detected.

## Minor (non-blocking) observation

- `video_processor.py:74` still logs `"Could not open video source, using mock mode"` when `cv2.VideoCapture`
  fails to open a source. The string is misleading (there is **no** mock mode anymore — `_capture` is set to
  `None` and the loop merely sleeps, emitting nothing), but it is **cosmetic only**: no fabricated detections
  are produced on this path, so it is not a theatre/correctness defect. Recommend tidying the log wording in a
  future touch of this file; does not block close.

## VERDICT: **PASS**

No gaps requiring fix before close. No new later-stage gaps to ledger (G-016 advance + G-035 re-fit gate are
already tracked and correctly carried forward by the stage). The de-mock is genuine, the defect classifier is a
real, non-leaky, honestly-scoped model with a measured win over a fair baseline, and the strict baseline
decrease (396→383) reflects real removal of theatre.
