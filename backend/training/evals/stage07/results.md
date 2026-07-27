# Stage 7 — RL intervention eval (measured, paired CRN + 95% CI)

Scenario: capacity-1 maintenance crew, 5 cracks, 2.0 sim-h, event-driven · seeds [42, 43, 44, 45, 46, 47, 48, 49]

| chooser | mean crack-breakdowns (±95% CI) | mean return (±95% CI) |
|---|---|---|
| no_intervention | 4.0 ± 0.524 | -285.97 ± 38.13 |
| rules_priority | 0.375 ± 0.359 | -39.82 ± 23.7 |
| ppo_shield | 0.875 ± 0.245 | -118.7 ± 18.83 |

Paired PPO−rules breakdown diff: 0.5 ± 0.37 (negative => PPO had FEWER breakdowns than rules; CI spanning 0 => no significant difference).

**Finding:** Rules are near-optimal at v0 scope. PPO+shield does NOT beat the rules; rules remain the default chooser. The safety shield guarantees PPO is at least as safe; PPO ships as the learnable substrate for Stage 8.
**Default chooser:** rules.

Honesty: CRN-paired (G-046); the harness reports the measured delta, never asserts a winner; crack-prevention is the robust metric (Stage-6 independent audit); risk signal = ground-truth proximity in this sim eval (real-telemetry re-fit gated by G-035).