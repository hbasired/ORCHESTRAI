---
status: done
stage: 10
slug: explainability
created: 2026-06-13
---

# Stage 10 — Explainability (exact TreeSHAP + real counterfactual)

> Explainable, auditable decisions (KB_25; PRD v3 §18 Stage 10): de-mock `explainability.py` from random-fabricated
> SHAP/attention/counterfactuals to **real** explanations for the self-healing spine. (1) **Exact TreeSHAP** for the
> XGBoost failure predictor via XGBoost's native `pred_contribs` (no `shap` library needed) — the per-feature
> Shapley values are exact and the invariant `sum(shap)+base == model raw margin` holds. (2) A **real
> counterfactual** — a guided minimal-change search over the ACTUAL model (how far must tool-wear/torque/rpm move
> to flip at-risk→safe). New `backend/ml/failure_explainer.py`; `explainability.py` delegates to it for failure
> features and returns honest-empty for generic decisions (no fabrication). First-class de-mock: **audit 383 →
> 364** (removes ~19 `random.uniform` sites). Cross-links: KB_25 (explainable decisions) · failure_predictor (Stage 4).

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–10 + §5)

- [x] Read `KB_24` + `KB_25` (explainability is the "trust" leg + auditable-decisions of the self-healing loop). Aligned.
- [x] Read `audits/OPEN_GAPS_LEDGER.md`. Folded for Stage 10: **G-027** (free-cost — honoured: XGBoost native TreeSHAP, no `shap`/heavy deps); explainability de-mock is the in-lane theatre removal (strict decrease). Stage 10.5 = CTO #2 will sweep G-015/G-038/G-039/G-048.
- [x] **Free-cost only:** XGBoost native `pred_contribs` (no `shap`/`dice-ml` install) + a counterfactual search over the real model; no LLM in this stage's loop; OSS/local only. No committed keys.
- [x] **Stage explainer HTML:** `research/stage-explainers/STAGE_10/index.html` written (self-contained, honest, real file paths + measured numbers).

## Pre-requisites

- Stage(s) closed: 2–9. Depends on Stage 4 (XGBoost failure predictor — the model SHAP explains).
- Decision logs honoured: `2026-06-13_world_model_causal_diagnose.md` / `2026-06-13_vision_defect_detection.md` (honest de-mock pattern). New ADR: `2026-06-13_explainability_shap_counterfactual.md`.
- KB files at minimum version: KB_02 (failure predictor = XGBoost), KB_25 (self-healing loop).
- Gaps pulled in: none owned solely here; explainability advances the "trust/auditable" USP leg.

## Acceptance criteria

