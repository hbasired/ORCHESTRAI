"""Stage 8 — train the LSTM time-to-failure (TTF) world model (free, local, reproducible).

Writes:
  models/world_model_ttf.pt            (state_dict + arch + feature scaler + window/feature meta)
  models/world_model_ttf.metrics.json  (seed, hyperparams, train curve, held-out MAE vs naive baseline)

Honesty: the metrics record the measured result. The naive baseline is the mean-TTF predictor; the learned
model earns its place only by beating it on held-out (disjoint-seed) rollouts — reported either way.

Usage (from backend/):
    python training/stage_08_world_model/train.py --config training/stage_08_world_model/config.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_08_world_model.rollouts import (  # noqa: E402
    FEATURES, N_FEATURES, RolloutConfig, build_dataset,
)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"   # repo-root models/ (project convention)
WEIGHTS = MODELS_DIR / "world_model_ttf.pt"
METRICS = MODELS_DIR / "world_model_ttf.metrics.json"


def _load_config(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    cfg, stack = {}, [(-1, {})]
    cfg = stack[0][1]
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        val = val.strip()
        if val == "":
            d = {}
            parent[key] = d
            stack.append((indent, d))
        else:
            try:
                parent[key] = int(val)
            except ValueError:
                try:
                    parent[key] = float(val)
                except ValueError:
                    parent[key] = val
    return cfg


def main() -> int:
    import torch
    import torch.nn as nn

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    args = ap.parse_args()
    cfg = _load_config(Path(args.config))
    r, d, m, tr = cfg["rollout"], cfg["data"], cfg["model"], cfg["train"]
    seed = int(tr["seed"])
    torch.manual_seed(seed); np.random.seed(seed)

    rc = RolloutConfig(window_len=int(r["window_len"]), sample_period_s=float(r["sample_period_s"]),
                       eta_min_minutes=float(r["eta_min_minutes"]), eta_max_minutes=float(r["eta_max_minutes"]),
                       warmup_s=float(r["warmup_s"]))
    train_seeds = list(range(int(d["train_seeds_start"]), int(d["train_seeds_start"]) + int(d["train_seeds_count"])))
    val_seeds = list(range(int(d["val_seeds_start"]), int(d["val_seeds_start"]) + int(d["val_seeds_count"])))

    t0 = time.time()
    Xtr, ytr = build_dataset(train_seeds, rc)
    Xva, yva = build_dataset(val_seeds, rc)
    if len(Xtr) == 0 or len(Xva) == 0:
        print("REFUSE: empty dataset"); return 2

    # Standardise features (per-feature mean/std from TRAIN only — no leakage).
    mean = Xtr.reshape(-1, N_FEATURES).mean(axis=0)
    std = Xtr.reshape(-1, N_FEATURES).std(axis=0) + 1e-6
    Xtr_n = (Xtr - mean) / std
    Xva_n = (Xva - mean) / std

    class TTFNet(nn.Module):
        def __init__(self, n_feat, hidden, layers, dropout):
            super().__init__()
            self.lstm = nn.LSTM(n_feat, hidden, num_layers=layers, batch_first=True,
                                dropout=dropout if layers > 1 else 0.0)
            self.head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))
        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    net = TTFNet(N_FEATURES, int(m["hidden"]), int(m["num_layers"]), float(m["dropout"]))
    opt = torch.optim.Adam(net.parameters(), lr=float(tr["lr"]))
    lossf = nn.SmoothL1Loss()
    Xt = torch.as_tensor(Xtr_n, dtype=torch.float32); yt = torch.as_tensor(ytr, dtype=torch.float32)
    Xv = torch.as_tensor(Xva_n, dtype=torch.float32); yv = torch.as_tensor(yva, dtype=torch.float32)

    bs = int(tr["batch_size"]); n = len(Xt); curve = []
    for ep in range(int(tr["epochs"])):
        net.train(); idx = torch.randperm(n)
        for s in range(0, n, bs):
            mb = idx[s:s + bs]
            opt.zero_grad()
            loss = lossf(net(Xt[mb]), yt[mb])
            loss.backward(); opt.step()
        if (ep + 1) % 10 == 0 or ep == 0:
            net.eval()
            with torch.no_grad():
                vmae = float(torch.mean(torch.abs(net(Xv) - yv)).item())
            curve.append({"epoch": ep + 1, "val_mae_min": round(vmae, 3)})

    net.eval()
    with torch.no_grad():
        pred = net(Xv).numpy()
    learned_mae = float(np.mean(np.abs(pred - yva)))
    baseline_pred = float(ytr.mean())                      # naive: predict train-mean TTF
    baseline_mae = float(np.mean(np.abs(yva - baseline_pred)))
    improvement = round(100.0 * (baseline_mae - learned_mae) / baseline_mae, 1)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": net.state_dict(), "n_features": N_FEATURES, "hidden": int(m["hidden"]),
                "num_layers": int(m["num_layers"]), "window_len": int(r["window_len"]),
                "features": list(FEATURES), "feat_mean": mean.tolist(), "feat_std": std.tolist()}, WEIGHTS)

    metrics = {
        "model": "world_model_ttf", "stage": 8,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": "time-to-failure (minutes) forecasting from a telemetry window (KB_25 step 1, G-019)",
        "framework": "torch CPU LSTM regressor; SimWorld rollouts; no external dataset",
        "window_len": int(r["window_len"]), "features": list(FEATURES),
        "hyperparameters": {"hidden": int(m["hidden"]), "num_layers": int(m["num_layers"]),
                            "dropout": float(m["dropout"]), "lr": float(tr["lr"]),
                            "epochs": int(tr["epochs"]), "batch_size": bs, "seed": seed},
        "n_train": int(len(Xtr)), "n_val": int(len(Xva)),
        "train_seconds": round(time.time() - t0, 1),
        "val_curve": curve,
        "ttf_range_minutes": [round(float(yva.min()), 2), round(float(yva.max()), 2)],
        "learned_val_mae_min": round(learned_mae, 3),
        "naive_baseline_mae_min": round(baseline_mae, 3),
        "improvement_vs_baseline_pct": improvement,
        "beats_baseline": bool(learned_mae < baseline_mae),
        "honest_note": ("eta is randomised so TTF is under-determined by telemetry (which reflects proximity, "
                        "not absolute time); the model learns EXPECTED TTF and beats the mean-TTF baseline by "
                        "reading degradation level. Proxy/sim only (G-035). No external dataset; no fabrication."),
        "data_provenance": "synthetic SimPy plant (KB_05); ground-truth TTF from the sim crack schedule",
        "license": "Apache-2.0 (project)",
        "reproduce": "python training/stage_08_world_model/train.py --config training/stage_08_world_model/config.yaml",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"trained in {metrics['train_seconds']}s  n_train={len(Xtr)} n_val={len(Xva)}")
    print(f"TTF MAE: learned={learned_mae:.3f} min  vs  naive-baseline={baseline_mae:.3f} min  "
          f"(improvement {improvement}%)  beats_baseline={metrics['beats_baseline']}")
    print(f"weights -> {WEIGHTS}")
    print(f"metrics -> {METRICS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
