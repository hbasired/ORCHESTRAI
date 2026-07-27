# Stage 6 (depth-hardening) — Independent Review

**Auditor**: `task-auditor` (independent; did NOT implement Stage 6)
**Date**: 2026-06-14
**Scope**: the 2026-06-14 Stage-6 depth-hardening increment (5/5) — wire the deepened loop end-to-end
(predict → forecast TTF → causal diagnose → SHAP explain → neuro-symbolic VERIFY → intervene) and add
the richer A/B with paired bootstrap 95% CIs.
**ADR under review**: `compliance/decision-logs/2026-06-14_depth_06_slice_integration.md`

## VERDICT: **PASS** (with one disclosed, honest caveat about what "VERIFY gates execution" means in Stage 6)

The loop is genuinely wired end-to-end and additively; the deepened pieces are availability-gated so the
measured A/B is preserved; the bootstrap-CI A/B is correctly implemented and the committed numbers are
internally consistent; the harness reports the sign without asserting a winner. The one substantive
finding is that in **Stage 6 specifically** the VERIFY step is effectively a **no-op gate** (it always
approves) — which the ADR is honest about, but the phrasing "the verifier's value here is the real
per-action precondition/throughput/redundancy gate" slightly overstates it, because two of those three
contracts are explicitly disabled in the Stage-6 plant state. This is a transparency nuance, not theatre,
and the real gate is the Stage-7/Stage-17 concern. Not close-blocking; ledgered for the stage that arms it.

### Verification-environment limitation (disclosed)
The **Bash and PowerShell execution tools were denied** in this session, so I could **not dynamically
re-run** `scripts/run_slice_ab.py` or `pytest`. Verification is **static**: I read the harness, the loop
body, the tests, and the committed `results.json`, and **recomputed the headline deltas/CIs by hand** for
internal consistency. The bootstrap is seeded (`random.Random(seed=6)`, 5000 resamples) and the arms are
CRN-paired and deterministic per seed, so the numbers are reproducible by construction. A run-capable
session should execute the two commands to mechanically confirm.

---

## Claim 1 — the deepened pipeline is wired into the live loop, additively, gated

