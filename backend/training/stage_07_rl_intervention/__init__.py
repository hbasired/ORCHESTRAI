"""Stage 7 — RL intervention policy (PPO) training package.

Contents:
- env.py    : InterventionEnv — headless, seeded SimWorld wrapper with a
              maintenance-crew capacity constraint (the regime where greedy
              rules are sub-optimal and RL can earn its place).
- ppo.py    : compact, auditable from-scratch PPO (discrete, GAE, clipped).
- train.py  : trains -> models/rl_intervention_policy.{pt,metrics.json}.
- eval.py   : honest 3-way paired-seed eval (none / rules / PPO+shield) + CIs.

Free-cost: uses only the already-pinned torch (CPU) + numpy + the simulator.
No stable-baselines3, no gymnasium, no paid services.
"""
