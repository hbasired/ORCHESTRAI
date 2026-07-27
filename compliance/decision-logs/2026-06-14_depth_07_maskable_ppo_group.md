# ADR — Stage 7 Depth-Hardening: SB3 MaskablePPO beats rules on a group/opportunistic maintenance MDP

**Date**: 2026-06-14
**Status**: Accepted
**Stage**: 7 (depth-hardening increment 3/5 — deepens the closed Stage-7 RL; not a new stage number)
**Author personas**: `ml-engineer` (primary) + `agentic-governance-engineer` (ADR)
**Relates**: deepens `2026-06-12_rl_intervention_ppo.md` (v0 from-scratch PPO; rules near-optimal, PPO did not beat
them). Stages 6–10 depth-hardening pass; research §16.1. Follows CLAUDE.md Hard Rule 11/11a (full depth first).

---

## Context

The v0 Stage-7 RL was an honest negative: a from-scratch PPO on a single-crew SimWorld env where the greedy
priority rule is near-optimal, so PPO did not beat it. The operator's depth mandate (and research §16.1: TranDRL,
predictive *group* maintenance, opportunistic scheduling, action masking) points to the regime where DRL provably
beats greedy rules: scheduling structure a myopic rule can't exploit. The v0 "RL ties rules" was a property of the
*too-simple* env, not a law.

## Decisions

**D1 — Richer maintenance-scheduling MDP with real structure.** New
`backend/training/stage_07_rl_intervention/group_env.py::GroupMaintenanceEnv` (Gymnasium-native): machines in
**zones** (group batching — one crew trip services up to K zone-mates, sharing a fixed setup cost),
**opportunistic** time-varying demand (trips in low-demand windows cost less throughput), crew contention,
heterogeneous crack ETAs. A documented scheduling-MDP model (explicit seeded dynamics + realistic costs) — honest
as a model, not SimWorld telemetry. Verified the structure is real: a batching-aware threshold rule (−137.4) beats
fix-one-at-a-time greedy (−167.6), so grouping genuinely matters.

**D2 — SB3 MaskablePPO with action masking (battle-tested over from-scratch).** `train_sb3.py` uses
**sb3-contrib MaskablePPO**: illegal dispatches (no at-risk machine in a zone, or crew busy) are masked via the
env's `action_masks()`, so the agent never wastes probability on invalid actions. Battle-tested SB3 for credibility
(research §16.1) instead of fragile from-scratch code. 250k timesteps, ~11 min CPU.

**D3 — RL GENUINELY beats the best rule (honest, statistically supported).** CRN-paired eval on 50 held-out seeds
the agent never trained on: **MaskablePPO −125.1 vs the best rule (threshold/batch) −137.4** — paired mean diff
**+12.36, 95% CI [6.0, 18.71]** (lower bound > 0), 36/50 wins; vs greedy +42.51, CI [36.6, 48.4], 48/50. This is the
first RL policy in the project that beats the strongest hand-coded rule with statistical support — the depth payoff.
If it had only tied, that would have been reported honestly; it didn't.

**D4 — Honest glue + the v0 negative preserved.** `backend/ml/group_scheduler_rl.py` loads the SB3 policy
(honest `ModelUnavailableError` if absent). The v0 SimWorld env + from-scratch PPO + the "rules near-optimal in the
simpler regime" finding are RETAINED and not overwritten — both results are true for their respective regimes.

**D5 — Audit holds at 364 (`--no-baseline-drop`), additive.** New RL code lives under `backend/training/` (audit-
exempt) + `backend/ml/group_scheduler_rl.py` (no theatrical patterns); count unchanged confirms zero theatre added.

## Why
- The v0 "RL doesn't beat rules" was honest but a dead end for the INTERVENE leg. The research is explicit that DRL
  beats greedy under group/opportunistic structure — so the honest deep move is to build that regime and let RL show
  its advantage (or not). It did, with statistical support.
- Action masking + SB3 are the credible, standard tools; from-scratch PPO was the v0 shortcut.

## Consequences
- New: `group_env.py`, `train_sb3.py`, `eval_sb3.py`, `ml/group_scheduler_rl.py`, `tests/test_group_scheduler.py`,
  model card, this ADR, explainer. Models: `models/rl_intervention_maskable_ppo.{zip,metrics.json}`. Eval artefacts
  `training/evals/stage07/`.
- 20 Stage-7 tests pass; audit holds 364; no regression to the v0 path.
- G-025 advances: a learned recovery/scheduling policy now beats rules (scheduling-MDP scope); live-loop wiring +
  real plant remain Stage 11/16/17 + G-035.

## Alternatives rejected
1. **Keep the v0 from-scratch PPO / declare "rules win" final.** Rejected — that was the simpler regime's property;
   the research-grounded group/opportunistic regime is where the honest depth lives.
2. **Weaken the rule baseline to make RL "win".** Rejected as dishonest — the threshold/batch rule is a legitimate
   strong baseline; RL beats it on the merits.
3. **Wire the SB3 policy into the live SimWorld loop now.** Deferred — different state space; honest scope is the
   scheduling-MDP demonstration. Live wiring is Stage 11/16.

## References
- `backend/training/stage_07_rl_intervention/{group_env,train_sb3,eval_sb3}.py` · `models/rl_intervention_maskable_ppo.metrics.json`.
- `backend/ml/group_scheduler_rl.py`. Model card `compliance/model-cards/rl_intervention_maskable_ppo.md`.
- Research §16.1. KB: KB_02, KB_23, KB_25.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:29+00:00 -->
<!-- signature: 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 -->
