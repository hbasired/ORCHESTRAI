# Stage 10 — Independent Review (Explainability: exact TreeSHAP + real counterfactual)

**Reviewer**: fresh `task-auditor` agent (read-only)
**Date**: 2026-06-13
**Target**: `tasks/STAGE_10_explainability.md` (ACs 1–8; AC8 is this review)
**Verdict**: **PASS**

---

## Independence statement

I did NOT implement Stage 10. I read only the files named in the audit brief, re-ran the stage's tests,
re-ran the mechanical audit, and independently verified the two load-bearing claims (exact-SHAP invariant
and a model-scored counterfactual) with my OWN snippets rather than trusting the supplied tests. The only
file I wrote is this review. I fixed nothing and ledgered nothing.

---

## What I ran (real output)

### 1. Stage tests
`cd backend && python -m pytest tests/test_explainability.py tests/test_models.py -q`
→ **27 passed, 0 skipped** (the `@needs_model` SHAP/counterfactual tests actually RAN — the XGBoost brain is
present in this environment, so they were not silently skipped). Only deprecation warnings (numpy scalar /
pytest-asyncio), no failures.

### 2. No-regression (Stages 4/8/9)
`cd backend && python -m pytest tests/test_failure_predictor.py tests/test_world_model.py tests/test_diagnosis.py tests/test_vision_defect.py -q`
→ **25 passed, 1 skipped** (the 1 skip is an honest model-unavailable skip in `test_vision_defect.py`).
The new `feature_names`/`raw_vector`/`shap_contribs` helpers did not break `predict_failure`.

### 3. Mechanical audit
`bash scripts/audit.sh` → **TOTAL 364**, Baseline 383, `OK: count decreased from 383 to 364.`
`random_uniform_py = 115` (none in `ml/explainability.py` — confirmed by grep, only 2 matches and both are
in a docstring/comment). No `--no-baseline-drop` used; genuine strict decrease.

### 4. SHAP invariant — my own verification (not the test)
```
sum(shap)          = 1.2643
base_value_margin  = 0.1092
sum(shap)+base     = 1.3735
model_margin       = 1.3736
abs(diff)          = 1.0e-04        invariant<1e-3? = True

sum(contribs)      = 1.373558
output_margin (booster.predict output_margin=True) = 1.373557
abs(diff)          = 9.1e-07        match<1e-4? = True
```
The Shapley contributions returned by `shap_contribs` sum (incl. bias) to the booster's raw `output_margin`
to ~9e-7. This is real XGBoost `pred_contribs`, not approximated or fabricated.

### 5. base_score / probability nuance — my own verification
```
sigmoid(margin)    = 0.797954
p_fail (predictor) = 0.820500
abs(diff)          = 0.022546   (code claims "within ~0.02")
sig == p_fail ?    = False
```
The code does NOT claim `sum(shap)==logit(p_fail)` (which would be FALSE). It honestly states in the `method`
field that `sigmoid(margin) approximates p_fail within ~0.02` and that XGBoost applies a `base_score` offset.
Measured gap 0.0225 ≈ the disclosed ~0.02. Honest disclosure confirmed (`failure_explainer.py:75-78`,
ADR D1).

### 6. Counterfactual — my own verification (not the test)
```
at_risk=True  p_fail=0.8205  threshold=0.779
minimal_change = Rotational speed [rpm] 1380.0 -> 1397.25 (+1.2%)  p_fail_after=0.6462
Re-scored on REAL predict_failure: p_fail 0.8205 -> 0.6462  at_risk -> False  (below 0.779) ✓
alternatives (all real model-scored):
   Tool wear [min] 215->204.25 (-5.0%)  p_fail 0.7781
   Torque [Nm]     60->55.5    (-7.5%)  p_fail 0.6563
   Rotational speed 1380->1397.25 (+1.2%) p_fail 0.6462
```
Every candidate is scored by the actual predictor. The minimal-change winner genuinely flips the verdict when
applied to the real model. "Smallest relative change wins" logic is correct.

### 7. Honest unavailability — my own verification
- `FailureExplainer(FailurePredictor(models_dir=<empty>))`: `is_available()=False`, `explain(...)` raises
  `ModelUnavailableError` (no fabrication). ✓
- `shap_contribs` on a forced non-xgb (`_kind='mlp'`) instance raises `ModelUnavailableError`
  (`"exact TreeSHAP requires the XGBoost brain (active arch is 'MLP'); no fabricated attributions."`) —
  it refuses to approximate-and-pretend. ✓ (`failure_predictor.py:169-173`)

---

## Findings per acceptance criterion

