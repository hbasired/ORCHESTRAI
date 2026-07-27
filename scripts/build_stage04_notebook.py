#!/usr/bin/env python3
"""Generate the Stage-4 predictive-maintenance Colab notebook (valid .ipynb JSON).

Run: python scripts/build_stage04_notebook.py
Output: notebooks/stage04_predictive_maintenance_colab.ipynb

The notebook trains the PREDICT step of the self-healing engine (KB_25 step 1): an
LSTM + attention failure-predictor on a self-contained synthetic degradation dataset
(license-clean), on Colab's free GPU, and exports the 'brain' (torch state_dict +
scaler + metadata + metrics) as a downloadable zip.
"""
import json
import os

def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _src(lines)}

def code(*lines):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _src(lines)}

def _src(lines):
    # one big triple-quoted block per cell -> split keeping newlines
    text = "\n".join(lines)
    parts = text.split("\n")
    return [p + ("\n" if i < len(parts) - 1 else "") for i, p in enumerate(parts)]

cells = []

cells.append(md(
    "# Stage 4 — Predictive Maintenance brain (Colab, free GPU)",
    "",
    "Trains the **PREDICT** step of the Causal Self-Healing Engine (KB_25 step 1): given a rolling window of",
    "machine telemetry, predict **P(failure within the next H steps)**. Dataset is **self-contained synthetic**",
    "(realistic degradation physics, license-clean) — an optional real open-source dataset (AI4I 2020, CC BY 4.0)",
    "cell is included too.",
    "",
    "**How to run:** Runtime ▸ Change runtime type ▸ **GPU (T4)** → Runtime ▸ **Run all**. Last cell downloads",
    "`pdm_brain.zip` — **send that file back**. No API key is needed (training is pure local ML).",
)
)

cells.append(code(
    "import sys, platform, torch",
    "print('python', platform.python_version(), '| torch', torch.__version__)",
    "DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'",
    "print('device:', DEVICE, '|', torch.cuda.get_device_name(0) if DEVICE=='cuda' else 'no GPU (set Runtime->GPU for speed)')",
    "import numpy as np, pandas as pd",
    "import torch.nn as nn",
    "from torch.utils.data import TensorDataset, DataLoader",
    "from sklearn.preprocessing import StandardScaler",
    "from sklearn.metrics import roc_auc_score, average_precision_score, classification_report, roc_curve, precision_recall_curve",
    "import matplotlib.pyplot as plt",
    "SEED = 42",
    "np.random.seed(SEED); torch.manual_seed(SEED)",
    "rng = np.random.default_rng(SEED)",
)
)

cells.append(md(
    "## 1. Synthetic dataset — realistic machine degradation",
    "Each machine emits 5 sensors over time. ~35% develop a stochastic degradation (bearing wear) with a random",
    "onset/rate; sensors (vibration, temperature, current, acoustic, rpm) trend with the hidden degradation +",
    "noise; failure fires when degradation crosses 1.0. This is a genuine, imbalanced time-series problem —",
    "**not** a toy with random labels.",
)
)

cells.append(code(
    "N_MACHINES = 400      # machines",
    "T = 400               # timesteps each",
    "WINDOW = 32           # input window length",
    "HORIZON = 24          # predict failure within the next HORIZON steps",
    "FEATURES = ['vibration','temperature','motor_current','acoustic_db','rpm']",
    "",
    "def gen_machine(mid):",
    "    will_fail = rng.random() < 0.35",
    "    onset = int(rng.integers(80, 320)) if will_fail else T + 10",
    "    rate = rng.uniform(0.004, 0.020)",
    "    deg = 0.0; fail_t = None; rows = []",
    "    base_rpm = rng.uniform(1450, 1550)",
    "    for t in range(T):",
    "        if t >= onset:",
    "            deg += rate * rng.uniform(0.6, 1.4)",
    "        d = min(deg, 1.6)",
    "        vib  = 2.0 + 6.0*d + rng.normal(0, 0.30)",
    "        temp = 45  + 25*d  + rng.normal(0, 1.00)",
    "        cur  = 10  + 4.0*d + rng.normal(0, 0.40)",
    "        ac   = 60  + 15*d  + rng.normal(0, 1.50)",
    "        rpm  = base_rpm - 200*d + rng.normal(0, 15)",
    "        failed = d >= 1.0",
    "        if failed and fail_t is None: fail_t = t",
    "        rows.append([mid, t, vib, temp, cur, ac, rpm, int(failed), fail_t if fail_t is not None else -1])",
    "    return rows",
    "",
    "data = []",
    "for m in range(N_MACHINES):",
    "    data.extend(gen_machine(m))",
    "df = pd.DataFrame(data, columns=['machine','t']+FEATURES+['failed','fail_t'])",
    "print(df.shape, '| machines that fail:', (df.groupby('machine').fail_t.first() >= 0).sum())",
    "df.head()",
)
)

