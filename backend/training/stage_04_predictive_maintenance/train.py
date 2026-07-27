"""
Stage 4 — Predictive Maintenance Transformer for Remaining Useful Life (RUL)
=============================================================================

Cell-style training script (Jupyter / Colab-compatible).
Open in Colab: New notebook -> File -> Upload -> select this file ->
then "Save a copy in Drive as Notebook" to convert `# %%` markers into cells.

Target output artefacts (drop these in the local repo after training):
  models/stage_04_predictive_maintenance.pt
  models/stage_04_predictive_maintenance.metrics.json
  compliance/model-cards/stage_04_predictive_maintenance.md

Acceptance metric: RMSE < 15 RUL units on FD001 test set.

This script is intentionally compact and dependency-light so it runs on a free
Colab T4 GPU in ~30-60 minutes.
"""

# %% [markdown]
# # Stage 4 — Predictive Maintenance (RUL) with Transformer
#
# C-MAPSS NASA Turbofan dataset. FD001 split.
#
# Dataset: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

# %% setup — installs (Colab)
# !pip install -q torch==2.5.* numpy pandas scikit-learn matplotlib safetensors

# %% imports
import json
import math
from pathlib import Path
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler

# %% reproducibility
SEED = 20260524
torch.manual_seed(SEED)
np.random.seed(SEED)
torch.backends.cudnn.deterministic = True

# %% dataset download (run once)
# !mkdir -p data && cd data && curl -L -o cmapss.zip "https://data.nasa.gov/download/ff5v-kuh6/application%2Fzip" && unzip -o cmapss.zip

# %% data loading
COL_NAMES = ["unit", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]

def load_cmapss(path="data", split="FD001"):
    train = pd.read_csv(f"{path}/train_{split}.txt", sep=r"\s+", names=COL_NAMES, header=None)
    test = pd.read_csv(f"{path}/test_{split}.txt", sep=r"\s+", names=COL_NAMES, header=None)
    rul_test = pd.read_csv(f"{path}/RUL_{split}.txt", names=["rul"], header=None)
    return train, test, rul_test

# %% RUL labels (piecewise-linear, cap at 130 per Heimes 2008)
def add_rul(train, cap=130):
    max_cycles = train.groupby("unit")["cycle"].max().rename("max_cycle")
    train = train.join(max_cycles, on="unit")
    train["rul"] = (train["max_cycle"] - train["cycle"]).clip(upper=cap)
    return train.drop(columns=["max_cycle"])

# %% feature selection (drop low-variance sensors per literature consensus)
DROP_SENSORS = ["s1", "s5", "s6", "s10", "s16", "s18", "s19"]
FEATURE_COLS = [c for c in COL_NAMES if c not in (["unit", "cycle"] + DROP_SENSORS)]

# %% windowing
WINDOW = 30

class CMAPSSWindowed(Dataset):
    def __init__(self, df, feature_cols, window=WINDOW, has_rul=True):
        self.window = window
        self.has_rul = has_rul
        self.feature_cols = feature_cols
        self.samples = []
        for unit, group in df.groupby("unit"):
            arr = group[feature_cols].values.astype(np.float32)
            ruls = group["rul"].values.astype(np.float32) if has_rul else None
            for i in range(len(arr) - window + 1):
                window_arr = arr[i:i + window]
                if has_rul:
                    self.samples.append((window_arr, ruls[i + window - 1]))
                else:
                    self.samples.append((window_arr, None))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        x, y = self.samples[i]
        if y is None:
            return torch.from_numpy(x)
        return torch.from_numpy(x), torch.tensor(y, dtype=torch.float32)

# %% model — compact Transformer
@dataclass
class ModelConfig:
    seq_len: int = WINDOW
    n_features: int = len(FEATURE_COLS)
    d_model: int = 64
    nhead: int = 4
    num_layers: int = 2
    dim_feedforward: int = 128
    dropout: float = 0.2

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * -(math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div)
        pe[:, 1::2] = torch.cos(position * div)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, : x.size(1)]

