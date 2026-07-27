# Independent review — Stage 6 (Vertical Slice v0: predict → diagnose → intervene)

**Date**: 2026-06-12
**Reviewer**: `task-auditor` (fresh independent agent — did NOT implement Stage 6)
**Task doc**: `tasks/STAGE_06_vertical_slice_predict_diagnose.md`
**Verdict**: **PASS-WITH-GAPS** (no fabrication found; all stage tests pass; baseline 396 < 402; four disclosed/forward-targeted gaps + one process gap listed at the bottom)

---

## 1. Independence statement

I am a separate agent session invoked solely to audit Stage 6. I wrote none of the Stage 6 code, tests,
KB updates, or eval artifacts. I re-ran the stage's tests, the mechanical audit, and the A/B harness on a
**seed the implementer never used (77)** as an anti-cherry-pick check. I edited exactly one file — this one.
(To keep the repo unmutated I invoked the A/B `run_experiment()` directly rather than the CLI, because the
CLI's `write_reports()` would have overwritten the implementer's committed `results.json` artifact; the code
path executed is identical up to report writing — `backend/scripts/run_slice_ab.py:111-153`.)

## 2. What I ran (real output)

### 2.1 Stage 6 test suite

```
cd backend && python -m pytest tests/test_diagnosis.py tests/test_slice_events.py \
  tests/test_slice_predict_live.py tests/test_slice_intervene.py tests/test_slice_ab.py -q
→ 32 passed, 2 warnings in 12.42s
```

### 2.2 Anti-cherry-pick A/B — fresh seed 77, 4 sim-hours (implementer used 42/43/44 × 8 h)

```
seeds=[77] sim_hours=4.0
OFF: unplanned=195.78 min, crack_breakdowns=3, total=195.78 min, thr=9.50 u/h
ON : unplanned=199.15 min, crack_breakdowns=0, planned_maint=3, total=236.65 min, thr=7.25 u/h
MEASURED delta (OFF−ON): unplanned_downtime −3.37 min, total_downtime −40.87 min, throughput −2.25 u/h
```

**This single-seed short-window run came out AGAINST the loop on the downtime metrics** (while still
preventing **all 3** crack breakdowns, 3 → 0). The harness reported the negative delta verbatim — no clamp,
no assert, no massage. That is the strongest possible evidence the harness is honest, and simultaneously
evidence that the downtime delta is high-variance (see Gap 3). The robust, causally-attributable metric is
crack-breakdowns-prevented, which held at 100% on my fresh seed.

### 2.3 Mechanical audit

```
bash scripts/audit.sh
→ TOTAL 396 — Baseline (from .audit-baseline): 402 — "OK: count decreased from 402 to 396."
```

`.audit-baseline` still reads 402 (correct — it is rewritten only by `close-task.sh`).

### 2.4 Pre-existing-failure claim check (G-044)

```
cd backend && python -m pytest tests/test_api.py -q   → 21 failed, 3 passed in 3.27s
```

Exactly the claimed 21. Failure modes are `assert 503 == ...` / `KeyError` across Decision / Prediction /
Explainability / Optimization / Alert endpoint classes — i.e., app subsystems unavailable without the compose
stack — and span endpoint families Stage 6 never touched. I did **not** re-run the `test_websocket_smoke.py`
hang (per scope); plausibility judged from the diff in §5(c).

## 3. Findings per acceptance criterion