cells.append(md(
    "## 2. Windowing + labels + split + scaling",
    "A window ending at time `t` is **positive** if the machine fails within `[t, t+HORIZON)` and has **not**",
    "failed yet by `t` (we don't train on post-failure windows). Split by machine (no leakage).",
)
)

cells.append(code(
    "def build_windows(df):",
    "    X, y, meta = [], [], []",
    "    for mid, g in df.groupby('machine'):",
    "        g = g.sort_values('t').reset_index(drop=True)",
    "        feats = g[FEATURES].values.astype('float32')",
    "        failed = g['failed'].values",
    "        ft = g['fail_t'].iloc[0]",
    "        for end in range(WINDOW, len(g)):",
    "            if failed[end-1] == 1:",
    "                continue  # already failed -> skip",
    "            label = 1 if (ft >= 0 and end <= ft < end + HORIZON) else 0",
    "            X.append(feats[end-WINDOW:end]); y.append(label); meta.append((mid, end, ft))",
    "    return np.array(X, dtype='float32'), np.array(y, dtype='float32'), meta",
    "",
    "X, y, meta = build_windows(df)",
    "print('windows:', X.shape, '| positive rate:', round(float(y.mean()), 4))",
    "",
    "mids = np.array([m[0] for m in meta])",
    "uniq = np.arange(N_MACHINES); rng.shuffle(uniq)",
    "tr_m, va_m, te_m = uniq[:int(.7*N_MACHINES)], uniq[int(.7*N_MACHINES):int(.85*N_MACHINES)], uniq[int(.85*N_MACHINES):]",
    "def mask(ms): return np.isin(mids, ms)",
    "Xtr, ytr = X[mask(tr_m)], y[mask(tr_m)]",
    "Xva, yva = X[mask(va_m)], y[mask(va_m)]",
    "Xte, yte = X[mask(te_m)], y[mask(te_m)]",
    "",
    "scaler = StandardScaler().fit(Xtr.reshape(-1, len(FEATURES)))",
    "def scale(A): return scaler.transform(A.reshape(-1, len(FEATURES))).reshape(A.shape).astype('float32')",
    "Xtr, Xva, Xte = scale(Xtr), scale(Xva), scale(Xte)",
    "print('train/val/test:', Xtr.shape, Xva.shape, Xte.shape, '| train pos:', int(ytr.sum()))",
)
)

cells.append(md("## 3. Model — LSTM + attention pooling → failure logit"))

cells.append(code(
    "class FailurePredictor(nn.Module):",
    "    def __init__(self, n_features, hidden=64, layers=2, dropout=0.2):",
    "        super().__init__()",
    "        self.lstm = nn.LSTM(n_features, hidden, num_layers=layers, batch_first=True,",
    "                            dropout=dropout if layers > 1 else 0.0, bidirectional=True)",
    "        self.attn = nn.Linear(hidden*2, 1)",
    "        self.head = nn.Sequential(nn.Linear(hidden*2, 64), nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, 1))",
    "    def forward(self, x):",
    "        h, _ = self.lstm(x)                      # (B, T, 2H)",
    "        w = torch.softmax(self.attn(h), dim=1)   # (B, T, 1) attention over time",
    "        ctx = (w * h).sum(dim=1)                 # (B, 2H)",
    "        return self.head(ctx).squeeze(-1)        # (B,) logit",
    "",
    "CFG = dict(n_features=len(FEATURES), hidden=64, layers=2, dropout=0.2,",
    "           window=WINDOW, horizon=HORIZON, features=FEATURES)",
    "model = FailurePredictor(CFG['n_features'], CFG['hidden'], CFG['layers'], CFG['dropout']).to(DEVICE)",
    "print(model)",
)
)

