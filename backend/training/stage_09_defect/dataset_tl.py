"""Stage 9 depth-hardening — RGB dataset loader for TRANSFER LEARNING on real NEU-CLS.

Same real dataset as `dataset.py` (`newguyme/neu_cls`, 6 steel-surface classes) and the SAME deterministic
stratified split (seed 9, 20% test) so the held-out test images are identical to the ones the old loader
exposes — i.e. the transfer model never trains on them and the existing held-out test stays honest. The
difference: images are loaded as **RGB at a higher resolution** (default 128×128, ImageNet-normalised) so a
pretrained ImageNet backbone (ResNet18) can be fine-tuned. Grayscale NEU images are replicated to 3 channels.

Real, public dataset; no fabrication. Cached by `datasets`/`huggingface_hub` on first run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

HF_DATASET_ID = "newguyme/neu_cls"
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class DefectDataRGB:
    X_train: np.ndarray  # (N, 3, S, S) float32, ImageNet-normalised
    y_train: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    label_names: list[str]
    img_size: int


def _to_rgb_array(pil_img, size: int) -> np.ndarray:
    img = pil_img.convert("RGB").resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0           # (S, S, 3) in [0,1]
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD                # ImageNet normalise
    return np.transpose(arr, (2, 0, 1))                       # (3, S, S)


def load_defect_data_rgb(img_size: int = 128, test_frac: float = 0.2, seed: int = 9) -> DefectDataRGB:
    """Download (cached) + preprocess to RGB + the SAME stratified split as dataset.load_defect_data."""
    from datasets import load_dataset

    ds = load_dataset(HF_DATASET_ID, split="train")
    feat = ds.features.get("label")
    label_names = list(getattr(feat, "names", [])) or [f"class_{i}" for i in range(6)]

    X = np.stack([_to_rgb_array(ex["image"], img_size) for ex in ds]).astype(np.float32)
    y = np.asarray([int(ex["label"]) for ex in ds], dtype=np.int64)

    # IDENTICAL split logic to dataset.load_defect_data (same seed) → identical held-out test indices.
    rng = np.random.default_rng(seed)
    test_idx, train_idx = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        n_test = max(1, int(round(len(idx) * test_frac)))
        test_idx.extend(idx[:n_test].tolist())
        train_idx.extend(idx[n_test:].tolist())
    rng.shuffle(train_idx); rng.shuffle(test_idx)
    train_idx = np.asarray(train_idx); test_idx = np.asarray(test_idx)

    return DefectDataRGB(
        X_train=X[train_idx], y_train=y[train_idx],
        X_test=X[test_idx], y_test=y[test_idx],
        label_names=label_names, img_size=img_size,
    )


__all__ = ["DefectDataRGB", "load_defect_data_rgb", "HF_DATASET_ID", "IMAGENET_MEAN", "IMAGENET_STD"]