- [x] **AC1 — Exact TreeSHAP (real, no extra dep).** `backend/ml/failure_explainer.py::FailureExplainer.explain(...)` returns per-feature Shapley values via XGBoost native `pred_contribs`. The invariant **`sum(shap_values)+base_value == model raw margin`** holds exactly (verified by `test_explainability.py::test_shap_is_exact_sum_equals_margin`). Top driver for a worn machine = Tool wear (verified).
- [x] **AC2 — Real counterfactual.** `explain(...)["counterfactual"]` is a guided minimal-change search over the ACTUAL predictor (tool-wear/torque/rpm). When a flip is found, applying it to the real predictor genuinely drops p_fail below threshold (verified by `test_counterfactual_flip_is_scored_by_real_model`). Reports honestly when no single-feature flip exists.
- [x] **AC3 — `explainability.py` de-mocked.** Removed ALL `random.uniform`/`random.randint` fabrication (SHAP, attention, counterfactuals, heatmap). `compute_shap`/`generate_counterfactuals` delegate to the real explainer for `failure_features`; return **honest-empty** for generic decisions (no model behind them); `compute_attention` returns `[]` (no trained attention model). Verified by `test_models.py::TestExplainability` + `test_explainability.py`.
- [x] **AC4 — Honest unavailability.** The explainer raises `ModelUnavailableError` if the XGBoost brain/lib is absent (mirrors `failure_predictor`/`world_model`/`defect_classifier`); never fabricates. Verified.
- [x] **AC5 — Audit strictly decreases.** 383 → **364** (removed ~19 `random.uniform` sites in `explainability.py`). No `--no-baseline-drop` — genuine de-mock.
- [x] **AC6 — Tests green + no regression.** New `test_explainability.py` + updated `TestExplainability` pass; Stage-4/6/8/9 suites still pass (52 passed, 1 honest skip).
- [x] **AC7 — ADR + KB + explainer.** ADR; KB_02 (explainer note) / KB_23 (SHAP-exactness eval) / KB_25 (explainable-decisions step); explainer HTML.
- [x] **AC8 — Independent audit: PASS** (2026-06-13, fresh task-auditor agent → `audits/STAGE_10_independent_review.md`). Independently reproduced the SHAP invariant (sum+base 1.3735 ≈ margin 1.3736; sum(contribs)==output_margin to 9e-7), confirmed the base_score nuance is honestly disclosed, verified the counterfactual drops p_fail 0.82→0.65<0.779, confirmed 22 executable random sites → 0 (audit 364<383, genuine de-mock), honest unavailability, 27+25 tests pass. Explainer HTML confirmed present.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/ml/failure_explainer.py` | Exact TreeSHAP (XGBoost `pred_contribs`) + real counterfactual; honest `ModelUnavailableError` |
| `backend/tests/test_explainability.py` | SHAP-exactness, counterfactual, honest-empty/unavailable tests |
| `compliance/decision-logs/2026-06-13_explainability_shap_counterfactual.md` | ADR |
| `research/stage-explainers/STAGE_10/index.html` | Stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/ml/explainability.py` | De-mock: delegate real SHAP/counterfactual; honest-empty otherwise; remove all `random.*` |
| `backend/ml/failure_predictor.py` | Add `feature_names()`, `raw_vector()`, `shap_contribs()` public helpers (reused by the explainer) |
| `backend/tests/test_models.py` | Update `TestExplainability` to the honest contract |

## Files to DELETE

| Path | Reason |
|---|---|
| (none — methods rewritten in-file) | — |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_02_Models_Inventory.md` (failure_explainer / explainability de-mock note)
- `knowledge-base/KB_23_Evals_and_Benchmarks.md` (Stage 10 SHAP-exactness verification)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (explainable/auditable-decisions capability)

## Verification commands

```bash
bash scripts/audit.sh   # strictly decreases: 383 -> 364
cd backend && python -m pytest tests/test_explainability.py tests/test_models.py -q
bash scripts/independent-audit.sh 10
```

## Audit target

- Pre-stage baseline: **383**.
- Target: **364** (strict decrease). Removed: ~19 `random.uniform`/`random.randint` sites in `explainability.py` (`_generate_shap_values`, `compute_attention`, `generate_counterfactuals`, `generate_heatmap_data`). No `--no-baseline-drop`.

## Role

- Primary: `ml-engineer` (explainability, model-adjacent — owns `backend/ml/`).
- Secondary: `task-auditor` (AC8), `agentic-governance-engineer` (ADR).

## Risks / unknowns

- **SHAP is over the failure predictor (Stage 4), which is AI4I-proxy-trained (G-035)** — the attributions are exact for the model, but the model itself is a proxy; real-telemetry re-fit before pilot still applies.
- **Counterfactual is single-feature minimal-change** (v0): if no single actionable feature flips the verdict it reports "needs combined action" honestly; multi-feature / DiCE-library counterfactuals are a later refinement (not required — the real search is dependency-light and honest).
- The generic decision-engine pipeline now returns honest-empty explanations (no model behind it) — that subsystem's real models are Stage 11's de-mock; not an overclaim here.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-requisites (pre-filled from STAGE_09_vision_defect_detection.md hand-off)


- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*