cells.append(md("## 4. Train (GPU) — BCE with pos_weight for class imbalance"))

cells.append(code(
    "def loader(Xa, ya, bs=256, shuffle=False):",
    "    ds = TensorDataset(torch.tensor(Xa), torch.tensor(ya))",
    "    return DataLoader(ds, batch_size=bs, shuffle=shuffle)",
    "tr_dl, va_dl = loader(Xtr, ytr, shuffle=True), loader(Xva, yva)",
    "",
    "pos_weight = torch.tensor([(len(ytr)-ytr.sum())/max(ytr.sum(),1)], device=DEVICE)",
    "crit = nn.BCEWithLogitsLoss(pos_weight=pos_weight)",
    "opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)",
    "",
    "def eval_prauc(dl):",
    "    model.eval(); ps, ts = [], []",
    "    with torch.no_grad():",
    "        for xb, yb in dl:",
    "            ps.append(torch.sigmoid(model(xb.to(DEVICE))).cpu().numpy()); ts.append(yb.numpy())",
    "    p, t = np.concatenate(ps), np.concatenate(ts)",
    "    return average_precision_score(t, p), p, t",
    "",
    "best, best_state, patience, bad = -1, None, 6, 0; hist = []",
    "for epoch in range(40):",
    "    model.train(); tot = 0",
    "    for xb, yb in tr_dl:",
    "        opt.zero_grad()",
    "        loss = crit(model(xb.to(DEVICE)), yb.to(DEVICE)); loss.backward(); opt.step()",
    "        tot += loss.item()*len(xb)",
    "    va_prauc, _, _ = eval_prauc(va_dl); hist.append((tot/len(Xtr), va_prauc))",
    "    print(f'epoch {epoch:02d}  train_loss {tot/len(Xtr):.4f}  val_PR-AUC {va_prauc:.4f}')",
    "    if va_prauc > best: best, best_state, bad = va_prauc, {k: v.cpu().clone() for k,v in model.state_dict().items()}, 0",
    "    else:",
    "        bad += 1",
    "        if bad >= patience: print('early stop'); break",
    "model.load_state_dict(best_state)",
    "plt.plot([h[0] for h in hist], label='train loss'); plt.plot([h[1] for h in hist], label='val PR-AUC'); plt.legend(); plt.title('training'); plt.show()",
)
)

cells.append(md("## 5. Evaluate on the held-out test machines (ROC-AUC, PR-AUC, lead-time)"))

cells.append(code(
    "te_dl = loader(Xte, yte)",
    "_, p_te, t_te = eval_prauc(te_dl)",
    "roc = roc_auc_score(t_te, p_te); prauc = average_precision_score(t_te, p_te)",
    "# choose threshold maximizing F1 on validation",
    "_, p_va, t_va = eval_prauc(va_dl)",
    "prec, rec, thr = precision_recall_curve(t_va, p_va)",
    "f1 = 2*prec*rec/(prec+rec+1e-9); THRESH = float(thr[max(0, f1[:-1].argmax())])",
    "pred = (p_te >= THRESH).astype(int)",
    "print(f'TEST  ROC-AUC {roc:.3f} | PR-AUC {prauc:.3f} | threshold {THRESH:.3f}')",
    "print(classification_report(t_te, pred, digits=3))",
    "",
    "# Lead-time: for failing test machines, how many steps before failure did we FIRST flag?",
    "lead = []",
    "te_meta = [m for m in meta if m[0] in te_m]",
    "flag = {}",
    "for (mid, end, ft), pr in zip(te_meta, p_te):",
    "    if ft >= 0 and pr >= THRESH and mid not in flag and end <= ft:",
    "        flag[mid] = ft - end",
    "lead = list(flag.values())",
    "lead_mean = float(np.mean(lead)) if lead else 0.0",
    "print(f'mean lead-time: {lead_mean:.1f} steps before failure (n={len(lead)} failing machines flagged early)')",
    "",
    "fpr, tpr, _ = roc_curve(t_te, p_te)",
    "fig, ax = plt.subplots(1,2, figsize=(11,4))",
    "ax[0].plot(fpr, tpr); ax[0].plot([0,1],[0,1],'--'); ax[0].set_title(f'ROC (AUC={roc:.3f})'); ax[0].set_xlabel('FPR'); ax[0].set_ylabel('TPR')",
    "ax[1].plot(rec, prec); ax[1].set_title(f'PR (AP={prauc:.3f})'); ax[1].set_xlabel('recall'); ax[1].set_ylabel('precision'); plt.show()",
)
)

