# CTO Checkpoint #1 — INDEPENDENT Review (pays gap G-031)

**Date**: 2026-06-12
**Reviewer**: fresh `cto-reviewer` agent — did NOT implement any stage, the 2026-05-31 interim review, the
Strategic Product Reset, or any audit verified below. Read-only; this file is my only write.
**Verifies/refutes**: `audits/CTO_1_review.md` (2026-05-31 interim SELF-review by the implementing agent,
explicitly caveated) + `audits/CTO_1_remediation_map.json`.
**Scope drift acknowledged**: the interim covered Stages 0–3; three more stages (4, 5, 6) plus the 2026-06-11
Strategic Product Reset have closed since. I judge the interim findings both *as written* (were they honest and
correct on 2026-05-31?) and *as of today* (do they still hold?). Checkpoint #2 fires at Stage 10.5.

---

## 1. Independence statement & interim-review verification

I re-ran the mechanical audit and the Stage 6 core test suites myself (real output, §1.1), recomputed the A/B
arithmetic from the committed artifact, spot-checked one code claim end-to-end, and grep-verified two
remediation claims in the scripts and hooks. Verdict per interim finding follows in §1.2.

### 1.1 What I ran (real output, this session)

```
bash scripts/audit.sh
→ TOTAL 396 — Baseline (from .audit-baseline): 402 — "OK: count decreased from 402 to 396."
  (matches audits/STAGE_06_audit.md and both independent stage reviews)

cd backend && python -m pytest tests/test_diagnosis.py tests/test_slice_intervene.py -q
→ 18 passed, 1 warning in 2.90s
  (warning = pre-existing pytest-asyncio fixture deprecation; unrelated)
```

**Spot-check (one code claim end-to-end): the Stage 6 measured A/B.** Recomputed every headline number in
`backend/training/evals/stage06/results.json` from its own per-seed pairs — all reproduce exactly:
unplanned downtime mean (397.59+606.58+406.64)/3 = **470.27** OFF vs (271.71+284.79+249.98)/3 = **268.83** ON
(−42.8%); crack breakdowns 13→1 across 3 seeds = mean 4.33→0.33 (**−92.3%**); total downtime −32.1%;
throughput 6.96→6.92 (−0.04, honestly reported as flat). The JSON carries a self-describing note —
*"reported as measured, not asserted"* — and `backend/services/slice_runner.py` matches the claimed
architecture: one shared `run_slice_step` body (`slice_runner.py:74-140`), honest
`ModelUnavailableError` fail-fast in BOTH entry points (`:176-180` SliceLoop raises; `:233-238`
LiveSliceRunner logs and refuses to run — no fabricated arm anywhere). Per-seed deltas are wide
(+125.9 / +321.8 / +156.7 min unplanned), corroborating the independent auditor's variance finding (G-046).
One drift found: the docstring at `slice_runner.py:18-19` claims an *"optional `decision_logs` writer"* that
does not exist in the code — consistent with, and another face of, G-045 (see §3).

### 1.2 Verdict on each interim finding