| Item | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| Pipeline order in `run_slice_step` | predict → forecast TTF → diagnose+causal → explain → VERIFY → intervene | **YES** | `slice_runner.py::run_slice_step` (L120-234): telemetry → window buffer → `world_model.predict_ttf` (L164-169) → `predictor.predict_failure` (L170) → `diagnose(...)` (carries causal attribution) (L188) → `decide_intervention` (L194) → `explainer.explain` SHAP (L199-208) → `verify(...)` (L212-219) → `start_maintenance` (L221-222). Order matches the claim. |
| TTF + SHAP are ADDITIVE (don't change execution) | yes | **YES** | `ttf_forecast` only attaches to `pred_payload` (L181-182); `explanation` only attaches to `iv_payload` (L228-229). Neither feeds the `execute` decision. Both are best-effort, exception-swallowed, availability-gated (`is_available()`), so absence → no effect. The A/B is preserved. |
| VERIFY GATES execution | maintenance only fires if approved | **YES (mechanically true)** | L221: `if execute and decision.kind == PREVENTIVE_MAINTENANCE and approved: executed = stage.start_maintenance()`. `approved` comes from `verify(...)`. The gate is genuinely in the execution path — a `False` would block the maintenance. |
| Verifier PlantState uses available_crew = n_stages | yes (so single-machine maintenance approves; A/B preserved) | **YES — and MORE (see finding)** | `_build_plant_state` (L99-117) sets `available_crew=n`, **AND** `throughput_floor_frac=0.0`, **AND** `max_concurrent_critical_offline=n`. So not just crew — the throughput-floor and SIL-redundancy contracts are **also** relaxed to no-ops in Stage 6. |

### Finding F-1 (non-blocking, transparency): VERIFY is a no-op gate in Stage 6
With the Stage-6 `_build_plant_state` (`available_crew=n`, `throughput_floor_frac=0.0`,
`max_concurrent_critical_offline=n`) and the loop calling `verify` with a **single** `PlannedAction` per
stage, after broken/maintenance stages are already skipped upstream (L154), **every constraint passes by
construction**:
- `target_validity` — sid always present → pass
- `maintenance_precondition` — stage is online (broken/maintenance skipped at L154) → pass
- `crew_capacity` — 1 ≤ n → pass
- `throughput_floor` — floor 0.0 → always pass
- `critical_redundancy` — max=n → always pass
- `act_on_risk_only` — SOFT only

So in Stage 6 the verifier **cannot reject anything** — it is a provenance-attaching no-op gate. The ADR
(D2) is honest that it "APPROVES the normal single-machine maintenance … execution, and therefore the
measured numbers, are unchanged," and the alternatives-rejected section openly defers crew contention to
Stage 7. **This is honest deferral, not theatre.** The mild overstatement is calling it "the real
per-action precondition/throughput/redundancy gate, now in the live path" when two of those three
contracts are disabled here. The *real* gate value lands when Stage 7 (crew contention) / Stage 17
(functional safety) supply a non-relaxed `PlantState`. The verifier code itself (audited under Stage 8C)
**is** a genuine rejecting engine — `test_plan_verifier.py` proves it rejects crew/throughput/redundancy/
precondition violations under a non-relaxed state. Ledgered to the stage that arms it (see below).

## Claim 2 — richer A/B with paired bootstrap 95% CIs

| Item | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| unplanned downtime −182 min, CI [93,274], significant | mean 182.41, CI [93.36, 273.96], sig | **YES (consistent)** | `results.json`: off mean 510.82, on mean 328.41 → delta 182.41. `measured_delta_ci95.unplanned_downtime_min` = mean 182.42, ci95 [93.36, 273.96], significant=true (CI excludes 0). |
| crack breakdowns −4.2, CI [3,5], significant | mean 4.2, CI [3,5] | **YES** | off crack_breakdowns mean 4.6, on 0.4 → 4.2. ci95 [3,5], significant=true. |
| throughput −0.05, CI [−0.22,0.12], NOT significant | mean −0.05, CI [−0.22,0.12] | **YES** | on 7.37 − off 7.42 = −0.05; ci95 [−0.22, 0.12] spans 0 → significant=false. Honest "no throughput cost." |
| Bootstrap is seeded / reproducible | 5000 resamples, CRN-paired | **YES** | `_paired_bootstrap_ci` uses `random.Random(seed=6)`, 5000 resamples over per-seed OFF−ON diffs; `significant = lo>0 or hi<0`. Arms are CRN-paired (same seed, same crack campaign, differ only by SliceLoop). Deterministic. |
| Harness reports sign, does NOT assert a winner | honesty rule | **YES** | `run_slice_ab.py` docstring + `measured_delta.note` ("reported as measured, not asserted"); `test_slice_ab.py` explicitly does NOT assert ON beats OFF, only that fields are finite and present. Determinism test (`test_arms_are_deterministic_per_seed`) confirms reproducibility. |

**Per-seed sanity (from `results.json` pairs):** seed 42 unplanned 397.59→271.71, 43 606.58→284.79,
44 406.64→249.98, 45 638.80→360.23, 46 504.50→475.32 — every seed shows a reduction; crack_breakdowns
drop from {3,5,5,5,5} to {1,0,0,0,1}. The effect is consistent across seeds, supporting the significant
CI. The throughput cost is genuinely negligible (planned-maintenance downtime is small relative to
avoided crack-breakdown secondary damage at 2.5× MTTR). Numbers are coherent, not massaged.

## Theatre / bypass / baseline

- **Theatre grep (changed files):** `slice_runner.py`, `run_slice_ab.py` — **zero** matches for
  `random.uniform|random.choice|random.randint|Math.random|generateMockState|_get_demo_*|RESPONSES = {|MODELS = [`.
  `_paired_bootstrap_ci` uses stdlib `random.Random` for **resampling** (a legitimate statistical use, not
  a fabricated model output), and it lives in `backend/scripts/` driving a seeded experiment — not a
  backend service fallback. No theatre.
- **Audit baseline:** `.audit-baseline` = 364, held (additive wiring; ADR D4). The change is integration
  glue + a bootstrap function — zero new counted patterns. Structurally additive (confirmed by grep; could
  not run `audit.sh` due to tool denial, but the invariant holds by construction).
- **Bypass:** none. No `--no-verify`/`--force`. No LLM-direct actuator (execution routes through the
  deterministic policy + the symbolic verifier gate, then `Stage.start_maintenance`, a sim API). No
  hard-rule violation.
- **Honest-unavailable contract preserved:** `SliceLoop._run` / `LiveSliceRunner._run` still raise/stop
  honestly if the Stage-4 brain is absent; world-model and explainer load best-effort and return None
  rather than fabricate.

## Gaps to fix before close
**None blocking.** F-1 (VERIFY is a no-op gate in Stage 6 because throughput/redundancy contracts are
relaxed) is honestly deferred — the real gate is armed by Stage 7 (crew contention) / Stage 17 (functional
safety). Appended to `OPEN_GAPS_LEDGER.md` so the arming stage wires a non-relaxed `PlantState` and adds a
test that the live loop can actually REJECT a plan. Recommend the ADR/explainer soften "the real
…throughput/redundancy gate, now in the live path" to "the gate is now in the live path; its rejecting
contracts are exercised from Stage 7/17 when crew contention/SIL constraints bind" — wording only.

## Honesty assessment
**Strong.** The integration is real (the deepened pieces genuinely run and attach provenance), the A/B is
measured not asserted, the bootstrap is correct and seeded, and the one place where a claim runs slightly
ahead of reality (VERIFY "gating" in Stage 6) is itself disclosed in the ADR. No inflated numbers, no
faked gate, no leakage. PASS.