cells.append(md(
    "## 6. Export the brain → `pdm_brain.zip` (send this back)",
    "Contains `pdm_failure_predictor.pt` (weights), `scaler.pkl`, `model_meta.json` (architecture), and",
    "`metrics.json`. These let the backend reconstruct + run inference (`predict_failure(window)`).",
)
)

cells.append(code(
    "import pickle, json, zipfile, os",
    "os.makedirs('brain', exist_ok=True)",
    "torch.save(model.state_dict(), 'brain/pdm_failure_predictor.pt')",
    "with open('brain/scaler.pkl','wb') as f: pickle.dump(scaler, f)",
    "meta = {**CFG, 'threshold': THRESH, 'arch': 'BiLSTM+attention', 'seed': SEED,",
    "        'scaler_mean': scaler.mean_.tolist(), 'scaler_scale': scaler.scale_.tolist()}",
    "json.dump(meta, open('brain/model_meta.json','w'), indent=2)",
    "metrics = {'roc_auc': round(float(roc),4), 'pr_auc': round(float(prauc),4),",
    "           'threshold': round(THRESH,4), 'mean_lead_time_steps': round(lead_mean,2),",
    "           'test_positive_rate': round(float(t_te.mean()),4), 'n_test_windows': int(len(t_te)),",
    "           'dataset': 'synthetic-degradation v1', 'window': WINDOW, 'horizon': HORIZON}",
    "json.dump(metrics, open('brain/metrics.json','w'), indent=2)",
    "with zipfile.ZipFile('pdm_brain.zip','w', zipfile.ZIP_DEFLATED) as z:",
    "    for fn in ['pdm_failure_predictor.pt','scaler.pkl','model_meta.json','metrics.json']:",
    "        z.write('brain/'+fn, fn)",
    "print('metrics:', json.dumps(metrics, indent=2))",
    "try:",
    "    from google.colab import files; files.download('pdm_brain.zip')",
    "except Exception as e:",
    "    print('Not in Colab — find pdm_brain.zip in the file browser. (', e, ')')",
)
)

cells.append(md(
    "## (Optional) Real open-source dataset — AI4I 2020 (UCI, CC BY 4.0)",
    "Tabular (not windowed) but real. Swap it in if you prefer real data over synthetic; record the license in",
    "`KB_03_Datasets_Catalog.md`.",
)
)

cells.append(code(
    "# import pandas as pd",
    "# url = 'https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip'",
    "# # download + unzip + load the CSV; target column is 'Machine failure'. License: CC BY 4.0.",
    "# print('See https://archive.ics.uci.edu/dataset/601 for schema + license.')",
)
)

cells.append(md(
    "---",
    "### Model card (fill `compliance/model-cards/pdm_failure_predictor.md`)",
    "- **Model:** BiLSTM + temporal attention → failure-within-horizon classifier.",
    "- **Purpose:** PREDICT step of the self-healing engine (KB_25). Not a certified safety function.",
    "- **Data:** synthetic degradation v1 (this notebook, seed 42) — or AI4I 2020 (CC BY 4.0).",
    "- **Metrics:** see `metrics.json` (ROC-AUC, PR-AUC, lead-time vs the all-healthy baseline).",
    "- **Limits:** trained on synthetic dynamics; must be re-fit on real plant telemetry before any pilot.",
)
)

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "name": "python3"},
                   "language_info": {"name": "python"}, "accelerator": "GPU",
                   "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}

os.makedirs("notebooks", exist_ok=True)
out = "notebooks/stage04_predictive_maintenance_colab.ipynb"
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print(f"wrote {out} ({len(cells)} cells)")
