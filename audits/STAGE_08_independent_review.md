# Stage 08 — Independent Review

**Stage**: 08 — Learned World Model (time-to-failure forecasting) + Causal Attribution v1
**Task doc**: `tasks/STAGE_08_world_model_causal_diagnose.md`
**Reviewer**: fresh `task-auditor` agent (AC8). Read-only; this is my one and only output file.
**Date**: 2026-06-13

---

## Independence statement

I did **not** implement Stage 8. I read only the files named in the audit scope, re-ran the test suites
and audit myself, and re-ran the held-out TTF eval on seeds the trainer never touched. Every finding
below cites a file:line or a command I actually executed. I fixed nothing and ledgered nothing (no
later-stage gaps found that aren't already tracked under G-020/G-035).

---

## What I ran (real output)

**1. Stage-8 suites (`test_world_model.py`, `test_diagnosis.py`, `test_models.py`)**
```
36 passed, 5 warnings in 15.79s
```
No skips — the TTF `@needs_weights` tests ran (weights present), the honest-unavailable + causal tests ran.
The 5 warnings are pre-existing deprecations (pytest-asyncio loop scope; numpy ndim→scalar in `rl_policy.py`),
unrelated to Stage 8.

**2. No-regression on Stage 6/7/4 (`test_slice_intervene.py`, `test_intervention_rl.py`, `test_failure_predictor.py`)**
```
25 passed, 1 warning in 19.49s
```
Stage-6 slice, Stage-7 RL, Stage-4 predictor all green — no regression.

**3. Mechanical audit (`bash scripts/audit.sh`)**
```
  random_uniform_py               141
  random_choice_py                152
  math_random_ts                   84
  ... (mock_detections 6, generate_mock_state 3, heuristic_actions 3,
        random_choices_py 4, generate_robots 3, rest 0)
  TOTAL                           396
  Baseline (from .audit-baseline): 396
  NO PROGRESS: count is equal to baseline (396).
```
TOTAL == baseline == 396. Flat hold (declared `--no-baseline-drop`).

**4. Fresh-seed eval to test the +97.8% win for seed-specificity**
`cd backend && python training/stage_08_world_model/eval.py --seeds 70,71,72,73`
```
seeds=[70, 71, 72, 73] n=296
TTF MAE: learned=0.066 min  vs naive=2.871 min  (improvement 97.7%)  beats_baseline=True
```
On seeds **never used in training (train=100–139), validation (200–211), or the committed eval (60–64)**, the
learned model lands MAE **0.066 min** vs naive **2.871 min** = **+97.7%**. The win reproduces on unseen seeds; it
is **not** seed-specific. (Note: this eval run rewrote the untracked working-tree `training/evals/stage08/results.json`,
which previously held the 60–64 numbers — that file is `??` untracked, never committed; the 60–64 figures are
independently preserved in `models/world_model_ttf.metrics.json` and the model card, which I read before re-running.
This is the eval script's own write behaviour, not an edit by me.)

---

## Findings per acceptance criterion

| AC | Claim | Confirmed? | Evidence |
|---|---|---|---|
| **AC1** | Learned LSTM TTF forecaster, free+local, real weights+metrics | **YES** | `train.py:97-105` (real `nn.LSTM`→MLP head, SmoothL1 regression); `models/world_model_ttf.metrics.json` (n_train 3251, n_val 852, train 35.9s CPU); torch-CPU + SimWorld rollouts, no external dataset (`rollouts.py:21-24`). |
| **AC2** | TTF MAE beats naive mean-TTF baseline | **YES** | metrics: learned 0.067 vs naive 2.979 (+97.8%); my fresh-seed run: 0.066 vs 2.871 (+97.7%). Baseline is the train-mean predictor (`train.py:131-132`), a fair naive floor. |
| **AC3** | Honest inference glue; `ModelUnavailableError`; `np.random.randn` removed | **YES** | `world_model.py:99` `_load()` then predict; `:59,:61` raise `ModelUnavailableError` on no-torch / no-weights; only `np.random.randn` mention left is the docstring describing the removal (`:10`) — grep for the live pattern in the file returns nothing. |
| **AC4** | Causal attribution v1 over known SCM; back-compatible `Diagnosis` field | **YES** | `diagnosis.py:98-158` `attribute_cause` (do-operator over known SimWorld SCM); `:68` `causal_attribution` field defaults to `{}` (back-compatible); existing Stage-6 fields/`to_dict` keys unchanged; all 10 Stage-6 `test_diagnosis` tests still pass. |
| **AC5** | Honest scope boundary documented (not learned discovery, not neuro-symbolic verify) | **YES** | model card `:47-51`; ADR D5 `:47-51`; `diagnosis.py:118-122` docstring all state known-structure SCM only, G-020 stays open → Stage 17/spike. No overclaim of a causal twin. |
| **AC6** | Tests green + no regression; `test_models.py` updated to honest contract; zero new theatre | **YES** | 36 + 25 passed (above); `test_models.py:80-108` `TestWorldModel` rewritten to assert `ModelUnavailableError` and no random-weight init; integration test `:348-353` confirms legacy `predict()` raises rather than fabricating. Audit flat (no new theatre). |
| **AC7** | Model card + KB + explainer | **YES (card+ADR verified; KB/explainer not in my scope but referenced)** | `compliance/model-cards/world_model_ttf.md` present + honest; ADR `2026-06-13_world_model_causal_diagnose.md` present (untracked, listed in mechanical audit §3). KB_25/02/05/23 + explainer HTML are listed as updated; not re-read here (outside the named scope) — mechanical audit confirms KB_02/05/23/25 carry working-tree diffs. |
| **AC8** | Independent audit PASS | **THIS FILE** | — |

---

## Theatrical-work scan

- `world_model.py`: live `np.random.randn` / random-weights fallback is **gone**; the one occurrence is a
  docstring line (`:10`) documenting the removal. `predict_ttf` (`:92`) and the back-compat `predict` (`:132-143`)
  both route through `_load()` and raise `ModelUnavailableError` rather than inventing a forecast.
- `rollouts.py`: the `rng.uniform` at `:53` randomises the crack ETA (legitimate dataset variation), and
  `np.random.default_rng` at `:98` seeds it — both inside `training/`, exempt from the audit grep and not theatre.
- `diagnosis.py`: pure deterministic functions, no randomness, no fabrication.
- Audit grep TOTAL flat at 396 with zero new in-lane hits in the Stage-8 files. Confirmed by re-run.

---

## Judgement — TTF-win honesty (leakage analysis)

I scrutinised this hard because MAE 0.067 min / +97.8% looks suspiciously perfect. My conclusion: **it is a
real, non-leaky win, and the low number is correctly explained and caveated.**

- **Label is genuine ground truth, not circular.** `rollouts.py:81` labels each window with
  `(fail_at - sample_time)/60`, where `fail_at = stage.crack_failure_at` is set by the sim at
  `stage.py:75` as `crack_scheduled_at + eta_seconds`. It is the sim's own crack schedule — not derived from
  any input feature.
- **`crack_proximity` is NOT a feature.** `FEATURES` (`rollouts.py:28`, mirrored `world_model.py:31`) is the 5
  AI4I telemetry signals only. `crack_proximity()` (`stage.py:126-135`) — which *does* encode `elapsed/total` —
  is deliberately excluded. Feeding it would be leakage; it isn't fed.
- **Why a snapshot can't solve it but a window can (legitimate temporal inference).** The telemetry features are
  functions of `prox` (rpm ↓35%, torque ↑90%, temp-gap collapse across the degrade window — `stage.py:152-159`).
  From one snapshot the model recovers `prox` but not the ETA (`total`), because ETA is **randomised 8–20 min**
  (`config.yaml:7-8`, `rollouts.py:53`) → absolute TTF = `total·(1−prox)` is under-determined. Across the
  6-sample / 30 s window the model observes `d(prox)/dt = 1/total`, recovers `total`, and thus absolute TTF.
  That is exactly the "reads the degradation rate across the window" claim in the card (`:22-26`) and ADR D2
  (`:29-31`). It is real temporal inference, not a leaked target.
- **Why the MAE is so low (and honestly flagged).** The simulator is clean: the degraded-signal swings are large
  (`degraded_rpm_drop_frac 0.35`, `degraded_torque_rise_frac 0.9`, `calibration.py:170-171`) versus small seeded
  noise (rpm ±12, torque ±1.2, `calibration.py:162-165`) → very high SNR → the rate is recoverable to high
  precision. The card (`:42-44`) and ADR D2 explicitly say the 0.067-min figure is a sim number, real telemetry
  will be noisier, and gate any production claim on G-035. That is the honest framing, not overselling.
- **Reproduces on unseen seeds** (my 70–73 run: +97.7%). Not seed-specific.

Verdict on the win: **honest and reproducible.**

## Judgement — causal-deferral honesty

`attribute_cause` (`diagnosis.py:98-158`) is a **real counterfactual over a KNOWN, documented structure** (the
SimWorld SCM in KB_05): it rejects confounders (intrinsic wear + co-occurring `power_dip` → stays `machine_local`,
test `test_world_model.py:85-93`) and attributes a power-dip-driven anomaly to `externally_influenced`
(`:96-103`). The "NOT learned discovery / NOT neuro-symbolic verify, deferred → Stage 17/spike" boundary is stated
in three places (card `:47-51`, ADR D5, the function docstring `:118-122`). This is **not** an overclaimed causal
twin — it is an honest, bounded v1, and G-020 correctly stays PARTIAL/open. `Diagnosis.causal_attribution` is a
defaulted-empty field (`:68`); all existing Stage-6 diagnosis tests pass unchanged → genuinely back-compatible.

## Judgement — `--no-baseline-drop` (D6)

Honest. The de-mock here (`world_model.py`'s `np.random.randn` fallback) is **grep-invisible** to `audit.sh`
(its patterns are `random.uniform|random.choice|Math.random|...`, not `randn`), so removing it cannot move the
counter — same class as the G-047 note. I confirmed there is **no in-lane grep-counted theatre** in the Stage-8
files to remove (the 396 hits are all pre-existing Stage-9/10/11 files: explainability, neural_networks,
robotics/supply-chain heads, frontend `Math.random`). Holding flat at 396 on an additive ML stage is therefore
the honest accounting, not a dodge. It is declared in the task doc, the mechanical audit gaps section, and ADR D6.

## No-regression

`sim_world.py` is **untouched** (not in `git diff --name-only`). Stage-6 slice (`test_slice_intervene`),
Stage-7 RL (`test_intervention_rl`), and Stage-4 predictor (`test_failure_predictor`) all pass (25/25).
`weights_only=True` on `torch.load` (`world_model.py:65`) — no pickle-exec surface.

---

## VERDICT: **PASS**

All seven implementation ACs (AC1–AC7) are independently confirmed with runnable evidence; AC8 is this review.
The TTF win is real, non-leaky, and reproduces on unseen seeds (70–73: +97.7%). The causal-attribution v1 is a
genuine known-SCM counterfactual with an honestly-stated deferral (G-020 → Stage 17/spike, not overclaimed). The
`np.random.randn` theatre is genuinely removed, `ModelUnavailableError` is raised rather than fabricating, and
`torch.load(weights_only=True)` is used. The `--no-baseline-drop` hold at 396 is honest for this grep-invisible
additive ML stage. No regression to the simulator or to Stage 4/6/7.

**Gaps that must be fixed before close:** none.

**Open items (already tracked, no new ledger rows needed):**
- G-020 (learned causal discovery + neuro-symbolic verify) → Stage 17 / research spike — correctly deferred.
- G-035 (re-fit on real telemetry before any production TTF claim) — correctly caveated in card/ADR.
