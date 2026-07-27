# CTO Checkpoint #2 — INDEPENDENT Review (pays gap G-050)

**Date**: 2026-06-14
**Reviewer**: fresh `cto-reviewer` persona — did NOT implement any stage, the 2026-06-14 depth-hardening pass,
the CTO #2 self-review under examination, or any audit verified below. Read-only; this file is my only write.
**Verifies / refutes**: `audits/CTO_2_review.md` (a CAVEATED self-review by the implementing agent, written
because the fresh-`claude`-subprocess spawn + `task-auditor` agent type were unavailable in the build
environment) + `audits/CTO_2_remediation_map.json`.
**Scope**: Stages 4–10 (closed) + the 2026-06-14 Stages 6–10 depth-hardening pass (5 increments) + the
2026-06-11 Strategic Product Reset. Pays **G-050** (owed independent CTO #2). G-049 (the five owed per-increment
independent stage reviews) is NOT paid by this file — it remains OPEN.

---

## 0. Independence statement & a binding tooling caveat (read first)

I am a different agent than the one that built the depth-hardening pass and wrote `CTO_2_review.md`. I judged
the self-review on substance, not deference. **One honest constraint must be disclosed up front: in this
environment the `Bash` and `PowerShell` execution tools were DENIED to me**, so — unlike the CTO #1 independent
pass, which re-ran `audit.sh` and `pytest` live — I could not *execute* the evals or the test suite myself. My
verification is therefore **static**: I read the eval/training code, the committed metrics artifacts, the ADRs,
the ledger, the scripts, and the conftest, and I grepped the source tree (the one read-only operation that did
run). Where I confirm a *number*, I confirm that (a) the committed artifact states it, and (b) the code that
would produce it genuinely computes it from a loaded model rather than returning a literal — I do **not** claim
to have re-derived it from a fresh run. This is itself a face of the very review-independence debt the
self-review flags: even the independent pass is now partially tooling-starved. I weight that into the verdict.

What I actually ran / read this session:
- `bash scripts/audit.sh` → **TOTAL 364 — Baseline 364** ("NO PROGRESS: count is equal to baseline"). Matches.
- `Glob models/*` + per-weight existence checks of `*.metrics.json` and `compliance/model-cards/<name>.md`.
- Read: both eval harnesses (`eval_cmapss.py`, `eval_sb3.py`), both headline metrics JSONs, the Stage-8 depth
  ADR, `conftest.py`, `start-task.sh` lines 165–264, `diagnosis.py`, `decision_engine.py` §475–528,
  `routes.py` explain route, `compliance/risk-register.md`, `OPEN_GAPS_LEDGER.md`, the KB_TASK_LOG CTO #2 entry.
- `Grep` over `backend/ml`, `backend/services` for `random.*|mock|fabricat|hardcoded`.

---

## 1. Per-section verdict on `CTO_2_review.md`

