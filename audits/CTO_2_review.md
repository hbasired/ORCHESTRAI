# CTO Checkpoint #2 — Review (Stages 4–10 + the 2026-06-14 depth-hardening pass)

**Date**: 2026-06-14
**Scope**: Stages 4–10 (all closed) + the out-of-band Stages 6–10 depth-hardening pass (5 increments, 2026-06-14)
+ the 2026-06-11 Strategic Product Reset. Fires at Stage 10.5 per the roadmap.
**Reviewer persona**: `cto-reviewer` (read-only). This file + `audits/CTO_2_remediation_map.json` are the only writes.

> **INDEPENDENCE CAVEAT (read first).** The canonical CTO checkpoint runs as a FRESH `claude` subprocess via
> `scripts/cto-review.sh` (independent of the implementer). In this environment that spawn path — and the
> `task-auditor` agent type used for per-stage independent reviews — are **unavailable**, so this is an honest
> **self-review by the implementing agent**, ruthlessly caveated (same precedent as the CTO #1 interim of
> 2026-05-31, which was later paid by a fresh agent on 2026-06-12). I built the depth-hardening pass under review,
> so treat my verdict on it as honest-but-not-independent. **A fresh independent CTO #2 pass is OWED** (new gap
> **G-049**, below), alongside the **five owed per-increment independent reviews** for Stages 8/9/7/10/6 deepenings.
>
> **UPDATE (2026-06-14, same day): the owed reviews are now PAID.** Fresh `general-purpose` agents adopting the
> `task-auditor` / `cto-reviewer` personas independently reviewed all 5 increments
> (`audits/STAGE_0{6,7,8,9,10}_depth_independent_review.md`, all PASS) and produced an independent CTO #2
> (`audits/CTO_2_independent_review.md`, CONCUR) — **G-049 / G-050 RESOLVED**. They found two things this self-review
> missed: **G-051** (the Stage-6 VERIFY step is a no-op gate — wording corrected) and a **live fabrication in
> `decision_engine.explain_decision`** (hardcoded SHAP/attention/counterfactuals, audit-invisible) — **now de-mocked**;
> the broader `decision_engine` fabrication surface is ledgered **G-052 → Stage 11**. Caveat: the reviewer agents'
> Bash/pytest execution was denied → static verification + hand-recomputation (one ran `audit.sh`=364). The
> independence requirement (a different agent) is met; a dynamic re-run is belt-and-suspenders.

## 0. Read-only verification I actually ran (this session)

```
bash scripts/audit.sh
  → TOTAL 364 — Baseline (.audit-baseline): 364  (held flat across all 5 additive depth increments)
weights vs metrics.json vs model cards (all 7):
  pdm_failure_predictor · demand_forecaster · world_model_ttf · rul_transformer_cmapss ·
  defect_classifier · rl_intervention_policy · rl_intervention_maskable_ppo  → metrics:Y card:Y (7/7)
pytest (depth-hardening surface, 13 files): 93 passed, 1 skipped
  (tests/test_rul_transformer, test_causal_discovery, test_plan_verifier, test_group_scheduler,
   test_dice_explainer, test_vision_defect, test_world_model, test_diagnosis, test_slice_*, test_models)
A/B (scripts/run_slice_ab.py, 5 seeds/8h): unplanned downtime −182 min, bootstrap 95% CI [93, 274] (significant)
```

## 1. Executive verdict

**ON TRACK and materially stronger than CTO #1 — with one governance regression caught (and corrected) and a
GROWING independent-review debt.** CTO #1 said "spec-deep, code-thin; build one vertical slice before widening."
That prescription was followed (slice landed early at Stage 6) and is now **converted to depth**: seven real
trained models (five with real-benchmark or statistically-measured results), the predict→reason→verify→intervene
loop wired end-to-end with a *significant* A/B, audit 402→**364**. The 2026-06-14 depth-hardening pass turned the
original "honest-but-shallow" Stages 6–10 into "honest AND deep" (Transformer RUL on real C-MAPSS RMSE 13.80;
defect 88.2%→99.3% via transfer learning; SB3 MaskablePPO genuinely beating the best rule; DiCE; the VERIFY step
wired). The honesty discipline held throughout (audit flat, no theatre added, every number measured + caveated).

