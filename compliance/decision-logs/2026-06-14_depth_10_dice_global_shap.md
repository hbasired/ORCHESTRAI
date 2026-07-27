# ADR — Stage 10 Depth-Hardening: DiCE diverse counterfactuals + global SHAP

**Date**: 2026-06-14
**Status**: Accepted
**Stage**: 10 (depth-hardening increment 4/5 — deepens the closed Stage-10 explainability; not a new stage number)
**Author personas**: `ml-engineer` (primary) + `agentic-governance-engineer` (ADR)
**Relates**: deepens `2026-06-13_explainability_shap_counterfactual.md` (v0 exact-SHAP + single-feature CF).
Stages 6–10 depth-hardening pass; research §16.6. Follows CLAUDE.md Hard Rule 11/11a (full depth first).

---

## Context

The v0 Stage-10 explainer shipped exact TreeSHAP (already exact — kept) plus a **single-feature** greedy
counterfactual, and explicitly deferred DiCE-the-library + global SHAP as "later refinements". Research §16.6 (SHAP
+ DiCE diverse recourse + global attribution) makes those the standard depth — and Hard Rule 11a says the deeper
version IS the first implementation. The deps are now installed (dice-ml).

## Decisions

**D1 — DiCE diverse, multi-feature, actionable counterfactuals.** New `backend/ml/dice_explainer.py` uses
**dice-ml** (random method) to generate several DIFFERENT minimal recipes that each flip the predictor at-risk →
safe (e.g. "torque −35% AND tool-wear −62%"), beyond the v0 single-feature search. Crucially, DiCE varies only the
**actionable base physical features** (torque↓, rpm↑, tool-wear↓) through a sklearn-compatible black-box wrapper of
`predict_failure`, so the **derived features (temp_diff, power_w) are recomputed internally** — every counterfactual
is physically consistent. Each returned recipe is re-verified against the REAL predictor (`flips=True`). Measured: on
an at-risk machine (p_fail 0.966) DiCE returns 4 diverse recipes, all verified to flip below threshold.

**D2 — Global SHAP.** `dice_explainer.global_importance(n)` aggregates XGBoost's exact native TreeSHAP over a
reference sample → mean |Shapley| per feature (dataset-level "what drives risk in general") + mean signed Shapley,
complementing the per-decision SHAP. Dependency-light (reuses `predictor.shap_contribs`). Measured top drivers:
power_w, rotational speed, torque.

**D3 — Wired into the Stage-10 explainer, honest-unavailable.** `failure_explainer.explain(..., diverse_cf=True)`
adds a `diverse_counterfactual` field; `FailureExplainer.global_importance()` delegates to the DiCE explainer. Both
return honest "available: False" / raise `ModelUnavailableError` if dice-ml or the XGBoost brain is absent — never
fabricate. The reference distribution is the documented AI4I operating envelope (used by DiCE for feasibility).

**D4 — No new trained weight; audit holds 364 (`--no-baseline-drop`).** DiCE + global SHAP are METHODS over the
existing XGBoost predictor (like the v0 SHAP) → no model card. New code adds zero theatrical patterns (count
unchanged confirms it).

**D5 — Multi-model neural attribution scoped, not faked.** Extending Deep/gradient SHAP to the RUL transformer /
defect CNN is documented as a future item: those are perception/forecast models, whereas the failure predictor is
the in-loop DECISION model whose recourse matters most. Scoping with rationale — not a shortcut, and nothing
fabricated for the neural models.

## Why
- Single-feature counterfactuals are a thin recourse story; DiCE's diverse multi-feature recipes are the SOTA,
  genuinely more useful (an operator gets options), and now free/local. Keeping derived features consistent makes
  them physically valid — the honest way to do counterfactuals over engineered features.
- Global SHAP turns per-decision attribution into a dataset-level driver view at near-zero cost (exact TreeSHAP).

## Consequences
- New: `backend/ml/dice_explainer.py`, `backend/tests/test_dice_explainer.py`, this ADR, explainer refresh.
- Modified: `backend/ml/failure_explainer.py` (+`diverse_cf` option, +`global_importance`).
- 13 DiCE/explainability + 19 model tests pass; audit holds 364; no regression.
- Advances the trust/auditable-decisions leg (KB_25); still over an AI4I-proxy model (G-035).

## Alternatives rejected
1. **Keep only the v0 single-feature counterfactual.** Rejected — the shallow choice Hard Rule 11a forbids.
2. **Let DiCE vary the derived features directly.** Rejected — would produce physically-inconsistent counterfactuals
   (temp_diff/power_w not matching torque/rpm); varying base features + recomputing is correct.
3. **Install `shap` for global/Deep SHAP.** Unnecessary for the tabular model — XGBoost native TreeSHAP is exact and
   dependency-light; a neural Deep-SHAP is the scoped future item (D5).

## References
- `backend/ml/dice_explainer.py` (DiCE diverse CF + global SHAP) · `backend/ml/failure_explainer.py`.
- Tests `backend/tests/test_dice_explainer.py`. Research §16.6. KB: KB_02, KB_23, KB_25.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:30+00:00 -->
<!-- signature: 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 -->
