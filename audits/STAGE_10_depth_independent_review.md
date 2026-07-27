# Independent Review — Stage 10 Depth-Hardening (DiCE diverse counterfactuals + global SHAP)

**Auditor**: independent `task-auditor` (did NOT implement this increment).
**Date**: 2026-06-14.
**Scope**: the 2026-06-14 Stage-10 depth increment — DiCE diverse multi-feature counterfactuals + global SHAP.
**ADR reviewed**: `compliance/decision-logs/2026-06-14_depth_10_dice_global_shap.md`.

## VERDICT: PASS

Claim — DiCE generates diverse, physically-consistent counterfactuals that are **re-verified against the REAL
predictor**, plus global **exact** TreeSHAP — is fully supported by the code. The counterfactuals are NOT fabricated:
each recipe is re-scored by `predict_failure` and flagged `flips`. Varying only base physical features keeps derived
features (temp_diff, power_w) consistent because the predictor recomputes them. Global SHAP uses XGBoost's exact
native `pred_contribs` (not an approximation). Honest-unavailable throughout. Execution caveat below: harness blocked
Python execution, so I could not personally re-run the three test files; verdict rests on static analysis + the
mechanical audit (which I ran).

## Execution caveat (transparency)

`python -m pytest` was **denied by the harness permission layer** this session (Python execution blocked; only
`git`/`ls`/`scripts/audit.sh` permitted). I could NOT re-run `tests/test_dice_explainer.py`,
`tests/test_explainability.py`, or `tests/test_models.py`. Everything below is from reading source. I DID run
`scripts/audit.sh`: **TOTAL = 364 = baseline**.

## CRITICAL CHECK 1 — counterfactuals re-scored by the REAL predictor (not fabricated)

**Confirmed. Each recipe is independently re-verified.** In `dice_explainer.py::diverse_counterfactuals`
(lines 109-154), after DiCE returns candidate rows, each recipe is **re-scored by calling the real
`predict_failure`** with the counterfactual's base features (lines 145-148), and `flips = bool(p_after < thr)`
(line 150) is computed from that real prediction — not asserted, not fabricated. The test
`test_diverse_counterfactuals_flip_real_model` (test_dice_explainer.py:32-42) asserts at least one recipe genuinely
flips the real predictor and that only actionable features changed.

## CRITICAL CHECK 2 — derived-feature physical consistency

**Confirmed.** `_PredictorBlackBox` (dice_explainer.py:40-63) is the sklearn-compatible black box DiCE queries; its
`predict_proba`/`predict` call the REAL `predict_failure` per row over the **base** features only. DiCE is told
`features_to_vary=_ACTIONABLE` = `["torque_nm","rot_speed_rpm","tool_wear_min"]` (line 131) and the reference data
declares only `_BASE_FEATURES` as columns (line 105) — so DiCE never sees or mutates `temp_diff`/`power_w`. Those are
recomputed inside `failure_predictor._raw_vector` (verified: `temp_diff = process_temp_k - air_temp_k`,
`power_w = torque * rpm * 2π/60`, failure_predictor.py:110-111) every time `predict_failure` runs. Therefore every
counterfactual is physically consistent — derived features always match the (varied) base features. ADR Alternative
#2 (rejecting "let DiCE vary derived features directly") matches the code.

## CRITICAL CHECK 3 — global SHAP is EXACT (not approximated)

**Confirmed exact.** `global_importance` (dice_explainer.py:156-175) calls `predictor.shap_contribs(vec)` per
reference row and aggregates mean|Shapley|. `shap_contribs` (failure_predictor.py:163-175) uses **XGBoost's native
`pred_contribs`** (exact TreeSHAP, margin space) and **raises `ModelUnavailableError` if the active brain is not
XGBoost** — "no fabricated attributions". No sampling/kernel approximation. The bias term is correctly dropped
(`[:-1]`, line 168). Importance is sorted descending (line 171); the test
`test_global_importance_well_formed` asserts the descending sort and positive top driver.

