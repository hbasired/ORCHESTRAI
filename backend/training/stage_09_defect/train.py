"""Stage 9 — train the surface-defect classifier (real NEU-CLS dataset, free + local).

Writes:
  models/defect_classifier.pt            (state_dict + arch + label names + img size)
  models/defect_classifier.metrics.json  (seed, hyperparams, test accuracy + macro-F1 vs majority baseline)

Honest: real public dataset (NEU-CLS, 6 steel-surface defect classes); the metrics record measured held-out
accuracy + macro-F1 against the majority-class baseline (1/6). Grayscale steel surfaces are a PROXY for this
project's eventual warehouse/line imagery — re-fit on the deployment's real images before any pilot (G-035).

Usage (from backend/):
    python training/stage_09_defect/train.py --config training/stage_09_defect/config.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_09_defect.dataset import HF_DATASET_ID, IMG_SIZE, load_defect_data  # noqa: E402

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"   # repo-root models/ (project convention)
WEIGHTS = MODELS_DIR / "defect_classifier.pt"
METRICS = MODELS_DIR / "defect_classifier.metrics.json"


def _load_config(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    cfg, stack = {}, None
    root = {}; stack = [(-1, root)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]; val = val.strip()
        if val == "":
            d = {}; parent[key] = d; stack.append((indent, d))
        else:
            try:
                parent[key] = int(val)
            except ValueError:
                try:
                    parent[key] = float(val)
                except ValueError:
                    parent[key] = val
    return root


def main() -> int:
    import torch
    import torch.nn as nn

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    args = ap.parse_args()
    cfg = _load_config(Path(args.config))
    dcfg, mcfg, tcfg = cfg["data"], cfg["model"], cfg["train"]
    seed = int(tcfg["seed"])
    torch.manual_seed(seed); np.random.seed(seed)

    t0 = time.time()
    data = load_defect_data(test_frac=float(dcfg["test_frac"]), seed=int(dcfg["seed"]))
    n_classes = len(np.unique(data.y_train))

    class DefectCNN(nn.Module):
        def __init__(self, c1, c2, n_cls, dropout):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv2d(1, c1, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),   # 64->32
                nn.Conv2d(c1, c2, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),  # 32->16
                nn.Conv2d(c2, c2, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(4),  # ->4x4
            )
            self.head = nn.Sequential(nn.Flatten(), nn.Dropout(dropout),
                                      nn.Linear(c2 * 16, 64), nn.ReLU(), nn.Linear(64, n_cls))

        def forward(self, x):
            return self.head(self.net(x))

    net = DefectCNN(int(mcfg["conv1"]), int(mcfg["conv2"]), n_classes, float(mcfg["dropout"]))
    opt = torch.optim.Adam(net.parameters(), lr=float(tcfg["lr"]))
    lossf = nn.CrossEntropyLoss()
    Xtr = torch.as_tensor(data.X_train); ytr = torch.as_tensor(data.y_train)
    Xte = torch.as_tensor(data.X_test); yte = torch.as_tensor(data.y_test)

    bs = int(tcfg["batch_size"]); n = len(Xtr); curve = []
    for ep in range(int(tcfg["epochs"])):
        net.train(); idx = torch.randperm(n)
        for s in range(0, n, bs):
            mb = idx[s:s + bs]
            opt.zero_grad(); loss = lossf(net(Xtr[mb]), ytr[mb]); loss.backward(); opt.step()
        if (ep + 1) % 3 == 0 or ep == 0:
            net.eval()
            with torch.no_grad():
                acc = float((net(Xte).argmax(1) == yte).float().mean().item())
            curve.append({"epoch": ep + 1, "test_acc": round(acc, 4)})

    net.eval()
    with torch.no_grad():
        pred = net(Xte).argmax(1).numpy()
    yte_np = data.y_test
    acc = float((pred == yte_np).mean())
    # Macro-F1 (no sklearn dependency assumed).
    f1s = []
    for c in range(n_classes):
        tp = int(((pred == c) & (yte_np == c)).sum())
        fp = int(((pred == c) & (yte_np != c)).sum())
        fn = int(((pred != c) & (yte_np == c)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    macro_f1 = float(np.mean(f1s))
    majority = float(np.bincount(data.y_train).max() / len(data.y_train))  # majority-class baseline

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": net.state_dict(), "img_size": IMG_SIZE, "n_classes": n_classes,
                "conv1": int(mcfg["conv1"]), "conv2": int(mcfg["conv2"]),
                "dropout": float(mcfg["dropout"]), "label_names": data.label_names}, WEIGHTS)

    metrics = {
        "model": "defect_classifier", "stage": 9,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": "6-class steel-surface defect classification (Quality & Inspection, G-016)",
        "dataset": HF_DATASET_ID, "dataset_note": "real public NEU-CLS benchmark (6 classes); grayscale 64x64",
        "framework": "torch CPU CNN (3 conv + FC)",
        "n_train": int(len(Xtr)), "n_test": int(len(Xte)), "n_classes": n_classes,
        "hyperparameters": {**{k: mcfg[k] for k in mcfg}, **{k: tcfg[k] for k in tcfg}},
        "train_seconds": round(time.time() - t0, 1),
        "test_curve": curve,
        "test_accuracy": round(acc, 4),
        "test_macro_f1": round(macro_f1, 4),
        "majority_class_baseline_acc": round(majority, 4),
        "beats_baseline": bool(acc > majority),
        "honest_note": ("real NEU-CLS steel-surface data — a PROXY for this project's eventual warehouse/line "
                        "imagery; re-fit on deployment images before pilot (G-035). Label names are positional "
                        "(class_0..5); canonical NEU order is crazing/inclusion/patches/pitted/rolled-in/scratches."),
        "license": "NEU-CLS is a public research benchmark; project code Apache-2.0",
        "reproduce": "python training/stage_09_defect/train.py --config training/stage_09_defect/config.yaml",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"trained in {metrics['train_seconds']}s  n_train={len(Xtr)} n_test={len(Xte)} classes={n_classes}")
    print(f"test accuracy={acc:.4f}  macro-F1={macro_f1:.4f}  vs majority baseline {majority:.4f}  "
          f"beats_baseline={metrics['beats_baseline']}")
    print(f"weights -> {WEIGHTS}")
    print(f"metrics -> {METRICS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
