# ADR — Stage 7: PPO Intervention Policy (RL substrate + safety shield; rules remain default)

**Date**: 2026-06-12
**Status**: Accepted
**Stage**: 7 (RL Intervention — KB_25 step 4, INTERVENE)
**Author personas**: `ml-engineer` (primary) + `backend-engineer` (wiring) + `agentic-governance-engineer` (ADR)
**Supersedes/relates**: builds on Stage 6 (`2026-06-11_strategic_product_reset.md` D4 slice) and KB_25
(`2026-05-31_causal_self_healing_engine.md`). Advances gap **G-025** (PPO intervene) and resolves **G-046**
(A/B CRN pairing + CIs).

---

## Context

Stage 6 shipped the first closed predict→diagnose→intervene loop with a deterministic v0 intervention chooser
(`services/intervention_policy.py`) that prevents 92–100% of crack breakdowns. Stage 7's mandate (task doc):
"replace the deterministic chooser with a PPO policy over the SAME `InterventionDecision` contract — and the
measured Stage-6 rules baseline is the number PPO must beat to earn its place; if it cannot, the rules stay
(honesty rule: the better policy wins, not the fancier one)." Free-cost constraint: no paid services, CPU only.

## Decisions

**D1 — Real RL substrate, from scratch, no heavy deps.** A compact, auditable PPO (PPO-clip + GAE-λ, shared-trunk
actor-critic MLP) in `backend/training/stage_07_rl_intervention/ppo.py` using only the already-pinned `torch`
(CPU) + numpy. No stable-baselines3 / gymnasium (free-cost, minimal supply chain, fully auditable). Correctness
independently verified on a trivial contextual bandit (`test_ppo_learns_on_bandit`).

**D2 — Event-driven, capacity-constrained environment.** `InterventionEnv` wraps SimWorld headlessly with a
**maintenance-crew capacity constraint** (the regime where greedy rules can mis-prioritise). The constraint lives
in the ENV, not in SimWorld — so Stage-6 behaviour (unlimited implicit crew) is unchanged and **no Stage-6 test or
A/B regresses** (`sim_world.py` untouched, contrary to the task doc's initial Files-to-MODIFY guess — recorded
here as the honest as-built). Control returns to the agent only at real decision points (≥1 at-risk machine AND
crew free), concentrating the learning signal. Reward = throughput − breakdown penalty − maintenance occupancy −
**dense risk-exposure shaping** (objective-aligned; does not dictate which machine — prioritisation is learned).

**D3 — Safety shield (shielded RL).** At inference the stochastic net is wrapped by a hard shield: crew free +
any at-risk machine's risk ≥ critical (0.85) → maintenance FORCED on the highest-risk machine regardless of the
sampled action. Satisfies the ml-engineer mandate ("no policy that allows known-unsafe actions even at low
probability"); verified by test and observed live (raw net chose stage 9; shield forced at-risk stage 3).

**D4 — Honest "better policy wins": RULES REMAIN THE DEFAULT.** Measured (8 paired CRN seeds, 95% CI):
no-intervention 4.0 ± 0.52 crack-breakdowns; **rules_priority 0.375 ± 0.36**; ppo_shield 0.875 ± 0.25; paired
PPO−rules diff +0.5 ± 0.37 (PPO slightly worse, CI excludes 0). Training return improved −160.8 → −134.0
(pipeline learns; beats no-intervention). Therefore `intervention_policy.DEFAULT_CHOOSER = "rules"`; PPO ships
trained + shielded + available via `select_chooser("rl")` but **not default**. This is a deliberate, documented
negative-vs-rules result — the problem has little RL headroom at v0 (cracks rarely create a genuine
prioritisation dilemma), and forcing a marginal "win" would violate the honesty rule.

**D5 — Pluggable chooser seam, contract proven, granularity disclosed.** `select_chooser("rules"|"rl")` returns
either the per-machine rules function (default) or the fleet-level `RLInterventionPolicy` (PPO+shield). Both
produce `InterventionDecision`. They differ in granularity (rules = per-machine in the slice; RL = fleet-level
crew allocation) — stated honestly rather than faking a per-machine RL call. The slice's default path is unchanged.

**D6 — Audit baseline held at 396 (`--no-baseline-drop`).** Stage 7 is an additive ML stage: it adds a trained
model + RL substrate and introduces ZERO new theatrical patterns; the intervention path is already mock-free. The
remaining RL-flavoured theatre (`ml/rl_policy.py` untrained-actor + `random.*` heuristic, consumed only by the
off-slice, still-theatrical `decision_engine.py` + its `test_models.py` tests) is a robot-navigation/
decision-engine concern explicitly owned by **Stage 11**. De-mocking it here would either entangle two unrelated
subsystems or game the audit metric (remove grep-counted lines while leaving grep-invisible untrained-model
fabrication) — both rejected on honesty grounds.

## Why

- The mandate's honesty rule is explicit; the measured result says rules win, so rules stay default. The genuine,
  lasting value is the reusable RL substrate (env + PPO + paired eval) + the safety-shield pattern + a rigorous
  honest finding — not a manufactured PPO victory.
- Crew-capacity-in-env preserves Stage 6 exactly (zero regression), the highest-integrity way to add the RL regime.
- weights_only=True load keeps the new `.pt` free of the pickle code-execution surface the project guards against.

## Consequences

- New: `backend/training/stage_07_rl_intervention/{env,ppo,train,eval,config}.py`, `backend/ml/intervention_rl.py`,
  `backend/tests/test_intervention_rl.py` (14 tests), `models/rl_intervention_policy.{pt,metrics.json}`,
  `compliance/model-cards/rl_intervention_policy.md`, `training/evals/stage07/results.{json,md}`.
- Modified: `services/intervention_policy.py` (+`select_chooser`/`DEFAULT_CHOOSER`, docstring). `sim_world.py`,
  `slice_runner.py` UNCHANGED (crew constraint in env; rules default — no show-wiring).
- Audit baseline **396 → 396** (`--no-baseline-drop`, justified above). 14 RL tests + 32 Stage-6 slice tests pass.
- **G-046 RESOLVED** (CRN-paired eval + CIs). **G-025 advanced** (PPO substrate built; full multi-action recovery
  remains Stage 8/11). G-035 still gates real-telemetry claims.

## Alternatives rejected

1. **Force PPO to beat rules** (more tuning / contrived reward). Rejected: violates the honesty rule; the rules
   are genuinely near-optimal at v0; manufacturing a marginal win would be theatre.
2. **stable-baselines3 + gymnasium.** Rejected: heavy deps + version coupling; a from-scratch PPO is auditable and
   dependency-light (and verified correct on a bandit).
3. **De-mock `ml/rl_policy.py` to force a baseline drop.** Rejected (D6): cross-subsystem entanglement or
   audit-metric gaming; it is Stage 11's scope.
4. **Per-machine RL chooser slotted into the slice loop.** Rejected: the RL decision is fleet-level (crew
   allocation); a per-machine RL call cannot form the fleet observation — faking it would be dishonest.

## References

- Metrics: `models/rl_intervention_policy.metrics.json` · Eval: `backend/training/evals/stage07/results.json`
- KB_25 (intervene step), KB_05 (sim), KB_23 (eval), KB_02 (model inventory). Tests: `backend/tests/test_intervention_rl.py`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:28+00:00 -->
<!-- signature: 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 -->