| Interim finding (CTO_1_review.md) | Verdict | Evidence |
|---|---|---|
| **§1 Executive verdict**: "on-track architecturally; high execution risk; spec-deep, code-thin; freeze spec, build ONE vertical slice before widening" | **CONFIRM as written; REVISE as of today** | The diagnosis was accurate on 2026-05-31 and — decisively — the prescription was followed: the 2026-06-11 reset added ZERO build stages and re-targeted the slice from Stage 11 to Stage 6 (ADR `2026-06-11_strategic_product_reset.md`; PRD v3 §18 "depth before breadth … binding"); Stage 6 then closed the first real predict→diagnose→intervene loop with a measured, independently re-run A/B. "Code-thin" is no longer a fair present-tense description (§2). |
| **§2 G-003** (Stage 3 close: frontend de-mock, baseline < 436) | **CONFIRM resolved** | Closed 2026-05-31 at 436→411 strict decrease; independently re-verified 2026-06-12 (`STAGE_03_independent_review.md` F-1: zero `Math.random` in `api.ts`, `getMockState` gone, honest `emptyState()`). |
| **§2 G-002** (full-app HTTP→WS compose e2e) | **CONFIRM still OPEN** | Ledger row OPEN; Stage 3 re-audit could not run the live-Redis leg (self-skipped, no Redis on host) — the 11.6 ms figure remains unreproduced from any committed artifact (its F-2). |
| **§2 G-001** (Stage 3 independent re-audit) | **CONFIRM resolved** | `STAGE_03_independent_review.md` (2026-06-12) completes and supersedes the partial 2026-05-31 attempt; PASS-WITH-GAPS; 12 passed/1 honest skip re-run by that auditor. Ledger row marked RESOLVED. |
| **§2 process wiring** ("wire `start-task.sh` to surface OPEN_GAPS_LEDGER rows" — remediation map target: Stage 4) | **REFUTE as done — NOT implemented** | `grep OPEN_GAPS_LEDGER scripts/start-task.sh` → **zero matches**; zero matches in `.claude/hooks/` and in any other script except `independent-audit.sh`, whose line 103 asserts *"start-task.sh surfaces them later"* — **false**. The ledger's own protocol §2 also claims this surfacing exists. Three stages (4, 5, 6) opened and closed since the remediation was due. Mitigated in practice only because implementers folded gaps manually (Stage 6 ACs embedded G-031/G-001). This is the one interim remediation that was simply not honored. |
| **§3 vuln: unsigned ADRs pre-13.5** | **CONFIRM, unchanged** | Still pre-13.5; acceptable and tracked; `STAGE_06_audit.md` §5 audit-chain quick-verify OK. |
| **§3 vuln: Groq free-tier SPOF; Ollama fallback must be real by Stage 11** | **CONFIRM, unchanged** | Stage 6 deliberately used NO LLM (deterministic loop — sidesteps the SPOF for now); PRD v3 §19 risk 8 keeps Ollama proof as a Stage 11 acceptance criterion. Verify in code at Stage 11. |
| **§3 vuln: RBAC/BLP spec-only** | **CONFIRM, unchanged** | G-029/G-030 OPEN, targets 11.5/19 — not yet due; do not pilot without them. |
| **§4 missing implementations: "all specified, none built"** | **REVISE — materially stale** | Predict is BUILT and live-capable (carded XGBoost, PR-AUC 0.847), diagnose v0 BUILT (pure deterministic, evidence trails), intervene v0 BUILT (shared policy, invariant-safe sim execution), measured A/B exists. Still unbuilt: verify step, PPO recovery, world model, causal twin, dashboard, evals depth, BLP — all ledgered with targets (§5). |
| **§5 cross-cutting risks** (over-scope dominant; audit-independence fragility; credibility = spec not proof) | **CONFIRM with revision** | Over-scope mitigations demonstrably held (spec freeze + slice-first). Independence machinery now PROVEN to work (two fresh-agent stage audits + this pass) — but owed audits were carried across a stage boundary again (G-031/G-001 were Stage 6 OPEN pre-requisites, unchecked at its close; G-001 paid next day, G-031 paid by this document). Credibility: half-converted — a sim-measured artifact now exists; a pilot (G-043) remains the binding constraint. |
| **§6 remediation map** (6 items) | **4 honored / 1 refuted / 1 not-yet-due** | #1 Stage 3 close: done. #2 ledger surfacing: **NOT done (refuted above)**. #3 vertical slice: done EARLY (Stage 6, better than the Stage 11 target). #4 RBAC/BLP/traceability and #6 Annex IV/mac.py: targets 11.5/19, not yet due, still ledgered. #5 Ollama proof: Stage 11, not yet due. Owed items: Stage 3 re-audit PAID (2026-06-12); independent CTO pass PAID (this file). |

## 2. Executive verdict