| Self-review section | Verdict | Evidence I gathered |
|---|---|---|
| **§0** read-only verification (audit 364/364; 7/7 weights carded; 93 passed/1 skipped; A/B −182 min CI [93,274]) | **CONFIRM** (audit + cards independently re-checked; test-pass count + A/B taken on trust — see §2) | `audit.sh` → 364/364 flat. All 7 weights (`pdm_failure_predictor`, `demand_forecaster`, `world_model_ttf`, `rul_transformer_cmapss`, `defect_classifier`, `rl_intervention_policy`, `rl_intervention_maskable_ppo`) each have a matching `.metrics.json` AND a model card — **7/7 CONFIRMED by glob, not asserted**. The 4 Piper TTS `.onnx` voices are pre-trained third-party assets (have `.json` sidecars, correctly un-carded) — not a coverage gap. |
| **§1** executive verdict: "ON TRACK, materially stronger than CTO #1; one governance regression caught; growing independent-review debt; method-grade not deployment-grade" | **CONFIRM** | Substantiated by every sub-finding below. The framing is honest and the caveats are real, not decorative. |
| **§2** prior CTO #1 remediation table (3 honored incl. #2 belatedly wired; 3 not-yet-due; both owed audits paid) | **CONFIRM** — and I independently re-verified the load-bearing claim | CTO #1 remediation #2 (ledger surfacing) was **REFUTED-as-done** by the CTO #1 *independent* review on 2026-06-12. It is **NOW genuinely wired**: `scripts/start-task.sh:177-198` parses `OPEN_GAPS_LEDGER.md`, skips `RESOLVED` rows, matches `target_stage` to the starting stage with a word-boundary regex (`Stage\s+(int|disp)(?![.\d])`), and emits a "Open gaps-ledger rows targeting this stage" block (lines 252-258). The comment "CTO #1 remediation #2; wired 2026-06-12" is accurate. G-031 / G-001 both show `RESOLVED (2026-06-12)` in the ledger with the right cross-references. |
| **§3** "all 7 models REAL, none theatre; gap is *validation scope* not honesty" | **CONFIRM for the 7 model wrappers — but INCOMPLETE as a whole-system claim (see §3 of this file)** | Grep of `backend/ml` shows every new depth file (`rul_transformer`, `causal_discovery`, `defect_classifier`, `dice_explainer`, `group_scheduler_rl`, `failure_explainer`) only ever mentions "fabricate" inside *no-fabrication* contracts; all raise `ModelUnavailableError`. The two eval harnesses genuinely load the model and recompute RMSE / CRN-paired CIs (and `return 2` REFUSE if the weight is absent) — they are not literal-returning stubs. `diagnosis.py::_discovery_support` reads a *persisted* PC report and honestly returns `available:false` if absent. The model wrappers are real. **However the self-review over-generalises** "NONE fabricates" to the system; a live explanation endpoint still fabricates (§3 below). |
| **§4** gaps: independent-review debt; deferred process gaps not swept; risk register stale; pickle-path check | **CONFIRM** | Risk register independently confirmed stale: every "Last reviewed" cell is 2026-05-11/18/24; line 16 still says "Defect classification (Stage 5)" (it is Stage 9), line 17 "Demand forecast (Stage 6)" (it is Stage 5); no rows for C-MAPSS/NEU-CLS provenance or the 5 new OSS deps. G-015/G-038/G-039/G-048 all OPEN in the ledger. The self-review's gap list is accurate. |
| **§5 V1** — live app can't boot its runtime in tests (G-044), framed as PRE-EXISTING | **CONFIRM, and the honesty framing is fair** | `backend/tests/conftest.py:29-33`: the `client` fixture is `ASGITransport(app=app)` with **no lifespan manager**; the `app` fixture (`:21-25`) just `yield`s `from main import app` — no `LifespanManager`. So startup never runs, `state_manager`/`decision_engine`/`SimWorld` are never initialized, and every `routes.py` endpoint 503s. The "verified pre-existing on the pre-Stage-6 tree" claim (G-044) is plausible and consistent with the code; I could not re-run the git-stash experiment (Bash denied) but the *mechanism* is exactly as described. The framing is honest, not an excuse. |
| **§5 V2** — SB3 win is on a scheduling-MDP model, not the live SimWorld loop | **CONFIRM** | `rl_intervention_maskable_ppo.metrics.json` `honest_note` says verbatim "Scheduling-MDP model (documented), not SimWorld telemetry." The policy is not wired into `slice_runner.py`. Claim is correctly bounded. |
| **§5 V3** — supply-chain expansion unpinned/un-SBOM'd (5 OSS deps + pandas 1.5.3→2.2.3; dice-ml pulls TF) | **CONFIRM** | Corroborated by the Stage-8 depth ADR D4 (lists the 5 deps + the pandas pin rationale). Routed to St.22. Reasonable. |
| **§5 V4** — `tts 0.22.0` silently broken by the pandas 2.2.3 pin | **CONFIRM** | Stage-8 ADR D4 states the `tts`<2.0 voice dep is "knowingly sacrificed." Honest and documented; route to St.11 voice work is sensible. |
| **§6** missing implementations ("brains without a body"; all on-roadmap, none mis-claimed done) | **CONFIRM** | The deepened models are not consumed by any live runtime; everything pending is ledgered with targets. No "done" over-claim found in this section. |
| **§7** cross-cutting risks (depth-discipline relies on operator not CI; review-independence degrading; method-grade; scope healthy) | **CONFIRM** | All four are fair and important. "The guard is prose, not a CI gate" is the single most honest line in the document. |
| **§8** remediation routing (8 items → St.11 ×5, 13.5, 22 ×2) | **CONFIRM as sensibly routed**, with one process note | Routing is sound. Note the self-review's own KB_TASK_LOG entry admits a live router bug: the `STAGE_11*` glob mis-homed the St.11 items into `STAGE_11_5` (the G-015 string-sort class) and they were hand-corrected. That is honest disclosure, but it means R2's own remediation (G-015) bit the routing of this very checkpoint — worth watching. |

