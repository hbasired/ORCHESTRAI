# Stage 8 (depth-hardening) — Independent Review

**Auditor**: `task-auditor` (independent; did NOT implement Stage 8)
**Date**: 2026-06-14
**Scope**: the 2026-06-14 Stage-8 depth-hardening increment — Transformer RUL on real C-MAPSS FD001,
learned causal discovery (PC), neuro-symbolic plan verifier.
**ADR under review**: `compliance/decision-logs/2026-06-14_depth_08_world_model_causal_verify.md`

## VERDICT: **PASS**

All three claims are independently supported by static verification (code + committed artifacts +
dataset-integrity + by-hand recomputation of the headline numbers). No theatre, no fabrication, no
train/test leakage, no overclaim found. One methodological nit (val-split is window-level, not strictly
engine-level) is acknowledged in the trainer's own comment and does not touch the test evaluation.

### Verification-environment limitation (disclosed, not hidden)
Both the **Bash and PowerShell execution tools were denied** in this audit session, so I could **not
dynamically re-run** `eval_cmapss.py`, `discover_and_validate(...)`, `pytest`, or `scripts/audit.sh`.
My verification is therefore **static**: I read every source/test/artifact file, confirmed the cached
dataset is the genuine unmodified NASA FD001 (ground-truth RUL values match the canonical benchmark),
and **recomputed the headline metrics by hand** from the committed reports to confirm internal
consistency. Where a number depends on a fresh run I confirmed it is *reproducible by construction*
(seeded, single-pass, leakage-free) rather than asserting I re-observed it. This is flagged so the
PASS is not mistaken for a dynamic re-run; a follow-up run-capable session should execute the four
commands to close the loop (mechanical confirmation only — the design is sound).

---

## Claim 1 — Transformer RUL on real C-MAPSS FD001

| Item | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| Real FD001 dataset (not fabricated) | 100 train / 100 test engines, real benchmark | **YES** | `data/datasets/cmapss/{train,test,RUL}_FD001.txt` cached. `RUL_FD001.txt` = the canonical FD001 ground truth (112, 98, 69, 82, 91, … 20 — exactly the published values). Train/test rows have the correct 26-col layout (unit, cycle, 3 op, 21 sensors) and the well-known constant sensors (s1=518.67, s5=14.62, s6=21.61, s10=1.30, s16=0.03, s18=2388, s19=100). Unmodified NASA data. |
| Test RMSE 13.80 / NASA 372 | 13.803 / 372.3 | **YES (consistent)** | `models/rul_transformer_cmapss.metrics.json`: `test_rmse 13.803`, `test_nasa_score 372.3`. The independent re-eval path `eval_cmapss.py` recomputes through the public inference glue (`RULTransformer.predict_rul`), un-normalising `Xte` and re-predicting — an honest cross-check, not a trust-the-trainer printout. (Could not execute due to tool denial; logic is correct and single-pass.) |
| Beats CNN(18.45)/LSTM(16.14), +66% vs naive | yes | **YES** | metrics `naive_baseline_test_rmse 40.548`, `improvement_vs_baseline_pct 66.0`. 13.80 < 16.14 < 18.45. Literature numbers are labeled `cited_not_reproduced`. Model card claim disciplined: "beats the classic CNN and LSTM … competitive with the DCNN/Transformer SOTA … not claimed to beat it." |
| No train/test leakage | train-only scaler, single test eval, no test tuning | **YES** | `cmapss_data.load_fd001`: `feat_min/feat_max` fit on **train sensors only** (lines 128-130); test windows normalised with the same train scaler. `train_cmapss.py`: best-checkpoint selected on a held-out **val** slice; the official 100 test engines are touched **once** after `net.load_state_dict(best_state)` (lines 127-133). No reference to `Xte`/`yte` inside the training loop. **No leakage.** |
| Standard preprocessing | piecewise RUL cap 125, 14 sensors, window 30 | **YES** | `RUL_CAP=125.0`, `_INFORMATIVE_SENSORS` = the standard 14 FD001 channels (7 constant sensors + 3 near-constant op-settings dropped), window 30. `_piecewise_rul` clips remaining cycles at the cap. Test label = `min(RUL_FD001[i], cap)`. All canonical. |
| Honest-unavailable + weights_only load | raises ModelUnavailableError, weights_only=True | **YES** | `rul_transformer.py::_load` raises `ModelUnavailableError` if torch or weights absent (lines 104-109); `torch.load(..., weights_only=True)` (line 110). `predict_rul` never fabricates. `test_honest_unavailable` asserts this. |

**Minor methodological note (not a gap):** `train_cmapss.py` performs the 85/15 val split at the
**window level on the engine-ordered array** (`Xtr_all[:cut]` / `[cut:]`), not strictly engine-level —
the trainer's own comment (lines 82-84) discloses this ("approximated here at the window level … a
tail fraction ≈ the last engines"). One engine's windows can straddle the cut. This affects only
**model selection**, never the test metric (the test set is the disjoint official 100 engines). Honest
and harmless; noted for completeness.

## Claim 2 — Learned causal discovery (PC) recovers the proximity hub