**ON TRACK — upgraded from the interim. The slice changed the verdict.** On 2026-05-31 this project was
spec-deep and code-thin; that was the right call then. Since: two real, carded, leakage-audited models shipped
(XGBoost PdM PR-AUC 0.847 with a recall-tuned threshold; LSTM demand MAPE 21%, +59% vs persistence — both
with rejected-predecessor honesty trails), the baseline fell 436→411→404→402→396 through genuine de-mocking
at every step, and Stage 6 closed the FIRST predict→diagnose→intervene loop with a 3-seed measured A/B that an
independent auditor re-ran on a seed the implementer never used — and which reported an *unfavorable* downtime
delta on that seed verbatim. That negative-result-reported-honestly is the single strongest trust signal in
this repo. The discipline (spec freeze, depth-before-breadth, fresh-agent audits, gaps ledgered not buried)
is now demonstrated behavior, not aspiration.

**The risk has moved, not vanished.** The dominant risk is no longer breadth-outrunning-build; it is
**conversion**: sim-proven → live-app-proven → pilot-proven. Today the running app does not execute the slice
(`LiveSliceRunner` built but unwired; `ManufacturingAgent` constructed without a `sim_world` handle), decisions
are not persisted (G-045), the A/B's robust metric is crack-prevention (92–100%) while the downtime headline
needs error bars (G-046), the brains are proxy-trained (G-035), and local test debt (G-044) plus frontend
fabrication residue (G-047/G-032) remain. One interim remediation was flatly not implemented (ledger
surfacing), and one frozen-document claim overstates evidence (§4 V2). Honest summary: **sim-proven,
production-unproven** — exactly where a Stage-6-of-25 system should be, and provably no further.

## 3. Gaps (immediate — fix or ledger before/at Stage 7 open)

1. **CTO #1 remediation #2 unimplemented + protocol text overclaims.** Neither `scripts/start-task.sh` nor
   `/begin`/`load-context.py` surfaces `OPEN_GAPS_LEDGER.md` rows, yet `OPEN_GAPS_LEDGER.md` §2 (protocol) and
   `scripts/independent-audit.sh:103` both state that surfacing exists. Either wire it (the interim called it
   "low effort, high leverage" — it still is) or correct both texts. Three stages closed relying on manual
   discipline; manual discipline held, but that is luck-shaped.
2. **G-031 row**: mark RESOLVED referencing this file (main session owns the ledger edit; I am read-only).
3. **Slice docstring drift**: `backend/services/slice_runner.py:18-19` claims an "optional `decision_logs`
   writer" that does not exist anywhere in the slice path — tighten when G-045's writer lands (or strike the
   clause at the next touch of the file, Stage 7).
4. **Ledger hygiene**: footer still reads "Last updated: 2026-05-31" though rows changed 2026-06-12; G-001's
   resolution is recorded but the cross-referencing text at the bottom still describes G-031/G-001 as Stage 6
   pre-requisites without noting disposition. Trivial; fix at next ledger touch.

## 4. Vulnerabilities (file:line, verified this session)

1. **V1 — committed `.pkl` artifacts contradict the documented pickle control.**
   `models/pdm_failure_predictor.scaler.pkl` and `models/demand_forecaster.scaler.pkl` exist in the repo,
   while `.claude/hooks/pre_tool_use.sh:89-91` (rule 7) blocks `.pkl` under `models/` and
   `compliance/risk-register.md` (pickle row, marked **high**) records the control as in place. The files got
   in because the PreToolUse hook only sees Write/Edit tool calls — binary artifacts added via Bash/Colab
   download bypass it entirely. **Mitigating fact I verified**: the runtime never unpickles them — both
   loaders read scaler params from JSON meta (`backend/ml/failure_predictor.py:135`,
   `backend/ml/demand_forecaster.py:108`), so there is no active code-execution path. But a documented
   high-severity control that is demonstrably bypassed is itself a finding: delete/convert the two files and
   add a git-level/CI check (`git ls-files 'models/*.pkl'` must be empty), because the hook architecturally
   cannot enforce this class.