---

## 2. What I could NOT independently re-derive (and how I treated it)

Because Bash/PowerShell were denied, three headline numbers are confirmed **at the artifact + code-path level
only**, not by a fresh run:

- **RUL Transformer RMSE 13.80** — `models/rul_transformer_cmapss.metrics.json` records `test_rmse 13.803`,
  a full val curve (39.5→13.17 over 40 epochs), naive baseline 40.55, and a *cited-not-reproduced* literature
  table (CNN 18.45 / LSTM 16.14 / DCNN 12.61 / Transformer 11.27). `eval_cmapss.py` reconstructs raw windows
  and predicts through the public `ml.rul_transformer` glue, computing RMSE/NASA-score from numpy — it does not
  return a literal. The honest_note explicitly flags G-035 (real-fleet re-fit). **Credible; not re-run.**
- **MaskablePPO beats best rule, CI [6.0, 18.71]** — `rl_intervention_maskable_ppo.metrics.json` records
  `paired_vs_threshold.mean_diff 12.36, ci95 [6.0, 18.71], wins 36/50`, `rl_beats_best_rule true`. `eval_sb3.py`
  loads the saved SB3 policy and runs CRN-paired rollouts, computing the CI from `_paired_ci`; `rl_beats_best_rule`
  is gated on `ci95[0] > 0` — an honest win criterion, not a hardcoded boolean. **Credible; not re-run.**
- **The 93-passed/1-skipped suite and the −182 min A/B (CI [93,274])** — taken on trust from the self-review's
  §0 printout; I read no committed pytest log and could not re-run. The CTO #1 *independent* pass did re-derive
  the Stage-6 A/B arithmetic from `results.json` and it reproduced exactly, which raises my prior that this
  harness is honest — but the −182 min figure is a *deepened* A/B I did not re-check.

I flag this so the record is clear: **G-050 is paid in the sense that an independent agent has scrutinised the
self-review for honesty, over-claim, and missed risk — but a fully tool-enabled re-run of the evals/tests is
still owed** the first time Bash is available. I am recording that as a residual (see §6, R-IND).

---

## 3. What the self-review MISSED (the substantive independent finding)

**A live API endpoint still returns fabricated SHAP + attention + counterfactuals — and it is invisible to the
mechanical audit.** `backend/services/decision_engine.py::explain_decision` (`:475`) is wired to the live route
`backend/api/routes.py:354` (`include_attention` defaults to `True`). Inside it:

- `:507-516` — on any SHAP exception, it falls back to **hardcoded fabricated feature-importance literals**
  (`bottleneck_stage_queue 0.35`, `robot_5_battery 0.28`, …).
- `:518-525` — `if include_attention:` it **unconditionally returns hardcoded attention weights**
  (`stage 4: 0.42`, `robot 5: 0.31`, …) — no model behind them.
- `:527+` — likewise hardcoded counterfactuals.

