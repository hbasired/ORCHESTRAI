"""Stage 8 depth-hardening — independent re-eval of the C-MAPSS RUL Transformer.

Re-evaluates the trained model on the OFFICIAL FD001 test set through the honest inference glue
(`ml.rul_transformer`), so an auditor can reproduce the headline RMSE / NASA-score without trusting
the trainer's own printout. Reports vs the naive baseline + the cited literature range.

Usage (from backend/):
    python training/stage_08_world_model/eval_cmapss.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_08_world_model.cmapss_data import (  # noqa: E402
    CmapssConfig, DatasetUnavailableError, load_fd001, nasa_score,
)

EVAL_DIR = Path(__file__).resolve().parents[2] / "training" / "evals" / "stage08"


def _rmse(a, b) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def main() -> int:
    from ml.rul_transformer import RULTransformer
    m = RULTransformer()
    if not m.is_available():
        print("REFUSE: trained RUL transformer unavailable (run train_cmapss.py); no fabricated eval.")
        return 2
    try:
        d = load_fd001(CmapssConfig(window=30))
    except DatasetUnavailableError as e:
        print(f"REFUSE: {e}")
        return 2

    # Reconstruct raw (un-normalised) last windows and predict through the public glue.
    span = (d["feat_max"] - d["feat_min"])
    preds = []
    for i in range(len(d["Xte"])):
        raw = d["Xte"][i] * span + d["feat_min"]
        preds.append(m.predict_rul(raw)["rul_cycles"])
    preds = np.asarray(preds, dtype=np.float64)
    yte = d["yte"].astype(np.float64)

    test_rmse = _rmse(preds, yte)
    test_score = nasa_score(preds, yte)
    base = float(np.mean(yte))  # generous baseline = test mean
    base_rmse = _rmse(np.full_like(yte, base), yte)

    summary = {
        "dataset": "C-MAPSS FD001 (official 100 test engines)", "n_test_engines": int(len(yte)),
        "test_rmse": round(test_rmse, 3), "test_nasa_score": round(test_score, 1),
        "baseline_test_rmse": round(base_rmse, 3),
        "improvement_vs_baseline_pct": round(100.0 * (base_rmse - test_rmse) / base_rmse, 1),
        "beats_baseline": bool(test_rmse < base_rmse),
        "literature_fd001_rmse_cited": {"CNN(2016)": 18.45, "LSTM(2017)": 16.14, "DCNN(2018)": 12.61,
                                        "Transformer(2021)": 11.27},
        "note": "Re-eval through the public inference glue; real public benchmark; proxy-free numbers. G-035 for real fleet.",
    }
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "cmapss_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (EVAL_DIR / "cmapss_results.md").write_text(
        "# Stage 8 — C-MAPSS FD001 RUL Transformer (independent re-eval)\n\n"
        f"100 official test engines.\n\n| metric | value |\n|---|---|\n"
        f"| test RMSE | {summary['test_rmse']} |\n"
        f"| NASA score | {summary['test_nasa_score']} |\n"
        f"| naive baseline RMSE | {summary['baseline_test_rmse']} |\n"
        f"| improvement | {summary['improvement_vs_baseline_pct']}% |\n\n"
        "Cited FD001 literature RMSE: CNN 18.45 / LSTM 16.14 / DCNN 12.61 / Transformer 11.27 "
        "(not reproduced here). Real public benchmark; real-fleet generalisation is G-035.\n",
        encoding="utf-8")
    print(f"FD001 TEST  RMSE={test_rmse:.3f}  NASA-score={test_score:.1f}  "
          f"(baseline RMSE={base_rmse:.3f}, improvement {summary['improvement_vs_baseline_pct']}%)")
    print(f"reports -> {EVAL_DIR/'cmapss_results.json'} , {EVAL_DIR/'cmapss_results.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
