"""Stage 8 — held-out TTF eval on fresh seeds (TTF MAE vs naive mean-TTF baseline).

Independent re-evaluation entry point (the auditor can run it on seeds the trainer never used) to confirm the
world model's win is not seed-specific. Loads the trained net via the honest inference glue.

Usage (from backend/):
    python training/stage_08_world_model/eval.py --seeds 60,61,62,63,64
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_08_world_model.rollouts import RolloutConfig, build_dataset  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parents[2] / "training" / "evals" / "stage08"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=str, default="60,61,62,63,64")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]

    from ml.world_model import WorldModel, ModelUnavailableError
    wm = WorldModel()
    if not wm.is_available():
        print("REFUSE: trained world model unavailable (run train.py); no fabricated eval.")
        return 2

    X, y = build_dataset(seeds, RolloutConfig())
    if len(X) == 0:
        print("REFUSE: empty eval dataset"); return 2

    preds = np.array([wm.predict_ttf(w)["ttf_minutes"] for w in X], dtype=np.float32)
    learned_mae = float(np.mean(np.abs(preds - y)))
    # Naive baseline on THIS held-out set = its own mean (a generous baseline).
    baseline_mae = float(np.mean(np.abs(y - y.mean())))
    improvement = round(100.0 * (baseline_mae - learned_mae) / baseline_mae, 1)

    summary = {
        "seeds": seeds, "n": int(len(X)),
        "ttf_range_minutes": [round(float(y.min()), 2), round(float(y.max()), 2)],
        "learned_val_mae_min": round(learned_mae, 3),
        "naive_baseline_mae_min": round(baseline_mae, 3),
        "improvement_vs_baseline_pct": improvement,
        "beats_baseline": bool(learned_mae < baseline_mae),
        "note": "Fresh-seed held-out eval; baseline = mean-TTF predictor. Proxy/sim only (G-035).",
    }
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (EVAL_DIR / "results.md").write_text(
        "# Stage 8 — TTF world-model held-out eval\n\n"
        f"Seeds {seeds} · n={len(X)} · TTF range {summary['ttf_range_minutes']} min\n\n"
        f"| metric | value |\n|---|---|\n"
        f"| learned TTF MAE (min) | {summary['learned_val_mae_min']} |\n"
        f"| naive baseline MAE (min) | {summary['naive_baseline_mae_min']} |\n"
        f"| improvement | {improvement}% |\n\n"
        "Honesty: fresh seeds the trainer never used; baseline = mean-TTF; proxy/sim only (G-035).\n",
        encoding="utf-8")
    print(f"seeds={seeds} n={len(X)}")
    print(f"TTF MAE: learned={learned_mae:.3f} min  vs naive={baseline_mae:.3f} min  "
          f"(improvement {improvement}%)  beats_baseline={summary['beats_baseline']}")
    print(f"reports -> {EVAL_DIR/'results.json'} , {EVAL_DIR/'results.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