| AC | Claimed | Independently confirmed? | Evidence |
|---|---|---|---|
| AC1 live predict | [x] | **Yes (component level)** — with a wiring caveat (Gap 2) | `backend/simulation/entities/stage.py:137-178` (`telemetry()` derived from real state: status, `crack_proximity()` from the actual crack schedule at :126-135, `tool_wear_accum_min` accumulated by real production at :214, queue load); real XGBoost brain at `backend/ml/failure_predictor.py:124-130`; honest `ModelUnavailableError` (no fallback) at `failure_predictor.py:29,55,65,68` and `backend/services/slice_runner.py:176-180,233-238`; Redis→WS fan-out via `build_slice_envelope` + already-enveloped pass-through `backend/services/ws_broker.py:56-72,176-179`. Tests passed (§2.1), incl. `test_slice_loop_emits_predictions_on_live_world` and `test_brain_scores_degraded_higher_than_healthy` (real model, real ordering assert, `tests/test_slice_predict_live.py:60-99`). |
| AC2 diagnose v0 | [x] | **Yes** | `backend/services/diagnosis.py` — pure function, zero I/O, zero randomness, AI4I-threshold rules (:24-29), evidence trail on every hypothesis (:42-47), honest `NO_FAULT_FOUND` when the model flags risk but no rule fires (:212-226), deterministic tie-break (:228). **9 test cases** (≥6 required) incl. not-at-risk, ambiguous no-rule, external-attribution, and determinism (`tests/test_diagnosis.py:45-106`). |
| AC3 intervene v0 | [x] | **Partial — Gap 1 (decision_logs)** | Coordinator delegates to the shared policy: `backend/agents/embodied_agent.py:378-392` → `backend/services/intervention_policy.py:47-112` (same object the A/B uses — delegation equality asserted in `tests/test_slice_intervene.py:67-71`). Execution via `Stage.start_maintenance` (`stage.py:95-113`) — refuses when broken/in-maintenance (invariant-safe), cancels the crack, costs `0.5 × mttr`. End-to-end crack prevention asserted (`test_slice_intervene.py:114-137`). **But "persisted to decision_logs" is NOT implemented**: grep shows no writer anywhere — only the Stage-1 migration (`backend/alembic/versions/0001_init.py:286`) and comments (`slice_runner.py:18`, `intervention_policy.py:23`). Provenance is in-memory `SliceTrail` + WS envelopes only. |
| AC4 measured A/B | [x] | **Yes — with methodology caveat (Gap 3)** | `backend/scripts/run_slice_ab.py` reports, never asserts direction (:141-152 computes delta; no conditional on sign anywhere; confirmed by my seed-77 negative-delta run, §2.2). `results.json` numbers match the Hand-off and KB_23 §measured row exactly: 470.27 → 268.83 unplanned (−42.8%), crack breakdowns 4.33 → 0.33 (−92.3%), total −32.1%, throughput −0.04 (`backend/training/evals/stage06/results.json:10-22,133-138`; `knowledge-base/KB_23_Evals_and_Benchmarks.md:127`). Smoke test deliberately does not assert sign (`tests/test_slice_ab.py:49-52`) and skips honestly without the brain (:20). |
| AC5 event surface | [x] | **Yes** | Canonical KB_04-family envelope (`ws_broker.py:56-72`); broker fans out enveloped slice events as-is (:176-179) while the legacy incident path still wraps (:180-185) — both asserted with a fake-Redis-free broker drive (`tests/test_slice_events.py:29-83`). Four slice types gated by an allowlist with a hard `ValueError` on unknown types (:64-65). |
| AC6 baseline ↓ | [x] | **Yes** | 396 < 402 (§2.3). The 6 removed fabrication lines are real: `git diff backend/agents/manufacturing_agent.py` shows `random.randint/uniform/choice/random` init + `_simulate_production` drift deleted, replaced by `_sync_from_world` reading the actual `SimWorld` (every field traced to sim state or calibration, `manufacturing_agent.py:203-227`). Zero `random|mock|demo` matches in the added lines of the modified backend files. Junk dir `backend;C\` confirmed deleted. |
| AC7 independent audit | [ ] | **This document.** | — |
| AC8 KB updated | [x] | **Yes — substantive, not cosmetic** | Real diffs: KB_01 +27, KB_05 +26, KB_23 +25 (incl. the measured row at :127), KB_25 +15 (predict/diagnose/intervene status), KB_TASK_LOG +136. Stage explainer exists: `research/stage-explainers/STAGE_06/index.html`. |

## 4. Theatrical scan (adversarial)

- **Fabricated-prediction path when the brain is absent: NONE.** `FailurePredictor._load` raises
  `ModelUnavailableError` on missing meta/weights/library (`failure_predictor.py:53-82`); `SliceLoop._run`
  raises before its first sample (`slice_runner.py:176-180`); `LiveSliceRunner` logs and stops — does not run
  (`slice_runner.py:233-238`); the A/B CLI refuses with exit 2 and prints "no fabricated arm"
  (`run_slice_ab.py:191-194`); tests skip with an explicit honest-skip reason (`test_slice_ab.py:19-20`).
- **A/B delta massage: NONE.** No sign assertion, clamp, retry-until-favorable, or seed filtering in
  `run_slice_ab.py` or `test_slice_ab.py`. My adversarial seed produced an unfavorable delta and the code
  reported it (§2.2).
- **Telemetry tuned to flatter the model?** Judged **honest but structurally favorable** (see §5 and Gap 4).
  The drift constants (`calibration.py:170-173`: rpm −35%, torque +90%, wear +190 min, temp-gap −6 K at full
  proximity) deterministically drive a degraded machine into **all four** AI4I failure regimes the brain was
  trained on (`diagnosis.py:24-29`: TWF 200 min, HDF 8.6 K/1380 rpm, OSF 11,000 minNm, PWF power band). The
  mapping is openly documented as a design choice (`calibration.py:143-149`, `stage.py:137-145`, KB_05) and
  the telemetry inputs themselves (crack schedule, accumulated wear, queue load, status) are real sim state —
  this is not `random.uniform` theatre. But it does mean the ~92% prevention rate is near-guaranteed by
  construction: the A/B validates the **loop machinery and the intervention economics** (planned 0.5×mttr vs
  crack-induced 2.5×exponential(mttr), `calibration.py:114-121`), not the model's predictive skill on
  independent data (that was Stage 4's held-out AI4I eval; re-fit on real telemetry remains G-035).
- **Tests honest:** all 32 assert real behaviour (state transitions, ordering, prevention counts, envelope
  shapes, determinism, delegation equality). No no-op/always-pass tests found.
- **Bypass:** no `--no-verify`, no `--no-baseline-drop`, no `.audit-baseline` edit (still 402), no actuator
  paths outside `SimWorld` (the only "actuator" is `Stage.start_maintenance` inside SimPy — Stage-17 wrapper
  legitimately not required per the task doc), no classical crypto, no paid services, no committed keys.

## 5. Deviations judged

**(a) Telemetry + maintenance on the `Stage` entity instead of `sim_world.py`** (task-doc Files-to-MODIFY
table said `sim_world.py`; `sim_world.py` is in fact unmodified). **Acceptable — correct altitude.**
Per-machine telemetry and per-machine maintenance are per-machine concerns; `SimWorld` already exposes
`world.stages`, which is exactly how the slice consumes them (`slice_runner.py:92-98`). The Files-to-MODIFY
table is guidance, not an AC. Not a gap.

**(b) AC3 "persisted to decision_logs" satisfied via SliceTrail + envelopes, not a Postgres write.**
**Real gap — minor severity, correctly disclosed, target Stage 11.** The AC sentence is explicit and is not
met as written: no `decision_logs` writer exists anywhere in the slice path (only the Stage-1 table DDL).
The justification (the sim-closed-loop path has no DB session; durable runtime persistence is Stage 11's
LangGraph/Postgres work) is technically sound, and provenance is not lost (in-memory trail + enveloped WS
events carry decision + rationale + full diagnosis). But in-memory provenance dies with the process — this
must be ledgered to Stage 11, not silently absorbed. Demoting the AC from "met" to "met-except-persistence"
is why this review is PASS-WITH-GAPS rather than PASS.

**(c) test_api.py 21 failures + websocket hang claimed pre-existing (G-044).** **Plausible — corroborated.**
(i) My re-run reproduced exactly 21 failures; (ii) the failures are 503/KeyError infra-unavailability across
endpoint families (decisions, predictions, explainability, optimization, alerts) that Stage 6's diff never
touches; (iii) the Stage 6 diff to the only API-adjacent surfaces is additive — `ws_broker.py` adds an
envelope builder + a pass-through branch while keeping the legacy path (regression-tested,
`test_slice_events.py:62-72`), and `ManufacturingAgent.__init__` adds an optional `sim_world=None` parameter
(backward-compatible signature). One nuance: the de-mock means an agent constructed without a handle now
starts EMPTY instead of with 10 fabricated stages, which *could* flip a test that asserted fabricated state —
but the observed failures are 503s (requests never reached agent state), consistent with the
missing-compose-stack explanation and the implementer's git-stash verification claim.

## 6. Additional findings (not in the claimed-deviation list)

- **A/B arms are not common-random-numbers paired.** Each `Stage` holds ONE rng
  (`sim_world.py:89-90`) shared by cycle-time/defect/MTBF/MTTR draws AND the four `telemetry()` noise draws
  (`stage.py:161-164`). The ON arm samples telemetry every 30 sim-s × 10 stages, consuming that stream, so
  every natural-failure draw downstream diverges from the OFF arm — the docstring's "differs ONLY by the
  SliceLoop process" (`run_slice_ab.py:18-19`) is true of the code but not of the noise pairing. Consequence:
  the downtime delta carries arm-divergence variance on top of the intervention effect (my seed-77/4 h run:
  all 3 cracks prevented yet unplanned downtime −3.37 min *worse*). The 3-seed × 8 h headline (−42.8%) is
  honestly measured but variance-unquantified. Fix (Stage 7, where this harness becomes the RL eval env):
  dedicated telemetry-noise rng stream per stage + report per-seed spread/CI alongside the mean.
- **The live app does not run the slice today.** `LiveSliceRunner` is built and tested but unwired
  (disclosed: Hand-off "built, unwired"), and `EmbodiedCoordinator` constructs `ManufacturingAgent()` without
  a `sim_world` handle (`embodied_agent.py:100`), so in the running app the de-mocked head reports honest-empty
  rather than observing the live world. Honest (no fabrication; warning logged at
  `manufacturing_agent.py:115-117`) but the Hand-off line "observes the REAL SimWorld" holds only when a
  handle is passed (tests/harness). Wiring belongs to Stage 11.
- **Owed pre-requisite audits were not run at stage open.** The task doc's own pre-req section requires, at
  stage open: independent CTO #1 re-run (G-031) and Stage 3 independent re-audit (G-001). Both checkboxes are
  unchecked, both ledger rows are still OPEN (`OPEN_GAPS_LEDGER.md:27,57`), `CTO_1_review.md` is still the
  2026-05-31 interim self-review, and `STAGE_03_independent_review.md` is unchanged since 2026-05-31 (its own
  text says a full re-audit "is owed"). This is a process debt the stage carried in writing and then did not
  pay. It does not taint the Stage 6 code, but the main session must either run both before `close-task.sh 6`
  or explicitly re-target them with justification in KB_TASK_LOG.

## 7. VERDICT

**PASS-WITH-GAPS.**

The slice is real: real sim-state telemetry, the real Stage-4 XGBoost brain with honest refusal when absent,
a pure deterministic diagnoser with evidence trails, an invariant-safe sim-only intervention, an A/B harness
that demonstrably reports unfavorable results unmassaged, 32/32 passing substantive tests, audit 396 < 402
with the removed fabrications verified in the diff, and substantive KB/explainer updates. No theatre, no
bypass, no hard-rule violation found.

Gaps (fix-or-ledger before `close-task.sh 6`; the main session owns ledgering per protocol):

| # | Gap | Severity | Disposition / target |
|---|---|---|---|
| 1 | AC3's "persisted to `decision_logs`" not implemented — provenance is in-memory `SliceTrail` + WS envelopes only; no DB writer exists in the slice path | minor-medium | Ledger → **Stage 11** (LangGraph runtime + Postgres persistence); wire the slice decision write there |
| 2 | Live-app wiring absent: `LiveSliceRunner` unwired; `ManufacturingAgent` constructed without `sim_world` (`embodied_agent.py:100`) → running app emits no slice events and the de-mocked head is honest-empty | minor (disclosed in Hand-off) | Ledger → **Stage 11** |
| 3 | A/B lacks common-random-numbers pairing (telemetry noise consumes the shared per-stage rng) and reports no variance/CI; downtime delta is noise-sensitive (verified: seed 77/4 h negative delta despite 3/3 cracks prevented) — crack-breakdowns-prevented is the robust headline, downtime −42.8% needs error bars | medium (methodological, not honesty) | Ledger → **Stage 7** (harness becomes the RL training/eval env; add dedicated noise stream + per-seed spread) |
| 4 | Structural favorability: drift calibration guarantees degraded machines enter the brain's trained AI4I regimes, so prevention-rate is near-assured by construction; A/B validates loop machinery + intervention economics (2.5×/0.5× constants), not model skill on independent data | note (documented design) | Already covered by **G-035** (re-fit on real telemetry) + Stage 14 calibration retune; ensure pitch/KB claims framed as "sim-measured under calibrated assumptions" |
| 5 | Owed pre-req audits not run at stage open: G-031 (independent CTO #1) and G-001 (Stage 3 re-audit) still OPEN with unchecked task-doc boxes | medium (process) | **Run both before `close-task.sh 6`** or explicitly re-target with justification in KB_TASK_LOG |

Nothing here requires reworking the Stage 6 implementation itself. Gaps 1–4 are honest deferrals/notes that
must land in `audits/OPEN_GAPS_LEDGER.md` with the stated targets; Gap 5 is an open obligation of this very
stage's pre-req section and is the one item I'd hold close hostage to.

*Reviewed files: task doc; `services/diagnosis.py`, `services/intervention_policy.py`, `services/slice_runner.py`,
`services/ws_broker.py`; `simulation/entities/stage.py`, `simulation/calibration.py`, `simulation/sim_world.py`
(rng wiring); `agents/manufacturing_agent.py` (+diff), `agents/embodied_agent.py`; `ml/failure_predictor.py`
(availability/raise paths); `scripts/run_slice_ab.py`; all five Stage 6 test files; `training/evals/stage06/results.json`;
KB diffs (stat + measured row); `audits/OPEN_GAPS_LEDGER.md` (G-001/G-031 rows); `audits/STAGE_03_independent_review.md` (head).*
