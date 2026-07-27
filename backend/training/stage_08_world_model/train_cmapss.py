"""Stage 8 depth-hardening — train the Transformer RUL model on real C-MAPSS FD001.

Protocol (standard, leakage-free):
  - engine-level split: first 85 train engines → train, last 15 → validation (for early-stopping /
    best-checkpoint selection only; NO peeking at test),
  - report final RMSE + asymmetric NASA score on the OFFICIAL 100 FD001 test engines (single eval),
  - compare to the naive mean-RUL baseline; cite the published SOTA range in the metrics (not reproduced).

Writes:
  models/rul_transformer_cmapss.pt            (state_dict + arch + scaler + window/sensor meta)
  models/rul_transformer_cmapss.metrics.json  (seed, hyperparams, val curve, test RMSE/score vs baseline)

Usage (from backend/):
    python training/stage_08_world_model/train_cmapss.py            # defaults
    python training/stage_08_world_model/train_cmapss.py --epochs 40 --batch 512
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_08_world_model.cmapss_data import (  # noqa: E402
    CmapssConfig, DatasetUnavailableError, load_fd001, nasa_score, N_FEATURES,
)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
WEIGHTS = MODELS_DIR / "rul_transformer_cmapss.pt"
METRICS = MODELS_DIR / "rul_transformer_cmapss.metrics.json"

# Published FD001 test-set results (RMSE), cited for context — NOT reproduced here. Provenance in the
# model card / research log. Used only to frame "how close to SOTA is our honest number".
_LITERATURE = {
    "CNN (Babu 2016)": 18.45,
    "LSTM (Zheng 2017)": 16.14,
    "DCNN (Li 2018)": 12.61,
    "AGCNN (Liu 2020)": 12.42,
    "Transformer (Mo 2021)": 11.27,
}


def _rmse(pred, true) -> float:
    return float(np.sqrt(np.mean((np.asarray(pred) - np.asarray(true)) ** 2)))


def main() -> int:
    import torch
    import torch.nn as nn

    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--d_model", type=int, default=64)
    ap.add_argument("--nhead", type=int, default=4)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--ff", type=int, default=128)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=8)
    ap.add_argument("--val_engines", type=int, default=15)
    args = ap.parse_args()

    torch.manual_seed(args.seed); np.random.seed(args.seed)

    t0 = time.time()
    try:
        data = load_fd001(CmapssConfig(window=args.window))
    except DatasetUnavailableError as e:
        print(f"REFUSE: {e}")
        return 2

    Xtr_all, ytr_all = data["Xtr"], data["ytr"]
    Xte, yte = data["Xte"], data["yte"]

    # Engine-level val split is approximated here at the window level by holding out the windows that
    # belong to the last `val_engines` engines. cmapss_data emits windows grouped by engine in unit
    # order, so a tail fraction ≈ the last engines. Use a clean fraction for monitoring only.
    n = len(Xtr_all)
    val_frac = args.val_engines / float(data["n_train_engines"])
    cut = int(n * (1.0 - val_frac))
    Xtr, ytr = Xtr_all[:cut], ytr_all[:cut]
    Xva, yva = Xtr_all[cut:], ytr_all[cut:]

    from ml.rul_transformer import build_rul_transformer
    net = build_rul_transformer(N_FEATURES, args.window, d_model=args.d_model, nhead=args.nhead,
                                num_layers=args.layers, dim_feedforward=args.ff, dropout=args.dropout)
    opt = torch.optim.Adam(net.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    lossf = nn.MSELoss()  # MSE learns the RUL scale fast (Huber/L1 crawls); standard for C-MAPSS RUL

    # Warm-start the head bias at the mean train RUL so the net starts near the target scale.
    with torch.no_grad():
        net.head[-1].bias.fill_(float(ytr.mean()))

    Xt = torch.as_tensor(Xtr); yt = torch.as_tensor(ytr)
    Xv = torch.as_tensor(Xva)
    Xtest = torch.as_tensor(Xte)

    bs = args.batch; ntr = len(Xt); curve = []
    best_val = float("inf"); best_state = None
    for ep in range(args.epochs):
        net.train(); idx = torch.randperm(ntr)
        for s in range(0, ntr, bs):
            mb = idx[s:s + bs]
            opt.zero_grad()
            loss = lossf(net(Xt[mb]), yt[mb])
            loss.backward(); opt.step()
        sched.step()
        net.eval()
        with torch.no_grad():
            vrmse = _rmse(net(Xv).numpy(), yva)
        if vrmse < best_val:
            best_val = vrmse
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        if (ep + 1) % 5 == 0 or ep == 0:
            curve.append({"epoch": ep + 1, "val_rmse": round(vrmse, 3)})
            print(f"  epoch {ep+1:3d}/{args.epochs}  val_rmse={vrmse:.3f}  (best {best_val:.3f})")

    # Restore best-val checkpoint, then a SINGLE evaluation on the official test set.
    if best_state is not None:
        net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        test_pred = net(Xtest).numpy()
    test_rmse = _rmse(test_pred, yte)
    test_score = nasa_score(test_pred, yte)
    base_pred = float(ytr_all.mean())
    base_rmse = _rmse(np.full_like(yte, base_pred), yte)
    base_score = nasa_score(np.full_like(yte, base_pred), yte)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": net.state_dict(), "n_features": N_FEATURES, "window": args.window,
        "d_model": args.d_model, "nhead": args.nhead, "num_layers": args.layers,
        "dim_feedforward": args.ff, "dropout": args.dropout,
        "sensors": data["sensors"], "feat_min": data["feat_min"].tolist(),
        "feat_max": data["feat_max"].tolist(), "rul_cap": data["rul_cap"],
    }, WEIGHTS)

    metrics = {
        "model": "rul_transformer_cmapss", "stage": 8,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": "remaining-useful-life (cycles) on C-MAPSS FD001 (KB_25 step 1 — PREDICT, deepened)",
        "framework": "torch CPU Transformer encoder (self-attention over a 30-cycle, 14-sensor window)",
        "dataset": "NASA C-MAPSS FD001 (Saxena & Goebel 2008); 100 train / 100 test engines; real benchmark",
        "data_provenance": "downloaded from public mirrors (recorded), unmodified; cached under data/datasets/cmapss/",
        "mirrors": data["mirrors"],
        "preprocessing": {"sensors": data["sensors"], "window": args.window, "rul_cap": data["rul_cap"],
                          "normalisation": "per-sensor min-max fit on train only", "n_train_windows": int(n)},
        "hyperparameters": {"d_model": args.d_model, "nhead": args.nhead, "num_layers": args.layers,
                            "dim_feedforward": args.ff, "dropout": args.dropout, "lr": args.lr,
                            "epochs": args.epochs, "batch_size": bs, "seed": args.seed,
                            "scheduler": "cosine", "loss": "MSE", "head_bias_warmstart": "mean train RUL"},
        "n_train_windows": int(len(Xtr)), "n_val_windows": int(len(Xva)), "n_test_engines": int(len(yte)),
        "val_curve": curve, "best_val_rmse": round(best_val, 3),
        "test_rmse": round(test_rmse, 3), "test_nasa_score": round(test_score, 1),
        "naive_baseline_test_rmse": round(base_rmse, 3), "naive_baseline_nasa_score": round(base_score, 1),
        "improvement_vs_baseline_pct": round(100.0 * (base_rmse - test_rmse) / base_rmse, 1),
        "beats_baseline": bool(test_rmse < base_rmse),
        "literature_fd001_test_rmse_cited_not_reproduced": _LITERATURE,
        "honest_note": ("real public benchmark; RMSE/score computed once on the official 100 test engines "
                        "after best-val model selection (no test peeking). Published SOTA on FD001 is ~11-13 RMSE "
                        "(cited, not reproduced); our number is reported as-measured. Generalisation to a real "
                        "fleet still requires re-fit on real telemetry (G-035)."),
        "license": "Apache-2.0 (project code); dataset is NASA public-domain",
        "reproduce": "python training/stage_08_world_model/train_cmapss.py --epochs 40 --batch 512",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    dt = round(time.time() - t0, 1)
    print(f"\ntrained in {dt}s  n_train_windows={len(Xtr)} n_val_windows={len(Xva)}")
    print(f"FD001 TEST  RMSE={test_rmse:.3f}  NASA-score={test_score:.1f}  "
          f"(best_val_rmse={best_val:.3f})")
    print(f"naive baseline  RMSE={base_rmse:.3f}  score={base_score:.1f}  "
          f"-> improvement {metrics['improvement_vs_baseline_pct']}%  beats_baseline={metrics['beats_baseline']}")
    print(f"literature FD001 RMSE (cited): {_LITERATURE}")
    print(f"weights -> {WEIGHTS}\nmetrics -> {METRICS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
