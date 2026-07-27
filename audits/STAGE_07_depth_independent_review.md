# Independent Review — Stage 7 Depth-Hardening (SB3 MaskablePPO beats rules)

**Auditor**: independent `task-auditor` (did NOT implement this increment).
**Date**: 2026-06-14.
**Scope**: the 2026-06-14 Stage-7 depth increment — sb3-contrib MaskablePPO on a group/opportunistic maintenance MDP.
**ADR reviewed**: `compliance/decision-logs/2026-06-14_depth_07_maskable_ppo_group.md`.

## VERDICT: PASS

Claim — MaskablePPO **genuinely beats the best hand-coded rule** (CRN-paired held-out **−125.1 vs −137.4, 95% CI
[6.0, 18.71]**, 36/50 wins) — is supported by the committed code, metrics, and on-disk policy. The rule baselines are
**legitimate strong baselines, NOT weakened**; train/eval seeds are **disjoint**; the env is an **honest documented
model**, not fabricated telemetry; and the **v0 from-scratch PPO + its honest "rules tie" negative are RETAINED**.
Execution caveat below: I could not re-run `eval_sb3.py` (harness blocked Python execution), so I could not
personally reproduce the −125.1/−137.4 numbers; verdict rests on static analysis + committed artifacts + audit.

## Execution caveat (transparency)

`python ...eval_sb3.py` and `python -m pytest` were **denied by the harness permission layer** this session (Python
execution blocked; only `git`/`ls`/`scripts/audit.sh` permitted). I could NOT independently reproduce the eval
numbers or re-run `tests/test_group_scheduler.py` / `tests/test_intervention_rl.py`. The on-disk policy
(`models/rl_intervention_maskable_ppo.zip`, 528 KB) and `eval_sb3.py` are present, so the reproduction IS runnable
locally — I simply could not execute it here. Everything below is from reading source + committed metrics. I DID run
`scripts/audit.sh`: **TOTAL = 364 = baseline**.

## CRITICAL CHECK 1 — are the rule baselines legitimate, or weakened to manufacture a win?

**Legitimate. Confirmed by reading the rules (group_env.py:166-192).**

- `threshold_action` (the BEST rule, −137.4) is a genuinely smart **batching-aware** heuristic: it counts at-risk
  machines per zone under an ETA threshold and dispatches to the zone with the **most** urgent machines
  (`np.argmax(counts)`, line 192) — i.e. it explicitly exploits the GROUP structure. It also **defers** non-urgent
  fixes unless something is very close (lines 184-190) — i.e. it exploits the OPPORTUNISTIC structure too. This is
  precisely the strong rule a thoughtful engineer would write; it is NOT a strawman.
- `greedy_urgent_action` (−167.6) dispatches to the single most-urgent machine's zone — the standard myopic baseline.
- The env genuinely rewards batching: the test `test_batching_rule_beats_greedy_on_average`
  (test_group_scheduler.py:48-60, on seeds 200-220, disjoint from train/eval) asserts threshold > greedy, and the
  ADR/metrics confirm −137.4 > −167.6. So the structure is real and the strong rule already captures most of it —
  the RL win of +12.36 over `threshold` is **on the merits over a strong baseline**, not over a crippled one.
- ADR Alternative #2 explicitly rejects weakening the baseline as dishonest; the code matches that stance.

## CRITICAL CHECK 2 — train/eval seed disjointness (no eval-on-train)

**Disjoint. Confirmed.**
- `train_sb3.py:36-37`: `TRAIN_SEEDS = range(0,64)`, `EVAL_SEEDS = range(100,150)` — disjoint.
- The training env (`_SeedCycler`, train_sb3.py:87-91) re-seeds **only from TRAIN_SEEDS** each episode; EVAL_SEEDS
  are never touched in training. The eval (`_rollout`, lines 46-59) uses CRN: same seed → same crack campaign +
  demand profile for every policy, enabling a fair paired comparison. The agent predicts `deterministic=True` with
  action masks at eval. Sound.

## CRITICAL CHECK 3 — honest model, not fabricated telemetry