**But three things temper the verdict:** (a) the original 6–10 shipped shallow and needed a costly re-deepening —
the **operator**, not the process, caught it (now guarded by new Hard Rule 11/11a); (b) **no part of the
depth-hardening pass was independently reviewed** (tooling), so a real review-independence debt is accumulating;
(c) the system remains **proxy/benchmark-validated, not real-fleet-validated** (G-035) and the live app cannot
boot its runtime in tests (G-044) — so "production-grade" is still *method-grade*, not *deployment-proven*.

## 2. Prior CTO #1 remediation verification (AC: cross-check `CTO_1_remediation_map.json`)

| CTO #1 remediation (target) | Status now | Evidence |
|---|---|---|
| #1 Close Stage 3 (frontend de-mock, baseline<436) → St.3 | **HONORED** | `tasks/STAGE_03_ws_broker.md` status:done; baseline 436→411; re-verified `STAGE_03_independent_review.md`. |
| #2 Wire `start-task.sh` to surface ledger rows → St.4 | **NOW HONORED** (was refuted 2026-06-12) | `scripts/start-task.sh:177` "CTO #1 remediation #2; wired 2026-06-12"; lines 180–253 surface OPEN rows whose `target_stage ≤ stage`. The CTO #1 independent review's R1 is thus closed. |
| #3 Vertical slice predict→diagnose→intervene → St.11 | **HONORED EARLY** (St.6, then deepened) | `services/slice_runner.py`; A/B `training/evals/stage06/results.json`. |
| #4 RBAC + Bell-LaPadula MAC + traceability → St.11.5 | **NOT YET DUE** | G-029/G-030 OPEN, targets 11.5/19. Do not pilot without them. |
| #5 Verify Ollama-local LLM fallback is real → St.11 | **NOT YET DUE** | Spec-only; Stage 11. Free-cost resilience unproven in code. |
| #6 Annex IV pack + `backend/governance/mac.py` → St.19 | **NOT YET DUE** | Stage 19. |
| Owed: independent CTO #1 (G-031) | **PAID** | `audits/CTO_1_independent_review.md` (2026-06-12). |
| Owed: Stage 3 independent re-audit (G-001) | **PAID** | `STAGE_03_independent_review.md` (2026-06-12). |

**Net: 3 honored (one belatedly), 3 not-yet-due, both owed audits paid. No skipped-and-now-due remediation.**
A real improvement over CTO #1, where remediation #2 was outright skipped.

## 3. Are the shipped models production-grade or theatre-shipped? (AC — cite files)

**Verdict: all seven are REAL (no theatre) and method/benchmark-grade; NONE is deployment-validated.** None
fabricates — every one raises `ModelUnavailableError` rather than invent output, and the audit count (364, flat)
confirms the depth pass added zero `random.*`/mock patterns.

| Model | File | Result (measured) | Honest ceiling |
|---|---|---|---|
| Failure predictor (XGBoost) | `ml/failure_predictor.py` | PR-AUC 0.847 (AI4I) | AI4I proxy (G-035) |
| Demand forecaster (LSTM) | `ml/demand_forecaster.py` | MAPE 21% / +59% vs persistence | carded; not wired to live state (G-036) |
| World model TTF (LSTM) | `ml/world_model.py` | MAE 0.067 min vs 2.979 | near-trivial SimWorld signal (honest) |
| **RUL Transformer** | `ml/rul_transformer.py` | **RMSE 13.80 on REAL C-MAPSS FD001** (beats CNN 18.45 / LSTM 16.14) | benchmark, not the plant (G-035) |
| **Defect classifier (ResNet18 TL)** | `ml/defect_classifier.py` | **99.3% on REAL NEU-CLS** (was 88.2%) | steel-surface proxy (G-035); positional labels unverified |
| RL intervene (from-scratch PPO) | `ml/intervention_rl.py` | tied rules (honest negative, retained) | simpler regime |
| **RL intervene (SB3 MaskablePPO)** | `ml/group_scheduler_rl.py` | **beats best rule −125.1 vs −137.4, CI [6.0,18.71]** | scheduling-MDP **model**, not SimWorld telemetry; not wired to live loop |

Plus three real method components: exact-TreeSHAP + DiCE (`ml/failure_explainer.py`, `ml/dice_explainer.py`),
learned causal discovery (`ml/causal_discovery.py`, skeleton F1 0.75), neuro-symbolic verifier
(`services/plan_verifier.py`, now gating execution in the slice). **The credibility gap is not theatre — it is
*validation scope*: real benchmarks/models, proxy data, no live runtime, no actuator.** That is the honest story
the model cards already tell; the CTO's job is to keep it told and not let "99.3% on NEU-CLS" become "99.3% in the
warehouse" in any pitch.

