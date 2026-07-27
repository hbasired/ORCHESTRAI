# Independent Review — Stage 9 Depth-Hardening (transfer-learning defect classifier)

**Auditor**: independent `task-auditor` (did NOT implement this increment).
**Date**: 2026-06-14.
**Scope**: the 2026-06-14 Stage-9 depth increment — ResNet18 transfer learning on real NEU-CLS.
**ADR reviewed**: `compliance/decision-logs/2026-06-14_depth_09_defect_transfer_learning.md`.

## VERDICT: PASS

Claim — transfer-learning ResNet18 reaches **test accuracy 0.993 / macro-F1 0.993** (was 0.882 tiny CNN) on the
SAME seed-9 held-out split (no leakage) — is supported by the committed code, metrics, and on-disk weights. I found
no theatre, no fabrication, no leakage, and no weakened baseline. One execution caveat (below): the harness blocked
Python/pytest execution, so I could not personally re-run `tests/test_vision_defect.py`; the verdict rests on static
analysis + committed artifacts + the mechanical audit (which I did run).

## Execution caveat (transparency)

`python -m pytest` was **denied by the harness permission layer** in this session (Python execution blocked; only
read-only inspection — `git`, `ls`, `scripts/audit.sh` — was permitted). I therefore could NOT re-run
`tests/test_vision_defect.py` myself. Everything below is verified by reading source + committed metrics + on-disk
weights. The mechanical audit (`scripts/audit.sh`) I DID run: **TOTAL = 364**, equal to baseline.

## CRITICAL CHECK 1 — train/test leakage (the most important claim)

**No leakage. Confirmed by reading both loaders.**

- `backend/training/stage_09_defect/dataset.py::load_defect_data` (v1, grayscale 64×64) and
  `dataset_tl.py::load_defect_data_rgb` (v2, RGB 128×128) use **byte-for-byte identical split logic**:
  same `seed=9`, same `test_frac=0.2`, same `np.random.default_rng(seed)`, same per-class loop over
  `np.unique(y)`, same `rng.shuffle(idx)` / `n_test = max(1, round(len*0.2))` / `rng.shuffle(train_idx); rng.shuffle(test_idx)`
  (dataset.py:49-58 vs dataset_tl.py:54-62). Because both consume the same dataset in the same row order and draw
  from the same seeded RNG stream, the test indices are **identical**. The held-out 288 test images are the exact
  ones the ResNet never trains on. The only difference is preprocessing (RGB-128 + ImageNet norm vs gray-64).
- The val split for best-checkpoint selection is carved **from the train set only** (train_transfer.py:68-74),
  so there is **no test peeking** — best checkpoint is chosen on val, test is touched once at the end
  (train_transfer.py:116-118).
- Strong corroboration: `test_defect_classifier_beats_baseline_on_real_holdout` (test_vision_defect.py:92-102)
  loads `data.X_test` from the **v1 grayscale loader** and feeds those images through the new ResNet18 (its
  `_coerce_rgb` upconverts grayscale→RGB and resizes). This cross-checks that the v1 and v2 test sets are the
  same images — and that the model generalises on genuinely held-out data.

## CRITICAL CHECK 2 — metrics.json honesty

`models/defect_classifier.metrics.json` — read in full:
- `test_accuracy = 0.9931`, `macro_f1 = 0.9931`, `best_val_acc = 1.0`, `majority_baseline = 0.1667`,
  `prev_tiny_cnn_test_accuracy = 0.8819`. The "+11.1 pt" claim = 0.9931 − 0.8819 ≈ **+11.12 pt** — accurate.
- **Per-class precision/recall/F1 present** for all 6 classes (lines 77-108).
- **Confusion matrix present** (6×6, lines 109-158): 286 correct / 288 (2 off-diagonal: one class_1→class_3,
  one class_2→class_0) → 286/288 = 0.99306 → rounds to 0.9931. **Internally consistent**.
- `n_train=978, n_val=174, n_test=288` (1450 total; consistent with ~1800-image NEU-CLS minus the val carve).
- `val_curve` (12 epochs) is a plausible monotone-ish learning curve peaking at 1.0 (best-val selection).
- Honest caveats present: PROXY note (G-035), "SAME held-out split as the tiny-CNN baseline (no leakage)".

## CRITICAL CHECK 3 — inference glue (arch auto-detect, contract preserved, honest-unavailable)

`backend/ml/defect_classifier.py` — read in full:
- `_load()` reads `arch` from the checkpoint (line 59): `resnet18` → torchvision backbone + ImageNet norm
  (lines 61-73); else the **old tiny-CNN** is rebuilt (lines 74-95). Back-compat preserved.
- `weights_only=True` on `torch.load` (line 58) — safe deserialization.
- Public `classify()` (lines 98-121) returns the unchanged contract `{label_index, label, confidence,
  probabilities}`; softmax-normalised; accepts grayscale/RGB/PIL of any size (coercion in `_coerce_rgb`/`_to_pil_rgb`).
- Honest-unavailable: raises `ModelUnavailableError` if torch absent or weights missing (lines 51-57). NEVER
  fabricates a class — confirmed (no `random.*`, no hardcoded label).

## Artifacts on disk

- `models/defect_classifier.pt` — **44.8 MB** (consistent with a ResNet18 state_dict; a tiny 3-conv CNN would be
  ~KB, so the weight is genuinely the deep model). Gitignored (normal for binary weights).
- Model card `compliance/model-cards/defect_classifier.md` is a real **v2** card (ResNet18, 0.993, +11.1pt,
  no-leakage + PROXY caveats, v1 tiny-CNN retained as baseline) — not a stub.

## Mechanical audit

`bash scripts/audit.sh` → **TOTAL 364 = baseline 364** (`--no-baseline-drop`, as the ADR D4 justifies: replacing a
model adds no grep-counted theatre). I grepped the new files — no `random.uniform|random.choice|generateMockState|
_get_demo_*|RESPONSES =|MODELS =` in `dataset_tl.py`, `train_transfer.py`, or `defect_classifier.py`. Zero theatre.

## Gaps / overclaims / leakage found

**None that block.** Honest scope items (already disclosed, not gaps): NEU-CLS is a PROXY for deployment imagery
(re-fit before pilot, G-035); the 99.3% is benchmark-only.

Minor nit (non-blocking, cosmetic): the v1 tiny-CNN test set was 64×64 grayscale; feeding those exact arrays through
the ResNet via upconvert means the held-out **images** are identical but the **preprocessing** the model sees on the
holdout-sanity test differs slightly from training (gray-upconvert vs native RGB). This does not affect the headline
0.993 (which is measured natively in `train_transfer.py`); it only makes the in-repo sanity test mildly conservative.
Not a defect.

## Independent confirmation table

| Claim | Confirmed? | Basis |
|---|---|---|
| Same seed-9 held-out split, no leakage | YES | both loaders read; identical seeded split logic |
| test acc 0.993 / macro-F1 0.993 | YES (artifact) | metrics.json; confusion matrix 286/288 internally consistent |
| per-class P/R + confusion present | YES | metrics.json lines 77-158 |
| best-val selection, no test peeking | YES | train_transfer.py:68-74,116-118 |
| arch auto-detect + back-compat + contract preserved | YES | defect_classifier.py:59-95,98-121 |
| honest-unavailable, never fabricates | YES | defect_classifier.py:51-57; no random/mock in new code |
| audit holds 364, zero new theatre | YES (I ran audit.sh) | TOTAL 364 |
| tests pass | NOT RE-RUN | pytest execution blocked by harness; tests read and assert real behaviour |