| Item | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| TRUE_EDGES match the simulator's equations | prox→{rpm,torque,wear,air,process}, load→{torque,process} | **YES** | Cross-checked against `simulation/entities/stage.py::telemetry`: `prox` drives rpm (L152), torque (L153), wear (L154), process (L158), air (L159) = 5 edges; `load` drives torque (L153, `1+0.15*load`) and process (L158, `+1.5*load`) = 2 edges. **All 7 TRUE_EDGES are the genuine structural equations — not cherry-picked.** |
| Skeleton F1 0.75 | tp6/fp3/fn1, P0.667/R0.857/F1 0.75 | **YES (recomputed by hand)** | From `causal_discovery.json`: recovered ∩ true = {prox-rpm, prox-wear, load-torque, load-process, prox-torque, prox-air} = **6 TP**; recovered−true = {prox-load, rpm-wear, load-wear} = **3 FP**; true−recovered = {prox-process} = **1 FN**. P=6/9=0.667, R=6/7=0.857, F1=0.75. **Arithmetic checks out exactly.** |
| 4/5 hub edges, proximity = max-degree node | hub_n 4, prox degree 5 (max) | **YES** | `proximity_hub_recovered = [rpm, torque, wear, air]` (process missed); `node_degrees`: crack_proximity=5 (max), load=4. `proximity_is_max_degree_hub: true`. Consistent with the recovered skeleton. |
| Honest limitations | temp edges near noise floor; linear Fisher-Z | **HONEST, not an excuse** | The temperature signal is real: `degraded_temp_gap_collapse_k` × prox × 0.5 plus seeded noise — a ~few-K effect against sensor noise, genuinely low-SNR. The PC orientations are partly wrong (e.g. `process_temp_k → load` reverses ground truth) but the module **only claims the SKELETON F1 + HUB property** as the robust result and explicitly does not claim orientation accuracy. The stated limits are accurate, not face-saving. |
| No over-claim of "learned" in diagnosis | additive support only | **YES** | `services/diagnosis.py::attribute_cause` still labels itself "do-operator over **known** SimWorld SCM … now **corroborated by** learned PC discovery"; `_discovery_support()` reads the persisted report and returns `{available: False, …}` honestly if absent. Additive, back-compatible, no fabrication. |

## Claim 3 — Neuro-symbolic plan verifier (VERIFY step)

| Item | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| Real symbolic constraints | crew capacity, maintenance precondition, throughput floor, SIL redundancy | **YES** | `plan_verifier.py`: six pure-predicate constraints (`_c_target_validity`, `_c_maintenance_precondition`, `_c_crew_capacity`, `_c_throughput_floor`, `_c_critical_redundancy`, `_c_act_on_risk_only`); HARD violations reject, SOFT warn. Logic is correct and deterministic. |
| Rejects unsafe plans | yes | **YES** | `test_plan_verifier.py` genuinely exercises rejection: crew over-capacity, broken-machine precondition, throughput-floor breach (down 3 of 5 → reject), two-critical-offline (SIL). These are real assertions on the reject path, not no-ops. |
| Framing not overclaimed | "symbolic half" of neuro-symbolic | **YES — honest** | Docstring explicitly: "the **symbolic half** … no LLM, no randomness, no learning here … not a full SMT/temporal-logic engine (a future deepening)." The neural proposer is the existing stack; this is the disposer. No overclaim of a learned verifier. |

## Theatre / bypass / baseline

- **Theatre grep (new files):** `rul_transformer.py`, `causal_discovery.py`, `plan_verifier.py`,
  `cmapss_data.py`, `train_cmapss.py`, `eval_cmapss.py` — **zero** matches for
  `random.uniform|random.choice|random.randint|Math.random|generateMockState|_get_demo_*|RESPONSES = {|MODELS = [`.
  (`causal_discovery.py` uses `np.random.default_rng(...).uniform(...)` for legit seed/eta sampling — the
  audit greps the **stdlib `random.` module**, not numpy `rng.`, so this is correctly not flagged; and
  it is simulation-data collection, not a fabricated model output.)
- **Audit baseline:** `.audit-baseline` = 364. The increment is **purely additive**: training/test files
  are whitelisted by `scripts/audit.sh` (`backend/training/`, `backend/tests/`), and the new non-training
  source files add zero counted patterns. The TOTAL holding at 364 is therefore **structurally guaranteed
  by inspection** (I could not run `audit.sh` — bash denied — but the invariant holds by construction).
  `--no-baseline-drop` is justified for an additive deepening (ADR D5).
- **Bypass:** none. No `--no-verify`, no `--force`, no hard-rule violation. Free/OSS deps
  (causal-learn, torch CPU). No LLM-direct actuator path (verifier is read-only; no actuator wired).

## Gaps to fix before close
**None blocking.** The only items are honestly-deferred and already ledgered (G-035 real-fleet
re-discovery). The val-split window-level approximation is a documented non-issue.

## Honesty assessment
**Strong.** This is the opposite of theatre: a real public benchmark, a real architecture, a leakage-free
protocol, a learned discovery whose limitations are stated rather than hidden, and a verifier that is
explicitly the "symbolic half" — no number is inflated and every claim has a check behind it. The model
card and ADR practice disciplined claim language ("beats CNN/LSTM, competitive with SOTA, not claimed to
beat it"). PASS.
