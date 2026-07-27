"""Load the REAL NEU surface-defect classification dataset for Stage 9.

Source: `newguyme/neu_cls` on the HuggingFace Hub — the NEU-CLS benchmark (6 steel-surface
defect classes: crazing, inclusion, patches, pitted_surface, rolled-in_scale, scratches;
~1800 grayscale 200x200 images). A real, public, widely-cited dataset (NOT synthetic).

We resize to grayscale 64x64 for fast CPU training and do a deterministic stratified split.
The dataset is cached by `datasets`/`huggingface_hub`; the first run downloads it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

HF_DATASET_ID = "newguyme/neu_cls"
IMG_SIZE = 64


@dataclass
class DefectData:
    X_train: np.ndarray  # (N, 1, 64, 64) float32 in [0,1]
    y_train: np.ndarray  # (N,) int
    X_test: np.ndarray
    y_test: np.ndarray
    label_names: list[str]


def _to_gray_array(pil_img) -> np.ndarray:
    img = pil_img.convert("L").resize((IMG_SIZE, IMG_SIZE))
    return (np.asarray(img, dtype=np.float32) / 255.0)[None, :, :]   # (1, H, W)


def load_defect_data(test_frac: float = 0.2, seed: int = 9) -> DefectData:
    """Download (cached) + preprocess + stratified split. Real dataset; no fabrication."""
    from datasets import load_dataset

    ds = load_dataset(HF_DATASET_ID, split="train")
    # Resolve label names from the ClassLabel feature when available.
    feat = ds.features.get("label")
    label_names = list(getattr(feat, "names", [])) or [f"class_{i}" for i in range(6)]

    X = np.stack([_to_gray_array(ex["image"]) for ex in ds]).astype(np.float32)
    y = np.asarray([int(ex["label"]) for ex in ds], dtype=np.int64)

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

    return DefectData(
        X_train=X[train_idx], y_train=y[train_idx],
        X_test=X[test_idx], y_test=y[test_idx],
        label_names=label_names,
    )


__all__ = ["DefectData", "load_defect_data", "HF_DATASET_ID", "IMG_SIZE"]