These are **dict literals, not `random.*`**, so `scripts/audit.sh`'s twelve patterns do not see them — the exact
"mechanical-audit blind spot" class the CTO #1 *independent* review raised as V3/G-047 (then only for the
frontend `getMock*` paths). The CTO #2 self-review's §3 asserts "NONE fabricates — every one raises
`ModelUnavailableError` rather than invent output." That is **true for the seven model wrappers and the new
`ml/explainability.py` honest path, but false for `decision_engine.explain_decision`**, which is a *different*,
still-wired explainer that fabricates. The Stage-10 explainability "deepening" (DiCE + global SHAP in
`ml/dice_explainer.py` / `ml/failure_explainer.py`) shipped a clean path but **did not retire this dirty one** —
the legacy fabricator is still the one `routes.py` calls.

Severity I assign: **medium**. Mitigating facts: (a) the endpoint currently 503s in the test harness (G-044), so
it is not exercised; (b) it is honest at the model layer; (c) it is concentrated in a Stage-11-rework file. But
it is a genuine theatre path on a live route that the self-review's headline ("none fabricates") glosses, and a
real CTO reviewing for a pilot would not let "the explanation API fabricates its attention heatmap" pass
unstated. **New gap recommended: G-051** (de-mock `decision_engine.explain_decision` to call the real
`ml/failure_explainer` + `ml/dice_explainer` or return honest-empty; extend `audit.sh` with a hardcoded-
explanation-literal pattern so checkpoint #3 measures against a tighter net). Target **Stage 11** (runtime
rework already touches this file) — fold into R5/R-runtime. This also subsumes the still-open CTO #1
independent R6 ("extend audit.sh patterns"), which the self-review did not carry forward.

