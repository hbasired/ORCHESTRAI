"""Stage 9 depth-hardening — TRANSFER LEARNING defect classifier (pretrained ResNet18 on real NEU-CLS).

Deepens the toy 64×64 grayscale 3-conv CNN (88.2%) into a real transfer-learning model: a pretrained
ImageNet **ResNet18** with its last block (layer4) + a new head fine-tuned on NEU-CLS at RGB 128×128, with
light augmentation. SOTA on NEU-CLS is ~99% with deep models; transfer learning is the honest free/local/CPU
way to get there. Reports test accuracy + macro-F1 + per-class precision/recall + confusion matrix.

Writes (overwrites the canonical defect weights with the deeper model):
  models/defect_classifier.pt            (arch=resnet18, img_size, label_names, ImageNet norm, state_dict)
  models/defect_classifier.metrics.json  (seed, hyperparams, val curve, test acc/F1/per-class/confusion vs baseline)

Usage (from backend/):
    python training/stage_09_defect/train_transfer.py            # defaults
    python training/stage_09_defect/train_transfer.py --epochs 12 --img 128
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_09_defect.dataset_tl import (  # noqa: E402
    load_defect_data_rgb, IMAGENET_MEAN, IMAGENET_STD,
)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
WEIGHTS = MODELS_DIR / "defect_classifier.pt"
METRICS = MODELS_DIR / "defect_classifier.metrics.json"


def _augment(x, torch):
    """Light, label-preserving augmentation on normalised tensors: random H/V flips (NEU defects are
    orientation-agnostic). Cheap on CPU; sufficient for this dataset."""
    if torch.rand(1).item() < 0.5:
        x = torch.flip(x, dims=[3])   # horizontal
    if torch.rand(1).item() < 0.5:
        x = torch.flip(x, dims=[2])   # vertical
    return x


def main() -> int:
    import torch
    import torch.nn as nn
    from torchvision.models import resnet18, ResNet18_Weights
    from sklearn.metrics import f1_score, confusion_matrix, classification_report

    ap = argparse.ArgumentParser()
    ap.add_argument("--img", type=int, default=128)
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--seed", type=int, default=9)
    ap.add_argument("--val_frac", type=float, default=0.15)
    args = ap.parse_args()
    torch.manual_seed(args.seed); np.random.seed(args.seed)

    t0 = time.time()
    data = load_defect_data_rgb(img_size=args.img, seed=args.seed)
    n_cls = len(data.label_names)

    # carve a val split from train (stratified) for best-checkpoint selection (no test peeking).
    rng = np.random.default_rng(args.seed)
    tr_idx, va_idx = [], []
    for c in np.unique(data.y_train):
        idx = np.where(data.y_train == c)[0]; rng.shuffle(idx)
        k = max(1, int(round(len(idx) * args.val_frac)))
        va_idx.extend(idx[:k].tolist()); tr_idx.extend(idx[k:].tolist())
    tr_idx = np.asarray(tr_idx); va_idx = np.asarray(va_idx)
    Xtr = torch.as_tensor(data.X_train[tr_idx]); ytr = torch.as_tensor(data.y_train[tr_idx])
    Xva = torch.as_tensor(data.X_train[va_idx]); yva = torch.as_tensor(data.y_train[va_idx])
    Xte = torch.as_tensor(data.X_test); yte = data.y_test

    # pretrained ResNet18; freeze everything except layer4 + the new fc head (fine-tune last block).
    net = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    net.fc = nn.Linear(net.fc.in_features, n_cls)
    for name, p in net.named_parameters():
        p.requires_grad = name.startswith("layer4.") or name.startswith("fc.")
    trainable = [p for p in net.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    lossf = nn.CrossEntropyLoss()

    def _eval(X, y):
        net.eval()
        with torch.no_grad():
            preds = []
            for s in range(0, len(X), 128):
                preds.append(net(X[s:s + 128]).argmax(1))
            p = torch.cat(preds).numpy()
        return p, float((p == np.asarray(y)).mean())

    bs, n = args.batch, len(Xtr); curve = []
    best_va, best_state = -1.0, None
    for ep in range(args.epochs):
        net.train(); idx = torch.randperm(n)
        for s in range(0, n, bs):
            mb = idx[s:s + bs]
            xb = _augment(Xtr[mb], torch)
            opt.zero_grad()
            loss = lossf(net(xb), ytr[mb])
            loss.backward(); opt.step()
        sched.step()
        _, va_acc = _eval(Xva, yva.numpy())
        if va_acc > best_va:
            best_va = va_acc
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        curve.append({"epoch": ep + 1, "val_acc": round(va_acc, 4)})
        print(f"  epoch {ep+1:2d}/{args.epochs}  val_acc={va_acc:.4f}  (best {best_va:.4f})")

    if best_state is not None:
        net.load_state_dict(best_state)
    test_pred, test_acc = _eval(Xte, yte)
    macro_f1 = float(f1_score(yte, test_pred, average="macro"))
    cm = confusion_matrix(yte, test_pred).tolist()
    report = classification_report(yte, test_pred, target_names=data.label_names,
                                   output_dict=True, zero_division=0)
    baseline = 1.0 / n_cls

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({
        "arch": "resnet18", "state_dict": net.state_dict(), "n_classes": n_cls,
        "img_size": args.img, "label_names": list(data.label_names),
        "norm_mean": IMAGENET_MEAN.tolist(), "norm_std": IMAGENET_STD.tolist(),
        "finetuned": "layer4+fc (backbone frozen)",
    }, WEIGHTS)

    metrics = {
        "model": "defect_classifier", "stage": 9, "arch": "resnet18 (ImageNet) transfer learning",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": "6-class steel-surface defect classification (NEU-CLS) — Stage 9 deepened (transfer learning)",
        "dataset": "newguyme/neu_cls (real NEU-CLS benchmark; ~1800 imgs, 6 classes)",
        "img_size": args.img, "rgb": True, "normalisation": "ImageNet mean/std",
        "finetune": "ResNet18 pretrained; layer4 + fc unfrozen (backbone frozen); light H/V-flip augmentation",
        "hyperparameters": {"epochs": args.epochs, "batch_size": args.batch, "lr": args.lr,
                            "seed": args.seed, "val_frac": args.val_frac, "scheduler": "cosine"},
        "n_train": int(len(tr_idx)), "n_val": int(len(va_idx)), "n_test": int(len(yte)),
        "val_curve": curve, "best_val_acc": round(best_va, 4),
        "test_accuracy": round(test_acc, 4), "macro_f1": round(macro_f1, 4),
        "majority_baseline": round(baseline, 4),
        "per_class": {k: {"precision": round(v["precision"], 3), "recall": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3)}
                      for k, v in report.items() if k in data.label_names},
        "confusion_matrix": cm, "confusion_labels": list(data.label_names),
        "prev_tiny_cnn_test_accuracy": 0.8819,
        "train_seconds": round(time.time() - t0, 1),
        "honest_note": ("Transfer learning (pretrained ResNet18) on the REAL NEU-CLS benchmark; SAME held-out "
                        "split as the tiny-CNN baseline (no leakage). NEU-CLS steel surfaces are a PROXY for "
                        "real line/warehouse imagery — re-fit before pilot (G-035)."),
        "license": "Apache-2.0 (project code); NEU-CLS public benchmark; ResNet18 weights torchvision (BSD)",
        "reproduce": "python training/stage_09_defect/train_transfer.py --epochs 12 --img 128",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"\ntrained in {metrics['train_seconds']}s  n_train={len(tr_idx)} n_val={len(va_idx)} n_test={len(yte)}")
    print(f"TEST acc={test_acc:.4f}  macro-F1={macro_f1:.4f}  (tiny-CNN baseline 0.8819; majority {baseline:.3f})")
    print(f"weights -> {WEIGHTS}\nmetrics -> {METRICS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