2. **V2 — frozen-document claim overstates evidence.** `PRD-ai-embodied-agent-v3.md:235` claims
   *"11.6 ms p95 measured"* for the Stage 3 broker. The Stage 3 independent re-audit (F-2) established it is a
   **single-shot measurement on one dev host, not a p95, with no committed reproducible artifact** — and could
   not be re-measured (Redis down, test self-skipped). PRD v3 is hook-frozen, so the correction must land as a
   KB_26/ADR claim-correction note now and a fix in the next PRD version — this is precisely the
   product-manager role's claim-discipline mandate. The same number also appears uncorrected in the task doc
   and KB_TASK_LOG prose. Capture a real latency artifact when G-002's compose e2e finally runs.
3. **V3 — mechanical audit blind spot (confirms G-047).** `frontend-nextjs/src/lib/api.ts`
   `getMockModelMetrics()`/`getMockEmbodiedComparison()` return fabricated data in catch paths and match none
   of `scripts/audit.sh`'s twelve patterns. The 436→396 trajectory is real, but the gate is
   necessary-not-sufficient — extend the pattern set (`getMock`, hardcoded catch-path literals) at Stage 10.5
   so checkpoint #2 measures against a tighter net.
4. **Carried, unchanged from interim (all still true)**: unsigned ADRs pre-13.5; Groq single point of failure
   until the Stage 11 Ollama proof; zero access control on agent surfaces until 11.5/19 (G-029/G-030) — none
   newly actionable, all correctly scheduled.

## 5. Missing implementations (revised status of the interim's §4 list)

**Built since the interim**: predict (live-capable, carded XGBoost + honest refusal), diagnose v0
(deterministic, evidence trails, honest no-fault-found), intervene v0 (shared policy, sim-only,
invariant-safe), measured A/B harness, demand-forecast brain (carded, unwired to live state — G-036).

**Still missing, all specified with ledger targets (no change in substance, dates verified)**:
the loop's **verify** step (KB_25; planned), PPO recovery/RL intervene (G-025 → Stage 7), learned world model +
causal/neuro-symbolic diagnose (G-019/G-020 → Stage 8), live-app slice wiring + decision persistence + HITL +
active diagnosis + repair dispatch (G-045, Stage-6-review Gap 2, G-014, G-026, G-005 → Stage 11), dashboard +
live-cascade observability (G-006/G-021 → Stage 12.5), evals-to-Galileo depth (G-008 → Stage 20), digital twin
(G-007 → Stage 22.7), BLP/MAC + RBAC (G-029/G-030 → 11.5/19), real-data re-fit (G-035 → Stage 22). The ledger
(47 rows, 7 resolved, zero silently dropped) remains the single most load-bearing governance artifact in the
repo — protect it.

## 6. Cross-cutting risks

1. **Conversion risk (now dominant).** Every proof so far lives in SimPy + held-out proxy datasets. The Stage 6
   independent review's structural-favorability note is the sharpest framing: the calibration *guarantees*
   degraded machines enter the brain's trained AI4I regimes, so the A/B validates **loop machinery and
   intervention economics, not model skill on independent data**. All external claims must say "sim-measured
   under calibrated assumptions" until G-035/G-043 convert it. Stage 11 is where this risk is retired or
   realized — hold it to the full conversion list (live wiring, persistence, Ollama proof, G-044, G-036).
2. **Process-text/reality drift.** Three instances found this pass (ledger-surfacing claim, `decision_logs`
   docstring, 11.6 ms p95). Individually small; as a class, this is how theatre starts in a project whose
   entire moat is "provable." The fix is cheap: never document an enforcement as existing before it runs.
3. **Owed-audit carry-over pattern.** Twice now (Stage 3 re-audit, this CTO pass) independence debts were
   carried across a stage boundary with written IOUs. Both were paid, and the caveats were honest — but the
   pattern normalizes "audit later." Recommend a hard rule at Stage 10.5: a stage may not CLOSE (not just
   open) while a prior owed independent audit is unpaid.