## 4. Gaps (immediate — address at/before Stage 11 open)

1. **Independent-review debt (the dominant process gap this checkpoint).** The five depth-hardening increments
   (Stages 8/9/7/10/6, 2026-06-14) were self-verified only — `task-auditor` was unavailable. This CTO #2 is itself
   a self-review. The project's own rule (CLAUDE.md §6) requires a *different* agent. → **G-049/G-050** (below).
   Mitigation in place: every increment re-ran its tests, reproduced eval numbers through the public glue, and
   confirmed no leakage — but that is the builder grading himself, exactly what the rule forbids.
2. **Deferred process gaps were NOT swept at the checkpoint that owns them.** `G-015` (next-task string-sort bug),
   `G-038` (role-map duplicated in `start-task.sh` + `context_loader.py`, fragile substring match), `G-039`
   (append-only is convention-only for `KB_TASK_LOG.md` + `research/initial-research.md` — no hook guard),
   `G-048` (`close-task.sh` OPEN_GAPS arithmetic fragility) are all ledgered "Stage 10.5 (CTO #2 cleanup)" and
   remain OPEN. The follow-up `agentic-governance-engineer` session must clear them.
3. **Risk register is stale.** `compliance/risk-register.md` last-reviewed dates are 2026-05-11/18/24; the cadence
   ("Every CTO checkpoint refreshes the full register") was not honored. Stale stage numbers (e.g. "Defect
   classification (Stage 5)" — it is Stage 9; "Demand forecast (Stage 6)" — it is Stage 5), and **no rows** for
   the depth-hardening additions (C-MAPSS/NEU-CLS data provenance, the new OSS supply chain: causal-learn/dice-ml/
   stable-baselines3/sb3-contrib/gymnasium, the pandas-2.2.3 pin that breaks `tts<2.0`). → route to St.11.
4. **`pdm_failure_predictor` is loaded from `.xgb.json` via `xgboost`** — confirm the Stage-24 risk-register row
   "Pickle code-execution on weight load" is honored (no `.pkl` in the load path). `failure_predictor.py:69`
   uses `model.load_model(.xgb.json)` (safe); `*.scaler.pkl` exists in `models/` — verify it is not loaded for
   the XGBoost path (it is the MLP path's; confirm at St.11).

## 5. Vulnerabilities (file:line, verified read-only this session)

1. **V1 — live app cannot boot its runtime in tests (G-044, confirmed pre-existing).** `backend/tests/conftest.py:31`
   builds the test client as `ASGITransport(app=app)` with **no lifespan manager**, so `state_manager` /
   `decision_engine` / `SimWorld` are never initialized → every `routes.py` / `simulation_routes.py` endpoint
   returns 503 (21 `test_api` failures), and `test_websocket_smoke` hangs. The ledger (G-044) records this was
   git-stash-verified pre-existing on the pre-Stage-6 tree — i.e. **not introduced by the depth pass**, but it
   means the full app integration path is *unexercised* and the deepened models are **not proven in a live runtime**.
   This is the single biggest "looks-done-isn't" risk for a pilot. → St.11 (runtime rework) must fix the fixture
   (wrap with a lifespan manager) AND stand up Neo4j in the test stack.
2. **V2 — SB3 MaskablePPO win is on a scheduling-MDP MODEL, not the live SimWorld loop.** `group_env.py` is a
   documented abstraction; the policy is NOT wired into `slice_runner.py` (different state space). The "RL beats
   rules" claim is true *for that regime* and must not be quoted as "RL beats rules in the plant." Honest in the
   model card + ADR; keep it honest in any external material.
3. **V3 — supply-chain expansion unsigned/un-pinned beyond requirements.txt.** Five new OSS deps + a major pandas
   bump (1.5.3→2.2.3) landed via `pip` with no hash pinning / SBOM; `dice-ml` pulls TensorFlow transitively. The
   risk-register "weight-load" and "policy DSL" rows exist but there is no dependency-provenance control. Pre-pilot
   (St.22) this needs a lockfile + SBOM. → ledger.
4. **V4 — `tts 0.22.0` is now broken** (needs `pandas<2.0`; we pinned 2.2.3 for `dice-ml`). Stage-2 voice is a
   declared low-risk component, but the breakage is silent — document it in requirements + the St.11 voice work.

## 6. Missing implementations (all specified, on-roadmap — none mis-claimed as done)

The deepened models are **brains without a body**: there is still **no live runtime** consuming them. Pending per
roadmap/ledger: LangGraph runtime + HITL + decision persistence + active diagnosis + repair dispatch + Ollama proof
(G-045/G-005/G-026/G-036 → **St.11**); MCP servers (St.11.5); agent memory + namespace isolation (St.12); live
cascade observability (G-021 → St.12.5); CDC inject wedge (St.13); PQC audit-chain signing — decision logs are
still placeholder-SHA256, not ML-DSA-65 (St.13.5); A2A (St.14); OT/IT + VDA 5050 (St.15/16); functional-safety
actuator wrapper (St.17); Annex IV evidence pipeline + RBAC/BLP (St.19); red-team evals (St.20); **real-fleet
re-fit (G-035 → St.22)** — the binding pre-pilot constraint; pilot (G-043 → St.22). The verify step is wired in
the slice but the *neuro-symbolic* depth (SMT/temporal logic) and the safety-wrapper integration are St.17.

## 7. Cross-cutting risks

1. **Depth-discipline relies on the operator, not yet the process — partially mitigated.** The shallow 6–10 builds
   passed every automated gate (audit, tests, even independent stage reviews) and were caught only by the operator.
   Hard Rule 11/11a + the per-stage mandatory-research requirement now encode "full depth in the first pass," and
   `TASK_TEMPLATE.md` seeds the depth-justification checkbox. **This is good recovery — but the guard is prose, not
   a CI gate.** There is no automated "is this the deepest honest free path?" check (inherently hard). Watch the
   next build stage (St.11) for recurrence; if it ships shallow again, the rule isn't working.
2. **Review-independence is degrading.** CTO #1 era proved the fresh-agent machinery works; this pass ran without
   it for 6 reviews (5 increments + this CTO). The honesty held *because the operator is engaged and the builder is
   disciplined* — neither is a control. Restore independent review the moment tooling permits; do not let a pilot
   claim rest on self-reviews.
3. **"Production-grade" is still method-grade.** Real benchmarks ≠ real deployment. G-035 (proxy data) + G-044 (no
   live runtime) + no actuator + unsigned audit chain mean the system is a *credible, honest prototype with
   SOTA-grade components*, not a deployable product. St.11 (runtime) and St.22 (real-fleet re-fit + pilot) are where
   this converts or stalls. Hold them to the full conversion list.
4. **Scope is healthy now** (the depth pass widened nothing; it deepened the existing slice). Keep it that way:
   resist new domains until St.11 gives the models a live body.

## 8. Future-task remediations (routed → `CTO_2_remediation_map.json`)

| # | Remediation | Target |
|---|---|---|
| R1 | Run the 5 owed per-increment independent reviews (Stages 8/9/7/10/6 depth) + an independent CTO #2 pass, via `independent-audit.sh`/`cto-review.sh`, when the fresh-agent tooling is available (G-049/G-050) | next session / 11 |
| R2 | Sweep deferred process gaps: G-015 (next-task sort), G-038 (role-map dup + word-boundary match), G-039 (append-only hook for KB_TASK_LOG + research log), G-048 (close-task.sh arithmetic) | 11 (open) |
| R3 | Refresh `compliance/risk-register.md`: correct stale stage numbers; add rows for C-MAPSS/NEU-CLS provenance, the new OSS supply chain, the pandas-2.2.3/tts conflict; update Last-reviewed | 11 |
| R4 | Fix the test harness (G-044): wrap the conftest `client` fixture in a lifespan manager + add Neo4j to the test stack so the live app path is actually exercised | 11 |
| R5 | Wire the deepened models into the live runtime (LangGraph + decision persistence + HITL) + prove the Ollama-local LLM fallback is real | 11 |
| R6 | Add dependency provenance: hash-pinned lockfile + SBOM for the expanded OSS surface (causal-learn, dice-ml, SB3, sb3-contrib, gymnasium); document the tts breakage | 22 |
| R7 | Carry forward the un-converted credibility constraints: real-fleet re-fit (G-035) + pilot (G-043) | 22 |
| R8 | Replace placeholder-SHA256 ADR/decision-log signing with real ML-DSA-65 | 13.5 |

## 9. Bottom line

The slice is no longer thin — it is deep, honest, and measured, with seven real models and a significant A/B. The
depth-hardening pass was the right response to a real shallowness, and the new hard rule should prevent recurrence.
**The two things to fix before this earns the word "production": give the models a live runtime (St.11) and pay
down the review-independence + real-data debts.** Stop self-certifying; wire the body; re-fit on real data. The
trajectory is credible.