| AC | Claim | Independently confirmed? | Evidence |
|---|---|---|---|
| AC1 — Exact TreeSHAP, no extra dep | per-feature Shapley via XGBoost native `pred_contribs`; `sum(shap)+base == margin`; top driver = Tool wear | **YES** | `failure_predictor.py:163-181` builds `xgb.DMatrix(...feature_names=booster.feature_names)` then `booster.predict(dm, pred_contribs=True)`. My snippet: invariant diff 1e-4 (<1e-3); `sum(contribs)==output_margin` to 9e-7. `test_shap_top_driver_is_tool_wear_for_worn_machine` passes. No `shap` lib imported. |
| AC2 — Real counterfactual | guided minimal-change search over the ACTUAL predictor; flip drops p_fail below threshold; honest when none | **YES** | `failure_explainer.py:86-126`: each candidate calls `self._predictor.predict_failure(**trial)`. My snippet: rpm +1.2% drops p_fail 0.8205→0.6462<0.779. Honest "no single feature flipped" branch present (`:119-122`). |
| AC3 — `explainability.py` de-mocked | all `random.*` removed; delegate real SHAP/CF for `failure_features`; honest-empty for generic; `compute_attention` returns `[]` | **YES** | Grep: only 2 `random.` matches, both in docstring/comment (`:5`, `:80`), zero executable. `compute_shap`/`generate_counterfactuals` delegate via `failure_explainer` (`:54-76`, `:136-159`); return `[]` for generic; `compute_attention` returns `[]` (`:78-81`). `test_explainability_module_honest_empty_for_generic` passes. git diff: 422 deletions, 198 net reduction. |
| AC4 — Honest unavailability | raises `ModelUnavailableError` if brain/lib absent or arch non-xgb | **YES** | My snippet raised in both cases. `failure_predictor.py:169-173`, `failure_explainer.py:46-47`. |
| AC5 — Audit strictly decreases | 383 → 364, no `--no-baseline-drop` | **YES** | `audit.sh` TOTAL=364 < 383. Old HEAD `explainability.py` had 22 executable random sites (20 `uniform`+2 `randint`); new has 0. Genuine theatre removal, not metric-gaming. |
| AC6 — Tests green + no regression | new tests pass; Stage 4/8/9 still pass | **YES** | 27 passed (stage) + 25 passed/1 honest skip (regression). |
| AC7 — ADR + KB + explainer | ADR; KB_02/23/25; explainer HTML | **PARTIAL (see gap G-S10-1)** | ADR `2026-06-13_explainability_shap_counterfactual.md` present and honest (esp. D1 base_score nuance). KB_02/23/25 in modified set per mechanical audit. **Explainer HTML `research/stage-explainers/STAGE_10/index.html` not verified by me** (out of the read-scope brief) — see gap. |
| AC8 — Independent audit PASS | this review | **DONE** | This file. |

---

## Theatrical-work scan

- `ml/explainability.py`: zero executable `random.*` / `_get_demo` / `generate_mock_state` / `heuristic`
  patterns (grep clean; the 2 `random.` hits are documentation of what was removed). The residual audit
  counts (`generate_mock_state=3`, `heuristic_actions=3`) live in OTHER files, not Stage 10's.
- `ml/failure_explainer.py`: no fabrication; every number routes through the real model or `pred_contribs`.
- `ml/failure_predictor.py` helpers: `shap_contribs` refuses (raises) for non-xgb rather than approximating.
- No `--no-verify`, no `--force`, no `--no-baseline-drop`. No hard-rule violations (no LLM-direct actuator,
  no new crypto, no new weight without a card — this stage adds no weight).

## Judgement on SHAP-exactness honesty + de-mock genuineness

- **SHAP is genuinely exact**, not approximated or fabricated: it is XGBoost native `pred_contribs`, the
  invariant holds to 1e-4, and `sum(contribs)` equals the booster's `output_margin` to ~1e-6.
- The **base_score/probability nuance is honestly disclosed**: the code does not claim `sum==logit(p_fail)`;
  it states `sigmoid(margin) ≈ p_fail within ~0.02`, and the measured gap (0.0225) matches. No overclaim.
- The **de-mock is genuine**: 22 executable random sites in the committed prior version → 0; 422 lines
  deleted; the strict decrease is real theatre removal, not a docstring-relocation trick.

## VERDICT: **PASS**

The two load-bearing claims (exact TreeSHAP invariant; model-scored counterfactual) are independently
verified with real numbers. `explainability.py` is genuinely de-mocked. Honest unavailability holds. Audit
strictly decreases (383→364) by real theatre removal. Tests pass with no regression.

### Non-blocking gap (does not block close per AC scope, but should be confirmed by the implementer)
- **G-S10-1 (this stage, AC7 completeness):** I did not independently confirm the existence/honesty of
  `research/stage-explainers/STAGE_10/index.html` (outside my read-scope). The mandatory per-stage explainer
  HTML (CLAUDE.md §6 operator mandate, 2026-06-11) must exist and be honest before `close-task.sh`. The
  implementer should verify it is present with real file paths + the measured numbers above. No later-stage
  ledger entry required.
