# ADR — Stage 9 Depth-Hardening: transfer-learning defect classifier (ResNet18, 88.2% → 99.3%)

**Date**: 2026-06-14
**Status**: Accepted
**Stage**: 9 (depth-hardening increment 2/5 — deepens the closed Stage-9 implementation; not a new stage number)
**Author personas**: `ml-engineer` (primary) + `agentic-governance-engineer` (ADR)
**Relates**: deepens `2026-06-13_vision_defect_detection.md` (v1 toy CNN). Part of the Stages 6–10 depth-hardening
pass (plan `this-is-not-the-eventual-garden.md`; research §16.5). Follows CLAUDE.md Hard Rule 11/11a (full depth first).

---

## Context

The v1 Stage-9 classifier was a toy 3-conv grayscale CNN at 64×64 → **88.2%** on the real NEU-CLS benchmark. SOTA
on NEU-CLS is ~99% (research §16.5: SH-DETR 91.72% detection, Swin/transfer-learning classification). 88.2% where
a deeper free/local path exists is exactly the shallow choice Hard Rule 11a forbids.

## Decisions

**D1 — Transfer learning with a pretrained ResNet18 (the deep, honest, CPU-feasible path).** New
`backend/training/stage_09_defect/{dataset_tl,train_transfer}.py`: pretrained ImageNet **ResNet18**, final fc → 6
classes, **layer4 + fc fine-tuned** (backbone frozen — fast on CPU: ~13 s/epoch), RGB **128×128** ImageNet-
normalised, light H/V-flip augmentation, cosine schedule, best-val checkpoint selection. **Measured test accuracy
0.993 / macro-F1 0.993** (best val 1.000), a **+11.1 pt** jump from 0.882 — SOTA-competitive. Per-class
precision/recall + confusion matrix recorded in `models/defect_classifier.metrics.json`.

**D2 — No leakage: identical held-out split.** `dataset_tl.load_defect_data_rgb` reuses the **exact** stratified
split (seed 9, 20% test) as the v1 grayscale loader, so the held-out test images are the same ones the model never
trains on — the +11.1 pt gain is a genuine held-out improvement, and the existing
`test_defect_classifier_beats_baseline_on_real_holdout` (which uses the v1 loader's test set) stays honest.

**D3 — Inference glue deepened, contract preserved.** `backend/ml/defect_classifier.py` auto-detects `arch` from
the checkpoint: `resnet18` → builds the torchvision backbone + RGB/ImageNet preprocessing (accepts grayscale/RGB/
PIL of any size, resized internally); old tiny-CNN checkpoints still load (back-compat). Public `classify(...)`
output unchanged (`{label_index, label, confidence, probabilities}`), honest `ModelUnavailableError`,
`weights_only=True`. The v1 toy CNN (`train.py`) is retained as the documented shallow baseline.

**D4 — Audit holds at 364 (`--no-baseline-drop`), additive.** Replacing the model adds no grep-counted theatre
(neither version fabricates); count unchanged confirms zero theatrical patterns introduced.

## Why
- 88.2% from a toy net, where transfer learning reaches ~99% free/local on CPU, is a depth shortfall — Hard Rule
  11a says the deeper version IS the first implementation. Transfer learning is the canonical, credible, honest way.
- Reusing the identical split keeps the improvement claim honest (real held-out, no leakage) and keeps the existing
  test meaningful.

## Consequences
- New: `dataset_tl.py`, `train_transfer.py`, this ADR, explainer refresh. Modified: `ml/defect_classifier.py`
  (arch-detecting RGB loader), `models/defect_classifier.{pt,metrics.json}` (now ResNet18), model card → v2.
- 25 defect/model tests pass (1 honest skip); audit holds 364; no regression.
- G-016 advances: defect classifier now SOTA-competitive (benchmark scope; real-fleet re-fit = G-035).

## Alternatives rejected
1. **Keep the 88.2% toy CNN.** Rejected — the shallow choice Hard Rule 11a forbids.
2. **Full fine-tune / 224×224 / Swin-Transformer.** Heavier on CPU for marginal gain on an easy dataset; frozen-
   backbone + layer4 at 128×128 already reaches 99.3%. Full fine-tune / a transformer backbone is a future option.
3. **MobileNetV3 backbone.** Comparable; ResNet18 chosen for ubiquity/credibility and it trains fast enough here.

## References
- `backend/training/stage_09_defect/train_transfer.py` (test acc 0.993) · `models/defect_classifier.metrics.json`.
- `backend/ml/defect_classifier.py` (arch-detecting inference). Model card `compliance/model-cards/defect_classifier.md`.
- Research: `research/initial-research.md` §16.5. KB: KB_02, KB_23, KB_25.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:29+00:00 -->
<!-- signature: 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 -->
