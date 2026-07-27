# ADR — Stage 8 Depth-Hardening: Transformer RUL (real C-MAPSS) + learned causal discovery + neuro-symbolic verify

**Date**: 2026-06-14
**Status**: Accepted
**Stage**: 8 (depth-hardening increment — re-opens the closed Stage-8 implementation to deepen it; not a new stage number)
**Author personas**: `ml-engineer` (primary) + `agentic-governance-engineer` (ADR)
**Relates**: deepens `2026-06-13_world_model_causal_diagnose.md` (the original honest-but-bounded Stage 8). Part of the
operator's Stages 6–10 depth-hardening pass (plan: `this-is-not-the-eventual-garden.md`; research: initial-research §16).

---

## Context

The operator judged Stages 6–10 *honest but shallow* — "easy implementations which will downgrade the product and
make it less intelligent" — and that no per-stage web research was done. Stage 8 (the biggest depth gap) shipped:
a toy 1-layer LSTM on a near-trivial SimWorld signal (97.8% but easy), a **hand-coded** known-SCM counterfactual
(not learned), and **no** VERIFY step. A SOTA research pass (research §16) grounded a deeper, still-honest,
free/local/CPU build.

## Decisions

**D1 — Transformer RUL on the REAL C-MAPSS FD001 benchmark (architecture + real data deepening).** New
`backend/ml/rul_transformer.py` (Transformer encoder, self-attention over a 30-cycle × 14-sensor window) +
`training/stage_08_world_model/{cmapss_data,train_cmapss,eval_cmapss}.py`. Standard leakage-free protocol
(14 informative sensors, train-only min-max, piecewise RUL cap 125, engine-level val split, single test eval).
**Measured: FD001 test RMSE 13.80 / NASA-score 372** — beats the CNN (18.45) and LSTM (16.14) literature
baselines, competitive with the DCNN/Transformer SOTA (~11–13), +66% over the naive baseline. A real,
comparable benchmark number replaces the near-trivial SimWorld signal. Model card + weights committed. The
original `world_model_ttf` LSTM is retained for the live-loop TTF signal (it is the in-sim timing signal); the
C-MAPSS Transformer is the benchmark-grade PREDICT deepening.

**D2 — LEARNED causal discovery validates the known SCM (G-020 advance).** New `backend/ml/causal_discovery.py`
runs the **PC algorithm** (causal-learn, Fisher-Z) on SimWorld telemetry and **recovers crack_proximity as the
common-cause hub** of the degradation sensors — skeleton **F1 0.75, 4/5 hub edges, proximity = max-degree node**
(canonical 100-seed report `training/evals/stage08/causal_discovery.json`). This empirically validates the
hand-coded SCM assumption that `services/diagnosis.py::attribute_cause` relied on (previously asserted, not
measured). `attribute_cause` now annotates each attribution with the learned-discovery support (additive,
back-compatible). Honest limits stated: ~3 K temperature edges sit near the sensor-noise floor and are below
PC's power; linear Fisher-Z cannot fully screen the semi-nonlinear rpm/wear coupling.

**D3 — Neuro-symbolic VERIFY step built (KB_25 step 3, was PLANNED-only).** New
`backend/services/plan_verifier.py` — the **symbolic half** of neuro-symbolic verification: a deterministic
constraint engine that checks a proposed intervention plan against declarative pre/post-conditions + safety
contracts (crew capacity, maintenance precondition, throughput floor, SIL critical-redundancy) and **rejects
unsafe plans** before any actuator moves. The neural proposer (world-model/causal/RL) proposes ⟂ this symbolic
engine disposes. Composes with the Stage-17 actuator wrapper (KB_17), which it predates.

**D4 — Free/OSS/local deps + real dataset.** Added causal-learn, dice-ml, stable-baselines3, sb3-contrib,
gymnasium (all free OSS); pinned **pandas 2.2.3** (dice-ml needs ≥2.0; streamlit/mlflow <3 satisfied; the unused
Stage-2 `tts`<2.0 voice dep is knowingly sacrificed). C-MAPSS FD001 cached under `data/datasets/cmapss/`
(git-ignored), downloaded from two recorded public mirrors with an honest `DatasetUnavailableError` if offline.

**D5 — Audit holds at 364 (`--no-baseline-drop`), additive.** The deepening ADDS real models; it removes no
grep-counted theatre (the remaining counted hits live in Stage-11+ files). New code introduces **zero**
theatrical patterns (audit count unchanged at 364, confirming no `random.*`/mock fallbacks). Justified in
`KB_TASK_LOG.md`, same pattern as the original additive Stage 8.

## Why
- The PREDICT step needed a real, comparable benchmark to be credible — C-MAPSS is the canonical one, and a
  Transformer on it is honest depth (real number, real architecture), not a near-trivial-signal score.
- The causal step claimed a structure it never measured; learned PC discovery turns the assumption into an
  empirical, reproducible validation — the honest way to back a causal claim.
- The VERIFY step was the missing leg of KB_25's loop; a symbolic constraint engine is the dependency-light,
  auditable, formally-grounded core that a learned proposer must pass.

## Consequences
- New: `backend/ml/rul_transformer.py`, `backend/ml/causal_discovery.py`, `backend/services/plan_verifier.py`,
  `training/stage_08_world_model/{cmapss_data,train_cmapss,eval_cmapss}.py`,
  `compliance/model-cards/rul_transformer_cmapss.md`, tests (`test_rul_transformer`, `test_causal_discovery`,
  `test_plan_verifier`), this ADR, the explainer refresh, research §16.
- Modified: `backend/services/diagnosis.py` (additive learned-discovery support), `backend/requirements.txt`.
- Models: `models/rul_transformer_cmapss.{pt,metrics.json}` (real benchmark). Eval artefacts under
  `training/evals/stage08/`.
- Audit **holds 364** (`--no-baseline-drop`, additive). 31 Stage-8 tests + 71 sim/slice/model regression tests pass.
- G-020 advances from PARTIAL → **learned discovery + neuro-symbolic verify now BUILT** (sim-scope; real-fleet
  re-discovery remains G-035). G-019 stays resolved.

## Alternatives rejected
1. **Keep the toy SimWorld LSTM / hand-coded SCM.** Rejected — that was exactly the shallow path the operator flagged.
2. **KCI (kernel) CI test for causal discovery.** Rejected at this sample size (too slow for 8k samples on CPU);
   Fisher-Z on the linear degrading regime is well-specified and fast, with honestly-stated limits.
3. **Full SMT/temporal-logic verifier.** Deferred — the declarative predicate engine is the verifiable,
   dependency-light core; an SMT/LTL deepening is a future option.
4. **Chase the ~3 K temperature edges to lift F1.** Rejected as over-fitting effort to a near-noise signal;
   reported honestly as a limitation. The robust hub property is the claimable result.

## References
- `backend/ml/rul_transformer.py` (RMSE 13.80 / NASA 372 on FD001) · `models/rul_transformer_cmapss.metrics.json`.
- `backend/ml/causal_discovery.py` (PC, F1 0.75, prox-hub) · `training/evals/stage08/causal_discovery.json`.
- `backend/services/plan_verifier.py` (VERIFY step) · KB_25 (loop), KB_02/05/23 (models/sim/evals).
- Research: `research/initial-research.md` §16. Model card: `compliance/model-cards/rul_transformer_cmapss.md`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:29+00:00 -->
<!-- signature: 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 -->