4. **Solo execution bandwidth** (PRD v3 §19 risk 6) — unchanged, honest, and not solvable by process. The
   de-risked sequencing is the correct mitigation available.
5. **Baseline composition.** 396 remaining hits are concentrated in the un-de-mocked robotics/supply-chain
   heads and six frontend `page.tsx` files (84 `Math.random`) — i.e., the bulk of de-mock work is scheduled
   (Stage 11/G-021/G-032), not hidden. Trajectory credible.

## 7. Future-task remediations (the main session ledgers; targets named for routing)

| # | Remediation | Target stage |
|---|---|---|
| R1 | Wire OPEN_GAPS_LEDGER surfacing into `start-task.sh` (and `/begin`), OR correct the false claims at `OPEN_GAPS_LEDGER.md` §2 and `independent-audit.sh:103` — the unmet CTO #1 remediation #2 | **Stage 7 open** (it gates every subsequent open) |
| R2 | Delete or convert `models/*.scaler.pkl` (runtime verified not to load them) + add a CI/git-level `.pkl` check — the PreToolUse hook architecturally cannot catch Bash-added binaries | **Stage 7** (next code-touching stage) |
| R3 | Claim correction for "11.6 ms p95": KB_26/ADR note now; correct in next PRD version; capture a committed latency artifact when the compose e2e (G-002) runs | **Stage 10.5** (CTO #2 / product-manager claim review) |
| R4 | A/B statistical rigor: dedicated telemetry-noise RNG stream (CRN pairing) + per-seed spread/CI on the downtime delta (confirms G-046) | **Stage 7** (harness becomes the RL eval env) |
| R5 | `decision_logs` writer for slice decisions + fix the `slice_runner.py:18-19` docstring (confirms G-045) | **Stage 11** (docstring touch allowed at 7) |
| R6 | Extend `scripts/audit.sh` patterns (`getMock`, catch-path literals) so checkpoint #2 measures against a tighter net (G-047 class) | **Stage 10.5** |
| R7 | Add the close-gate rule: no stage closes while a prior owed independent audit is unpaid (formalize the lesson of G-031/G-001) | **Stage 10.5** (process; pair with G-015/G-038/G-039 cleanup) |
| R8 | Stage 11 conversion bundle — hold close hostage to ALL of: LiveSliceRunner wired, `sim_world` handle passed in the app, Ollama fallback proven, G-036 demand wiring, G-044 test debt, G-002 compose e2e | **Stage 11** |
| R9 | Mark G-031 RESOLVED referencing this file | **immediate** (main session) |

## 8. Bottom line

The interim self-review was honest: every finding I could test reproduced, its prescription (freeze spec,
build one slice) was the correct call, and — rarest of all — it was actually obeyed. What changed since is
real: two carded brains with rejected-predecessor audit trails, a closed predict→diagnose→intervene loop, a
measured A/B whose harness provably reports results it doesn't like, a 436→396 fabrication trajectory, and
audit-independence machinery that now demonstrably works. What hasn't changed: nothing runs outside the sim,
one interim remediation was silently skipped (ledger surfacing), and three small text-vs-reality drifts show
the documentation occasionally runs ahead of the code — the exact failure mode this project exists to prevent
in others. Fix R1–R3 cheaply, hold Stage 11 to the conversion bundle, and the system earns its own pitch.

**FINAL: Interim verdict REVISED (upward) — "on-track architecturally, high execution risk, spec-deep/code-thin"
was correct on 2026-05-31 but is now stale: the slice exists, is honest, and was independently verified, so the
system is no longer code-thin and execution risk drops from high to moderate. Overall system verdict: ON TRACK —
sim-proven, production-unproven; dominant risk is sim→live→pilot conversion (Stage 11 is the gate); one interim
remediation REFUTED as unimplemented (ledger surfacing, R1); no theatre, no gate bypass, no hard-rule violation
found. G-031 is paid by this review.**