## CRITICAL CHECK 4 — honest-unavailable, never fabricates

**Confirmed.**
- `DiceExplainer.is_available()` (lines 76-86) returns False if `dice_ml` import fails OR the brain is not XGBoost.
- `_build()` raises `ModelUnavailableError` if dice-ml/pandas absent or non-XGBoost brain (lines 91-97).
- `failure_explainer._diverse_counterfactual` (failure_explainer.py:88-101) returns `{"available": False, ...}`
  (never fabricates) if DiCE unavailable or on any exception. `global_importance` delegates to the DiCE explainer.
- `diverse_counterfactuals` returns `{"needed": False}` when the machine isn't at-risk (p0 < threshold,
  lines 126-128) and `{"found": False, "note": ...}` if DiCE finds nothing in bounds (lines 133-138) — honest, no
  invented recipe.
- No `random.uniform|random.choice|generateMockState|_get_demo_*|RESPONSES =|MODELS =` in `dice_explainer.py`.
  (The `rng.uniform` at lines 100/159 builds the reference SAMPLE from the documented operating envelope — a
  legitimate, disclosed reference distribution, not a fabricated prediction; and it's analysis code, not a serving
  fallback.)

## Wiring verified

`failure_explainer.explain(..., diverse_cf=True)` adds a `diverse_counterfactual` field (failure_explainer.py:84-85);
`FailureExplainer.global_importance()` delegates to the DiCE explainer (lines 103-106). The v0 exact single-feature
SHAP + greedy counterfactual remain (the `counterfactual` path is unchanged) — additive deepening, not replacement.

## No new weight (correct)

DiCE + global SHAP are METHODS over the existing XGBoost predictor — no new `.pt`/`.metrics.json`/model-card
required (ADR D4). Correct: nothing new is trained.

## Mechanical audit

`bash scripts/audit.sh` → **TOTAL 364 = baseline** (`--no-baseline-drop`, justified: methods over an existing model,
zero grep-counted theatre). Confirmed zero new theatrical patterns in `dice_explainer.py` / `failure_explainer.py`.

## Gaps / overclaims found

**None that block.** Honest scope items (disclosed, not gaps): runs over the AI4I-proxy XGBoost model (G-035);
neural Deep/gradient SHAP for the RUL transformer / defect CNN is **scoped as future** (ADR D5) with rationale (those
are perception/forecast models; the failure predictor is the in-loop decision model) — scoped, not faked, nothing
fabricated for the neural models.

Minor note (non-blocking): `test_dice_honest_unavailable_when_no_dice` (test_dice_explainer.py:23-28) cannot truly
uninstall dice-ml mid-test, so it only asserts the contract shape (`isinstance(is_available(), bool)`). The honest-
unavailable path is nonetheless real in code (verified above); a stronger test would monkeypatch the import. Not a
defect — the production code is honest.

## Independent confirmation table

| Claim | Confirmed? | Basis |
|---|---|---|
| Counterfactuals re-scored by REAL predictor (flips verified) | YES | dice_explainer.py:145-150 re-calls predict_failure |
| Only base features varied → derived features consistent | YES | features_to_vary=_ACTIONABLE; _raw_vector recomputes temp_diff/power_w |
| Global SHAP is EXACT XGBoost TreeSHAP (not approx) | YES | shap_contribs uses native pred_contribs; raises if non-XGBoost |
| Honest-unavailable if dice-ml/XGBoost absent | YES | is_available()/_build()/_diverse_counterfactual all honest |
| No new weight; audit holds 364, zero new theatre | YES (I ran audit.sh) | TOTAL 364; no random/mock in new code |
| diverse_cf + global_importance wired into explainer | YES | failure_explainer.py:84-106 |
| tests pass | NOT RE-RUN | pytest blocked by harness; tests read and assert real behaviour |