`GroupMaintenanceEnv` (group_env.py:61-163) is a Gymnasium-native MDP with **explicit seeded dynamics + realistic
cost parameters** (trip setup cost, per-machine cost, breakdown penalty, demand oscillation). It is a documented
MODEL of the maintenance decision — the module docstring and ADR/model-card are explicit that it is NOT SimWorld
telemetry. The `random.uniform`/`rng.random` calls are legitimate stochastic env dynamics (crack arrivals, ETAs),
which live under `backend/training/` (audit-exempt) — not theatrical fallbacks in serving code. Action masking is
real (`action_masks()`, lines 110-121): no-op always legal; a zone legal iff crew free AND a zone-mate is at-risk.

## CRITICAL CHECK 4 — v0 retained, not overwritten

**Retained. Confirmed.**
- v0 files all present: `env.py`, `train.py`, `ppo.py`, `eval.py`, `config.yaml`, plus weights
  `models/rl_intervention_policy.{pt,metrics.json}` and model card `rl_intervention_policy.md`.
- The v0 honest negative is intact in `training/evals/stage07/results.json`:
  `"ppo_beats_rules_on_crack_prevention": false`, `"default_chooser": "rules"`, `"Rules are near-optimal at v0
  scope. PPO+shield does NOT beat the rules"`. Not overwritten.
- `tests/test_intervention_rl.py` still tests the v0 env, from-scratch PPO (bandit learning test), safety shield, and
  `DEFAULT_CHOOSER == "rules"`. The new MaskablePPO lives alongside via a separate inference glue
  (`ml/group_scheduler_rl.py`) and separate tests (`test_group_scheduler.py`).

## metrics.json honesty

`models/rl_intervention_maskable_ppo.metrics.json` — read in full. `return_means`: maskable_ppo −125.06,
threshold −137.42, greedy −167.58, no-op −828.89. `paired_vs_threshold`: mean_diff +12.36, ci95 [6.0, 18.71], wins
36/50. `paired_vs_greedy`: +42.51, [36.64, 48.39], 48/50. `rl_beats_best_rule: true`. These exactly match the ADR
and model card. The `_paired_ci` math (train_sb3.py:62-68) is a correct paired-difference 95% CI (mean ± 1.96·SE).
`beats_best_rule` requires both a higher mean AND the CI lower bound > 0 (train_sb3.py:119) — a sound, honest gate.

## Discrepancies found (non-blocking)

1. **timesteps doc mismatch (cosmetic):** metrics.json `hyperparameters.timesteps = 250000` and the model card says
   250k/~11 min, but the `reproduce` string in metrics.json and the train_sb3.py argparse default both say `150000`.
   The ADR (D2) says 250k. So the **actual run used 250k** (recorded), but the reproduce hint under-specifies it.
   Cosmetic; running with `--timesteps 250000` reproduces. Worth a one-line fix to the reproduce string but not a
   close-blocker.
2. **Unused import**: `from sb3_contrib.common.maskable.utils import get_action_masks` (train_sb3.py:103) is imported
   but not used. Harmless lint nit.

## Mechanical audit

`bash scripts/audit.sh` → **TOTAL 364 = baseline**. New serving code `ml/group_scheduler_rl.py` has no theatrical
patterns (honest-unavailable via `ModelUnavailableError`, no random/mock). Env stochasticity is under `training/`.
Zero new theatre.

## Independent confirmation table

| Claim | Confirmed? | Basis |
|---|---|---|
| Rules are LEGITIMATE strong baselines (not weakened) | YES | threshold_action is batching+opportunistic-aware (group_env.py:179-192) |
| Train/eval seeds disjoint, eval held-out | YES | TRAIN 0-63 vs EVAL 100-149; _SeedCycler only uses TRAIN |
| Env is honest documented model, not telemetry | YES | seeded MDP with explicit costs; docstring/ADR explicit |
| RL beats best rule −125.1 vs −137.4, CI [6.0,18.71], lb>0 | YES (artifact) | metrics.json; honest beats-gate (mean>rule AND ci_lb>0) |
| v0 from-scratch PPO + "rules tie" negative retained | YES | env.py/ppo.py/results.json/test_intervention_rl.py all present |
| audit holds 364, zero new theatre | YES (I ran audit.sh) | TOTAL 364; serving glue honest-unavailable |
| eval reproduces (−125.1, CI lb>0) | NOT RE-RUN | Python execution blocked; policy .zip present so runnable locally |
| tests pass | NOT RE-RUN | pytest blocked; tests read and assert real behaviour |
