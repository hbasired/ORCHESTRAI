# ADR — Stage 6 Depth-Hardening: integrate the deepened loop + richer A/B with bootstrap CIs

**Date**: 2026-06-14
**Status**: Accepted
**Stage**: 6 (depth-hardening increment 5/5 — the integration harness; not a new stage number)
**Author personas**: `backend-engineer` (primary) + `ml-engineer` + `agentic-governance-engineer` (ADR)
**Relates**: integrates Stages 8/8B/8C/10 deepenings into the Stage-6 vertical slice. Closes the Stages 6–10
depth-hardening pass. Follows CLAUDE.md Hard Rule 11/11a.

---

## Context

Stage 6 is the live closed-loop harness (predict → diagnose → intervene). Increments 1–4 deepened the pieces
(Stage-8 TTF world model, Stage-8B learned-causal diagnosis, Stage-8C neuro-symbolic verifier, Stage-10
SHAP/DiCE explanations) but the **VERIFY step was built and not wired into the live loop**, and the slice carried
no forecast/explanation provenance. This increment wires them in and upgrades the A/B to report confidence intervals.

## Decisions

**D1 — Wire the deepened pipeline into the live loop, additively.** `services/slice_runner.py::run_slice_step` now
runs **predict → forecast TTF (Stage 8) → diagnose+causal (Stage 8B, already in `diagnose`) → explain (Stage 10
exact-SHAP) → VERIFY (Stage 8C plan verifier) → intervene**. Each piece is availability-gated and ADDITIVE:
  - a per-stage telemetry **window buffer** feeds the world model → `ttf_forecast` on the prediction event
    (measured: surfaces on **90%** of at-risk predictions; the 10% are honest fast-degradation cases with <6
    samples of history);
  - the exact-SHAP **top drivers** (+ counterfactual) attach to the intervention event (the "why");
  - the **neuro-symbolic plan verifier GATES execution** — a maintenance only fires if the symbolic
    safety/precondition contract APPROVES it.

**D2 — Verification preserves the measured A/B.** The verifier is built from a Stage-6 PlantState with
`available_crew = n_stages` (Stage 6 models unlimited crew; crew contention is the Stage-7 RL env's concern), so it
APPROVES the normal single-machine maintenance — execution, and therefore the measured numbers, are unchanged. The
verifier's value here is the real per-action precondition/throughput/redundancy gate, now in the live path.

**D3 — Richer A/B with paired bootstrap 95% CIs.** `scripts/run_slice_ab.py` adds CRN-paired bootstrap (5000
resamples) 95% CIs over per-seed OFF−ON differences. Measured (5 seeds, 8 sim-h): **unplanned downtime −182 min,
95% CI [93, 274] (significant)**; **crack breakdowns −4.2, CI [3, 5] (significant)**; **throughput −0.05 u/h, CI
[−0.22, 0.12] (NOT significant — no throughput cost)**. The honesty rule holds: the sign is reported, not asserted,
and with few seeds the CIs are (truthfully) wide.

**D4 — Audit holds 364 (`--no-baseline-drop`), additive.** New code adds zero theatrical patterns; the integration
is wiring, not new fakery. 31 slice/verifier tests pass; no regression.

## Why
- The VERIFY leg existed but a built-and-unwired safety gate is not real until it sits in the live path; wiring it
  (without changing the measured outcome) makes the loop genuinely predict→reason→verify→intervene.
- A single mean delta hides uncertainty; bootstrap CIs are the honest way to say whether the slice's benefit is
  statistically supported (it is, for downtime and breakdowns).

## Consequences
- Modified: `backend/services/slice_runner.py` (deepened `run_slice_step` + `SliceLoop` wiring + helpers),
  `backend/scripts/run_slice_ab.py` (bootstrap CIs + pipeline note). New eval artefacts under
  `training/evals/stage06/`. This ADR + explainer.
- 31 slice/verifier tests pass; audit holds 364; the measured A/B improvement is preserved AND now CI-bounded.
- The live loop now emits forecast/explanation/verification provenance per decision — the audit-chain (Stage 13.5)
  + Annex IV pack (Stage 19) will record it.

## Alternatives rejected
1. **Leave VERIFY unwired (it "exists").** Rejected — a safety gate not in the live path is not real.
2. **Let the verifier model crew contention (capacity 1) in Stage 6.** Rejected — Stage 6 models unlimited crew;
   imposing crew contention would change the measured A/B and conflate Stage-7's concern into Stage 6.
3. **Report only the mean delta.** Rejected — bootstrap CIs are the honest depth (uncertainty, significance).

## References
- `backend/services/slice_runner.py` (deepened loop) · `backend/scripts/run_slice_ab.py` (bootstrap CIs).
- Eval `training/evals/stage06/results.{json,md}`. KB: KB_23, KB_25.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:29+00:00 -->
<!-- signature: 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 -->