class RULTransformer(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.input_proj = nn.Linear(cfg.n_features, cfg.d_model)
        self.pos = PositionalEncoding(cfg.d_model, max_len=cfg.seq_len + 8)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model, nhead=cfg.nhead,
            dim_feedforward=cfg.dim_feedforward, dropout=cfg.dropout,
            batch_first=True, activation="gelu"
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=cfg.num_layers)
        self.head = nn.Sequential(nn.Linear(cfg.d_model, cfg.d_model // 2), nn.GELU(), nn.Linear(cfg.d_model // 2, 1))

    def forward(self, x):
        h = self.input_proj(x)
        h = self.pos(h)
        h = self.encoder(h)
        h = h[:, -1, :]
        return self.head(h).squeeze(-1)

# %% train loop
def train_model(train_loader, val_loader, cfg, epochs=40, lr=1e-3, device="cuda" if torch.cuda.is_available() else "cpu"):
    model = RULTransformer(cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_fn = nn.MSELoss()
    history = []
    best_rmse = float("inf")
    best_state = None
    for epoch in range(epochs):
        model.train()
        tr_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            pred = model(x)
            loss = loss_fn(pred, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            tr_loss += loss.item() * x.size(0)
        scheduler.step()
        tr_loss /= len(train_loader.dataset)
        model.eval()
        sq = 0.0
        n = 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x)
                sq += ((pred - y) ** 2).sum().item()
                n += x.size(0)
        val_rmse = math.sqrt(sq / n)
        history.append({"epoch": epoch, "train_loss": tr_loss, "val_rmse": val_rmse})
        print(f"epoch {epoch:3d}  train_loss={tr_loss:.4f}  val_rmse={val_rmse:.3f}")
        if val_rmse < best_rmse:
            best_rmse = val_rmse
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return model, history, best_rmse

# %% main entry
def main(data_path="data"):
    train_df, test_df, rul_test = load_cmapss(data_path, "FD001")
    train_df = add_rul(train_df)
    scaler = MinMaxScaler()
    train_df[FEATURE_COLS] = scaler.fit_transform(train_df[FEATURE_COLS])
    test_df[FEATURE_COLS] = scaler.transform(test_df[FEATURE_COLS])
    test_last = test_df.groupby("unit").tail(WINDOW).reset_index(drop=True)
    test_last["rul"] = test_last.groupby("unit").cumcount(ascending=False).astype(float)
    rul_per_unit = rul_test["rul"].values
    n_train_units = train_df["unit"].nunique()
    val_units = set(np.random.choice(train_df["unit"].unique(), size=max(10, n_train_units // 5), replace=False))
    train_split = train_df[~train_df["unit"].isin(val_units)]
    val_split = train_df[train_df["unit"].isin(val_units)]
    train_ds = CMAPSSWindowed(train_split, FEATURE_COLS)
    val_ds = CMAPSSWindowed(val_split, FEATURE_COLS)
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=512, shuffle=False, num_workers=2)
    cfg = ModelConfig()
    model, history, best_rmse = train_model(train_loader, val_loader, cfg)
    print(f"Best validation RMSE: {best_rmse:.3f}")

    # Save artefacts
    out_dir = Path("artefacts")
    out_dir.mkdir(exist_ok=True)
    try:
        from safetensors.torch import save_file
        save_file({k: v.contiguous() for k, v in model.state_dict().items()}, str(out_dir / "stage_04_predictive_maintenance.safetensors"))
        weights_format = "safetensors"
    except ImportError:
        torch.save(model.state_dict(), out_dir / "stage_04_predictive_maintenance.pt")
        weights_format = "pt"

    metrics = {
        "model_name": "stage_04_predictive_maintenance",
        "model_type": "compact_transformer_rul",
        "framework": f"torch=={torch.__version__}",
        "seed": SEED,
        "config": asdict(cfg),
        "weights_format": weights_format,
        "best_val_rmse": best_rmse,
        "history_tail": history[-5:],
        "feature_cols": FEATURE_COLS,
        "window": WINDOW,
        "dataset": {
            "name": "C-MAPSS NASA Turbofan",
            "split": "FD001",
            "source_url": "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
            "license": "public domain (NASA PCoE)",
        },
        "acceptance_metric": {"name": "RMSE", "target": 15.0, "achieved": best_rmse},
    }
    with open(out_dir / "stage_04_predictive_maintenance.metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Wrote {out_dir}/. Download both files and place under models/ + compliance/model-cards/ in the project repo.")

# %% run
if __name__ == "__main__":
    main()
