"""Stage 7 depth-hardening — independent re-eval of the MaskablePPO scheduler vs rule baselines.

Loads the saved SB3 MaskablePPO policy and re-runs the CRN-paired comparison on held-out seeds, so an auditor
can reproduce the RL-vs-rules verdict without trusting the trainer's own printout.

Usage (from backend/):
    python training/stage_07_rl_intervention/eval_sb3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_07_rl_intervention.group_env import (  # noqa: E402
    GroupMaintenanceEnv, GroupEnvConfig, greedy_urgent_action, threshold_action,
)
from training.stage_07_rl_intervention.train_sb3 import _rollout, _paired_ci, EVAL_SEEDS, WEIGHTS  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parents[2] / "training" / "evals" / "stage07"


def main() -> int:
    if not WEIGHTS.exists():
        print(f"REFUSE: trained MaskablePPO not found ({WEIGHTS}); run train_sb3.py. No fabricated eval.")
        return 2
    from sb3_contrib import MaskablePPO
    model = MaskablePPO.load(str(WEIGHTS.with_suffix("")))

    def rl_policy(e, obs):
        a, _ = model.predict(obs, action_masks=e.action_masks(), deterministic=True)
        return int(a)

    rl = _rollout(rl_policy, EVAL_SEEDS)
    greedy = _rollout(lambda e, o: greedy_urgent_action(e), EVAL_SEEDS)
    thresh = _rollout(lambda e, o: threshold_action(e), EVAL_SEEDS)
    best_rule_mean = max(thresh.mean(), greedy.mean())
    best_rule = "threshold_batch" if thresh.mean() >= greedy.mean() else "greedy_urgent"
    vs = _paired_ci(rl, thresh if best_rule == "threshold_batch" else greedy)

    summary = {
        "n_eval": len(EVAL_SEEDS),
        "return_means": {"maskable_ppo": round(float(rl.mean()), 2),
                         "threshold_batch": round(float(thresh.mean()), 2),
                         "greedy_urgent": round(float(greedy.mean()), 2)},
        "best_rule": best_rule, "best_rule_mean": round(float(best_rule_mean), 2),
        "paired_vs_best_rule": vs,
        "rl_beats_best_rule": bool(rl.mean() > best_rule_mean and vs["ci95"][0] > 0),
        "note": "CRN-paired on held-out seeds; positive ci95 lower bound ⇒ genuine win. Scheduling-MDP model.",
    }
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "sb3_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"RETURNS (held-out, CRN): MaskablePPO={rl.mean():.1f}  {best_rule}={best_rule_mean:.1f}")
    print(f"paired vs best rule: {vs}  rl_beats_best_rule={summary['rl_beats_best_rule']}")
    print(f"report -> {EVAL_DIR/'sb3_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
