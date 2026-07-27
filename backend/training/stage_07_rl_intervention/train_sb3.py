"""Stage 7 depth-hardening — train MaskablePPO (sb3-contrib) on the group/opportunistic maintenance env.

Uses the battle-tested Stable-Baselines3 stack (research §16.1) with ACTION MASKING (sb3-contrib MaskablePPO):
illegal dispatches are masked, so the agent only chooses among valid actions. Trains on the richer
`GroupMaintenanceEnv` (group batching + opportunistic demand timing + crew contention) where greedy rules are
provably sub-optimal, then runs an HONEST CRN-paired (common-random-numbers) evaluation vs the rule baselines on
held-out seeds the agent never trained on. The better policy wins on the numbers — not the fancier one.

Writes:
  models/rl_intervention_maskable_ppo.zip   (SB3 MaskablePPO policy)
  models/rl_intervention_maskable_ppo.metrics.json  (hyperparams + CRN-paired RL-vs-rules result + verdict)

Usage (from backend/):
    python training/stage_07_rl_intervention/train_sb3.py --timesteps 150000
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.stage_07_rl_intervention.group_env import (  # noqa: E402
    GroupMaintenanceEnv, GroupEnvConfig, greedy_urgent_action, threshold_action,
)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
WEIGHTS = MODELS_DIR / "rl_intervention_maskable_ppo.zip"
METRICS = MODELS_DIR / "rl_intervention_maskable_ppo.metrics.json"

TRAIN_SEEDS = list(range(0, 64))      # episodes sample from here during training
EVAL_SEEDS = list(range(100, 150))    # held-out — never trained on


def _make_env(seed: int):
    from sb3_contrib.common.wrappers import ActionMasker
    env = GroupMaintenanceEnv(GroupEnvConfig(seed=seed))
    return ActionMasker(env, lambda e: e.action_masks())


def _rollout(policy_fn, seeds) -> np.ndarray:
    """Run a policy on each seed (CRN: same seed → same crack campaign + demand). Returns per-seed returns."""
    rets = []
    for s in seeds:
        env = GroupMaintenanceEnv(GroupEnvConfig(seed=s))
        obs, _ = env.reset(seed=s)
        R, done = 0.0, False
        while not done:
            a = policy_fn(env, obs)
            obs, r, term, trunc, _ = env.step(a)
            R += r
            done = term or trunc
        rets.append(R)
    return np.asarray(rets, dtype=np.float64)


def _paired_ci(a: np.ndarray, b: np.ndarray) -> dict:
    """95% CI on the paired difference a-b (CRN). Positive ⇒ a beats b."""
    d = a - b
    mean = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0
    return {"mean_diff": round(mean, 2), "ci95": [round(mean - 1.96 * se, 2), round(mean + 1.96 * se, 2)],
            "wins": int((d > 0).sum()), "n": int(len(d))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timesteps", type=int, default=150000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.monitor import Monitor
    import torch
    torch.manual_seed(args.seed); np.random.seed(args.seed)

    t0 = time.time()
    # Training env cycles through TRAIN_SEEDS by re-seeding on reset.
    base = GroupMaintenanceEnv(GroupEnvConfig(seed=args.seed))
    from sb3_contrib.common.wrappers import ActionMasker

    class _SeedCycler(GroupMaintenanceEnv):
        """Re-seed each episode from TRAIN_SEEDS for campaign diversity (held-out EVAL_SEEDS stay unseen)."""
        def reset(self, *, seed=None, options=None):
            s = int(TRAIN_SEEDS[np.random.randint(len(TRAIN_SEEDS))])
            return super().reset(seed=s, options=options)

    env = Monitor(ActionMasker(_SeedCycler(GroupEnvConfig(seed=args.seed)), lambda e: e.action_masks()))
    model = MaskablePPO("MlpPolicy", env, seed=args.seed, verbose=0,
                        n_steps=2048, batch_size=256, gae_lambda=0.95, gamma=0.99,
                        learning_rate=3e-4, ent_coef=0.01, n_epochs=10,
                        policy_kwargs={"net_arch": [128, 128]})
    model.learn(total_timesteps=args.timesteps)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(WEIGHTS.with_suffix("")))  # SB3 appends .zip

    # ---- honest CRN-paired eval on held-out seeds ----
    from sb3_contrib.common.maskable.utils import get_action_masks

    def rl_policy(e, obs):
        masks = e.action_masks()
        a, _ = model.predict(obs, action_masks=masks, deterministic=True)
        return int(a)

    rl = _rollout(rl_policy, EVAL_SEEDS)
    greedy = _rollout(lambda e, o: greedy_urgent_action(e), EVAL_SEEDS)
    thresh = _rollout(lambda e, o: threshold_action(e), EVAL_SEEDS)
    noop = _rollout(lambda e, o: 0, EVAL_SEEDS)

    vs_greedy = _paired_ci(rl, greedy)
    vs_thresh = _paired_ci(rl, thresh)
    best_rule = "threshold_batch" if thresh.mean() >= greedy.mean() else "greedy_urgent"
    best_rule_mean = max(thresh.mean(), greedy.mean())
    beats_best_rule = bool(rl.mean() > best_rule_mean and (vs_thresh["ci95"][0] > 0 if best_rule == "threshold_batch" else vs_greedy["ci95"][0] > 0))

    metrics = {
        "model": "rl_intervention_maskable_ppo", "stage": 7,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "framework": "Stable-Baselines3 sb3-contrib MaskablePPO (action masking); Gymnasium env",
        "env": "GroupMaintenanceEnv (group batching + opportunistic demand timing + crew contention)",
        "hyperparameters": {"timesteps": args.timesteps, "n_steps": 2048, "batch_size": 256,
                            "lr": 3e-4, "gamma": 0.99, "gae_lambda": 0.95, "ent_coef": 0.01,
                            "n_epochs": 10, "net_arch": [128, 128], "seed": args.seed},
        "train_seconds": round(time.time() - t0, 1),
        "eval_seeds": [EVAL_SEEDS[0], EVAL_SEEDS[-1]], "n_eval": len(EVAL_SEEDS),
        "return_means": {"maskable_ppo": round(float(rl.mean()), 2),
                         "threshold_batch_rule": round(float(thresh.mean()), 2),
                         "greedy_urgent_rule": round(float(greedy.mean()), 2),
                         "no_op": round(float(noop.mean()), 2)},
        "paired_vs_greedy": vs_greedy, "paired_vs_threshold": vs_thresh,
        "best_rule": best_rule, "best_rule_mean": round(float(best_rule_mean), 2),
        "rl_beats_best_rule": beats_best_rule,
        "honest_note": ("CRN-paired (common-random-numbers) on held-out seeds the agent never trained on. "
                        "Positive mean_diff with ci95 lower bound > 0 ⇒ a genuine, statistically-supported win. "
                        "If RL only ties the best rule, that is reported honestly — the better policy wins, not the "
                        "fancier one. Scheduling-MDP model (documented), not SimWorld telemetry."),
        "license": "Apache-2.0 (project); SB3/sb3-contrib MIT",
        "reproduce": "python training/stage_07_rl_intervention/train_sb3.py --timesteps 150000",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"\ntrained {args.timesteps} steps in {metrics['train_seconds']}s")
    print(f"RETURNS (held-out, CRN): MaskablePPO={rl.mean():.1f}  threshold_batch={thresh.mean():.1f}  "
          f"greedy={greedy.mean():.1f}  no-op={noop.mean():.1f}")
    print(f"vs best rule ({best_rule} {best_rule_mean:.1f}): RL_beats_best_rule={beats_best_rule}")
    print(f"  paired vs threshold: {vs_thresh}")
    print(f"  paired vs greedy:    {vs_greedy}")
    print(f"weights -> {WEIGHTS}\nmetrics -> {METRICS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
