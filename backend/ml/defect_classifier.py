"""Stage 9 — surface-defect classifier inference glue (Quality & Inspection, G-016).

Loads the defect classifier trained by `backend/training/stage_09_defect/` on the real NEU-CLS benchmark
(6 steel-surface defect classes) and classifies an image. Honest by design (mirrors `failure_predictor` /
`world_model`): raises `ModelUnavailableError` if torch/weights are absent — NEVER fabricates a class.

Stage 9 depth-hardening (2026-06-14): the production weight is now a **transfer-learning ResNet18**
(pretrained ImageNet, fine-tuned on NEU-CLS RGB 128×128) — deeper and more accurate than the original toy
64×64 grayscale CNN. The loader auto-detects the architecture from the checkpoint (`arch` key), so the old
tiny-CNN checkpoint still loads (back-compat). The public `classify(...)` contract is unchanged: it accepts a
grayscale/RGB array or a PIL image of any size and returns `{label_index, label, confidence, probabilities}`.

Proxy/sim caveat (G-035): NEU-CLS steel surfaces are a proxy for the deployment's real warehouse/line imagery;
re-fit on real images before any pilot. Not actuator-wired; the Stage-17 safety wrapper precedes any reject action.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from ml.failure_predictor import ModelUnavailableError  # reuse the honest-unavailable contract

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_WEIGHTS = _MODELS_DIR / "defect_classifier.pt"


class DefectClassifier:
    """Surface-defect classifier. Honest about unavailability — never fabricates."""

    def __init__(self, weights_path: Optional[Path] = None) -> None:
        self._path = Path(weights_path) if weights_path else _WEIGHTS
        self._net = None
        self._torch = None
        self._meta: Optional[dict] = None

    def is_available(self) -> bool:
        try:
            self._load()
            return True
        except ModelUnavailableError:
            return False

    def _load(self) -> None:
        if self._net is not None:
            return
        try:
            import torch
            import torch.nn as nn
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"PyTorch not available: {e}")
        if not self._path.exists():
            raise ModelUnavailableError(
                f"trained defect classifier not found: {self._path} — run "
                f"backend/training/stage_09_defect/train_transfer.py"
            )
        ckpt = torch.load(str(self._path), map_location="cpu", weights_only=True)
        arch = ckpt.get("arch", "tiny_cnn")

        if arch == "resnet18":
            from torchvision.models import resnet18
            net = resnet18(weights=None)
            net.fc = nn.Linear(net.fc.in_features, int(ckpt["n_classes"]))
            net.load_state_dict(ckpt["state_dict"])
            net.eval()
            self._net = net
            self._meta = {
                "arch": "resnet18", "img_size": int(ckpt["img_size"]),
                "label_names": list(ckpt["label_names"]),
                "norm_mean": np.asarray(ckpt["norm_mean"], dtype=np.float32),
                "norm_std": np.asarray(ckpt["norm_std"], dtype=np.float32),
            }
        else:  # back-compat: original tiny grayscale CNN
            c1, c2, n_cls = int(ckpt["conv1"]), int(ckpt["conv2"]), int(ckpt["n_classes"])
            dropout = float(ckpt["dropout"])

            class DefectCNN(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Conv2d(1, c1, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                        nn.Conv2d(c1, c2, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                        nn.Conv2d(c2, c2, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
                    )
                    self.head = nn.Sequential(nn.Flatten(), nn.Dropout(dropout),
                                              nn.Linear(c2 * 16, 64), nn.ReLU(), nn.Linear(64, n_cls))

                def forward(self, x):
                    return self.head(self.net(x))

            net = DefectCNN(); net.load_state_dict(ckpt["state_dict"]); net.eval()
            self._net = net
            self._meta = {"arch": "tiny_cnn", "img_size": int(ckpt["img_size"]),
                          "label_names": list(ckpt["label_names"])}
        self._torch = torch

    def classify(self, image) -> dict:
        """Classify a defect image.

        `image`: a grayscale (H,W)/(1,H,W) or RGB (H,W,3)/(3,H,W) array (in [0,1] or [0,255]) OR a PIL image,
        of ANY size (it is resized internally). Returns ``{label_index, label, confidence, probabilities}``.
        Raises ``ModelUnavailableError`` if the brain/lib is absent (never fabricates).
        """
        self._load()
        if self._meta["arch"] == "resnet18":
            x = self._coerce_rgb(image)            # (3, S, S) ImageNet-normalised
        else:
            x = self._coerce_gray(image)[None, :, :]  # (1, S, S)
        t = self._torch.as_tensor(x[None, ...], dtype=self._torch.float32)
        with self._torch.no_grad():
            logits = self._net(t)
            probs = self._torch.softmax(logits, dim=1)[0].numpy()
        idx = int(probs.argmax())
        names = self._meta["label_names"]
        return {
            "label_index": idx,
            "label": names[idx] if idx < len(names) else f"class_{idx}",
            "confidence": float(probs[idx]),
            "probabilities": [float(p) for p in probs],
        }

    # ---- preprocessing -----------------------------------------------------

    def _to_pil_rgb(self, image, size: int):
        """Coerce any supported input to an RGB PIL image resized to (size, size)."""
        from PIL import Image
        if hasattr(image, "convert"):  # already PIL
            return image.convert("RGB").resize((size, size))
        arr = np.asarray(image, dtype=np.float32)
        if arr.ndim == 3 and arr.shape[0] in (1, 3) and arr.shape[0] < arr.shape[-1]:
            arr = np.transpose(arr, (1, 2, 0))   # (C,H,W) -> (H,W,C)
        if arr.ndim == 3 and arr.shape[2] == 1:
            arr = arr[:, :, 0]
        if arr.max() <= 1.5:                     # looks like [0,1]
            arr = arr * 255.0
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        mode = "RGB" if (arr.ndim == 3 and arr.shape[2] == 3) else "L"
        return Image.fromarray(arr, mode=mode).convert("RGB").resize((size, size))

    def _coerce_rgb(self, image) -> np.ndarray:
        size = self._meta["img_size"]
        pil = self._to_pil_rgb(image, size)
        arr = np.asarray(pil, dtype=np.float32) / 255.0                 # (S,S,3)
        arr = (arr - self._meta["norm_mean"]) / self._meta["norm_std"]
        return np.transpose(arr, (2, 0, 1)).astype(np.float32)          # (3,S,S)

    def _coerce_gray(self, image) -> np.ndarray:
        size = self._meta["img_size"]
        if hasattr(image, "convert"):  # PIL
            img = image.convert("L").resize((size, size))
            return np.asarray(img, dtype=np.float32) / 255.0
        arr = np.asarray(image, dtype=np.float32)
        if arr.ndim == 3 and arr.shape[0] == 1:
            arr = arr[0]
        if arr.ndim != 2:
            raise ValueError(f"image must be (H,W) or (1,H,W) or PIL; got shape {arr.shape}")
        if arr.max() > 1.5:
            arr = arr / 255.0
        if arr.shape != (size, size):
            from PIL import Image
            arr = np.asarray(Image.fromarray((arr * 255).astype(np.uint8)).resize((size, size)),
                             dtype=np.float32) / 255.0
        return arr


_default: Optional[DefectClassifier] = None


def get_defect_classifier() -> DefectClassifier:
    global _default
    if _default is None:
        _default = DefectClassifier()
    return _default


__all__ = ["DefectClassifier", "get_defect_classifier", "ModelUnavailableError"]
