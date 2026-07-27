# ADR — Stage 10: Explainability (exact TreeSHAP + real counterfactual)

**Date**: 2026-06-13
**Status**: Accepted
**Stage**: 10 (Explainability — the "trust / auditable decisions" leg of the self-healing loop; PRD v3 §18)
**Author personas**: `ml-engineer` (primary) + `agentic-governance-engineer` (ADR)
**Relates**: builds on Stage 4 (XGBoost failure predictor — the model being explained); the honest de-mock pattern from Stages 8–9.

---

## Context

PRD v3 §18 places explainability at Stage 10; KB_25 names "explainable, auditable decisions" as the trust leg.
The repo's `explainability.py` (480 lines) fabricated SHAP importances, attention weights, counterfactuals, and
heatmap scatter with `random.uniform`/`random.randint` (~19 audit-counted sites). `shap` and `dice-ml` are NOT
installed. Key enabler discovered: **XGBoost has built-in exact TreeSHAP** via `booster.predict(pred_contribs=True)`
— no `shap` library needed, and the Stage-4 failure predictor is an XGBoost model.

## Decisions

**D1 — Exact TreeSHAP via XGBoost native `pred_contribs` (no extra dependency).** `backend/ml/failure_explainer.py`
explains the failure predictor with exact per-feature Shapley values. The defining invariant holds exactly:
**`sum(shap_values) + base_value == model raw margin`** (verified: 1.3735 ≈ output_margin 1.3736). Note the honest
nuance: XGBoost applies a `base_score` offset so `sigmoid(margin) ≈ p_fail` within ~0.02 — stated in the
`method` field and the model card, not hidden. Free/local, zero new deps.

**D2 — Real counterfactual (guided minimal-change search over the actual model).** `explain(...)["counterfactual"]`
searches actionable features (tool-wear↓, torque↓, rpm↑) for the smallest change that flips at-risk→not-at-risk,
scoring every candidate with the REAL predictor. When a flip is found, applying it genuinely drops p_fail below
threshold (test-verified). When no single-feature change suffices, it reports that honestly ("needs combined
action") — no fabricated "fix". This is DiCE-style intent without the heavy `dice-ml` dependency.

**D3 — `explainability.py` de-mocked.** All `random.*` fabrication removed. `compute_shap` /
`generate_counterfactuals` delegate to the real `failure_explainer` when the decision carries `failure_features`;
they return **honest-empty** for generic decisions with no model behind them. `compute_attention` returns `[]`
(there is no trained attention model — not fabricated). `generate_natural_language` is preserved (it was honest —
text from real fields). `generate_heatmap_data` derives only from real attention (empty today).

**D4 — Honest unavailability.** The explainer raises `ModelUnavailableError` if the XGBoost brain/lib is absent
(mirrors `failure_predictor`/`world_model`/`defect_classifier`). Exact TreeSHAP requires the tree model; if a
non-XGBoost arch were active, `shap_contribs` raises rather than approximate-and-pretend.

**D5 — Audit STRICTLY DECREASES (383 → 364).** Removing the ~19 `random.uniform`/`random.randint` sites in
`explainability.py` is a genuine de-mock the grep catches. **No `--no-baseline-drop`** — the second consecutive
genuine strict decrease (after Stage 9).

## Why

- The trust/auditable-decisions leg of the USP needs REAL explanations, not fabricated importances. XGBoost's
  native TreeSHAP makes exact Shapley values free and dependency-light — the honest way to deliver it.
- A counterfactual scored by the actual model is genuinely useful (it tells an operator what change would make a
  machine safe) and honest (verified flips, honest "no single fix" when none exists).
- De-mocking the random SHAP both improves honesty and earns a real strict baseline decrease.

## Consequences

- New: `backend/ml/failure_explainer.py`, `backend/tests/test_explainability.py`, this ADR,
  `research/stage-explainers/STAGE_10/`.
- Modified: `backend/ml/explainability.py` (full honest rewrite), `backend/ml/failure_predictor.py` (+`feature_names`,
  `raw_vector`, `shap_contribs` helpers), `backend/tests/test_models.py` (`TestExplainability` honest contract).
- Audit **383 → 364** (strict decrease). 52 tests pass across explainability/models/predictor/vision/world/diagnosis (1 honest skip).
- No new trained weight (SHAP is a method over the existing XGBoost model) → no new model card; KB_02/23/25 updated.
- G-035 still applies: SHAP is exact for the model, but the model is AI4I-proxy-trained; re-fit before pilot.

## Alternatives rejected

1. **Install `shap` + `dice-ml`.** Rejected: XGBoost native TreeSHAP is exact and zero-dependency; `dice-ml` pulls
   heavy deps. A dependency-light real counterfactual search is honest and sufficient at v0.
2. **Keep generic random SHAP "for the dashboard".** Rejected: fabricated importances are exactly the theatre the
   project forbids; honest-empty for unmodelled decisions is correct.
3. **Approximate SHAP for non-XGBoost models.** Rejected: would invite fabrication; raise `ModelUnavailableError`
   instead (only the tree model gets exact TreeSHAP here).

## References

- `backend/ml/failure_explainer.py` (invariant: sum(shap)+base == model_margin).
- KB_02 (failure predictor = XGBoost), KB_23 (eval), KB_25 (explainable decisions).
- Tests: `backend/tests/test_explainability.py`, `backend/tests/test_models.py::TestExplainability`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:28+00:00 -->
<!-- signature: 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 -->