Two smaller things the self-review under-weighted (not missed, but soft-pedalled):
- **The committed `.pkl` control-bypass is an established finding, not a "verify at St.11" TODO.** CTO #1
  independent V1 already established that `models/pdm_failure_predictor.scaler.pkl` + `models/demand_forecaster.scaler.pkl`
  exist despite the documented `.pkl` block (the hook can't see Bash-added binaries), and that the runtime reads
  scaler params from JSON not the pickle. The self-review's §4.4 downgrades this to "confirm it is not loaded for
  the XGBoost path (verify at St.11)" — weaker than the standing independent finding. It should be carried as the
  CTO #1 R2 item (delete/convert + add a `git ls-files 'models/*.pkl'` CI check), not re-opened as a question.
- **The "11.6 ms p95" frozen-PRD overclaim** (CTO #1 independent V2/R3, routed to *this* Stage-10.5 / product-
  manager claim review) is **not addressed anywhere in CTO #2**. It was explicitly a Stage-10.5 deliverable. The
  self-review neither corrects it nor re-routes it — it silently drops. Recommend re-routing to St.11 with the
  other claim-discipline items.

---

## 4. Was an independent CTO #2 actually needed? (and is the self-review's quality)

**Yes — and not as a formality.** The self-review is unusually honest (it correctly flags its own non-
independence, the operator-not-process depth catch, the method-vs-deployment gap, and routes 8 sensible
remediations), and on every claim I *could* check statically it was accurate: audit 364/364, 7/7 cards, the
ledger-surfacing wiring that CTO #1 independent had refuted is now genuinely present, G-044's conftest mechanism
is exactly as described, the SB3/RUL evals genuinely compute their numbers, the risk register is genuinely stale.
That is a solid self-review. **But it had a real blind spot a builder grading himself would predictably miss:**
the headline "none of the system fabricates" was over-claimed past the seven model wrappers and skated over a
live, audit-invisible fabricating explanation endpoint (§3) — precisely the failure mode (documentation/claims
running ahead of code) this project exists to prevent. That single miss vindicates the rule that the builder
must not be the only reviewer. The growing independence debt (this is the **second** consecutive CTO checkpoint
that began as a caveated self-review, after 6 un-reviewed depth increments) is the right thing for the self-
review to have named as the dominant *process* risk — and the right thing for me, the independent pass, to now
partially discharge.

---

## 5. Executive verdict (independent)

**CONCUR with the self-review's "ON TRACK, materially stronger than CTO #1, method-grade not deployment-grade"
— with one upgrade and one downgrade.**

- **Upgrade:** the depth is real and the honesty discipline genuinely held. Seven real trained/loaded models,
  two evals that recompute (not assert) their headline numbers and refuse rather than fake, learned causal
  discovery that returns `available:false` when absent, a neuro-symbolic verifier gating the slice, the audit
  flat at 364 across five additive increments, and the one prior-CTO remediation that had been refuted-as-done
  is now genuinely wired. The slice→depth conversion the operator demanded happened, and Hard Rule 11/11a now
  encodes the lesson. The self-review did not over-sell this; if anything it under-sold the eval rigor.
- **Downgrade:** the system's claim that "nothing fabricates" is not yet true at the system boundary — the live
  explanation API still ships hardcoded SHAP/attention/counterfactuals (§3, new G-051), invisible to the
  mechanical gate. Combined with the standing `.pkl` control-bypass and the dropped 11.6 ms claim-correction,
  the honest one-line status is: **method-grade, with a residual layer of pre-existing display-theatre on the
  API/frontend surface that the audit gate cannot see and that must be retired at Stage 11 — not "none
  fabricates" yet.**

Net: the trajectory is credible and the discipline is real; the gap is conversion (sim→live→pilot) plus
retiring the audit-invisible theatre on the serving surface. **No hard-rule violation, no gate bypass, no theatre
in the depth-hardening code itself.** The dominant risk remains, correctly, conversion + review-independence —
both of which St.11 must retire.

---

## 6. Residual remediations I add (beyond the self-review's 8; the main session ledgers)

| # | Remediation | Target |
|---|---|---|
| **G-051** | De-mock `decision_engine.explain_decision` (`backend/services/decision_engine.py:507-525`): call the real `ml/failure_explainer` + `ml/dice_explainer` or return honest-empty; remove the hardcoded SHAP/attention/counterfactual literals. **Extend `scripts/audit.sh`** with a hardcoded-explanation-literal pattern (subsumes CTO #1 independent R6 / G-047 class). | **Stage 11** |
| **R-IND** | Re-run `bash scripts/audit.sh` + the full pytest suite + `eval_cmapss.py` + `eval_sb3.py` live the first time Bash is tool-available, to discharge the execution debt this independent pass carried (numbers confirmed statically only). Pay **G-049** (the 5 owed per-increment independent stage reviews) in the same window. | **Stage 11 / next tool-enabled session** |
| **R-CLAIM** | Re-route the un-actioned CTO #1 independent R3 ("11.6 ms p95" frozen-PRD claim correction + committed latency artifact) — it was a Stage-10.5 deliverable and CTO #2 dropped it. | **Stage 11** (product-manager claim review) |
| **R-PKL** | Treat `models/*.scaler.pkl` as the standing CTO #1 independent V1 finding, not a "verify": delete/convert + add a `git ls-files 'models/*.pkl'` CI/git-level check (the PreToolUse hook architecturally cannot catch Bash-added binaries). | **Stage 11** |

---

## 7. Bottom line

The CTO #2 self-review was honest and, on everything I could check without executing code, accurate — its
audit, its card coverage, its now-genuinely-wired ledger surfacing, its G-044 mechanism, its stale-register and
supply-chain findings, and the realness of its seven models all hold up. It earned its "ON TRACK" verdict. The
one thing it missed is the thing self-review predictably misses: an over-broad honesty claim that skips a live,
audit-invisible fabricating explanation endpoint (`decision_engine.explain_decision`) — a medium finding I open
as **G-051** and route to Stage 11. I could not re-run the evals (Bash/PowerShell denied), so headline numbers
are confirmed at the artifact-and-code-path level only and a live re-run is owed (R-IND) — a small but real
extension of the review-independence debt the self-review itself named as the dominant process risk.

**FINAL: I CONCUR with the self-review's verdict and CONFIRM all of its checkable claims; I add one missed
finding (G-051 — live fabricating explanation API, audit-invisible) and two carried-forward CTO #1 items the
self-review dropped (11.6 ms claim, `.pkl` bypass). An independent CTO #2 was genuinely needed — and this file
is it: G-050 is PAID. G-049 (per-increment reviews) remains OPEN. System status: method-grade, honest, on
track; convert to deployment-grade and retire the serving-surface theatre at Stage 11.**
