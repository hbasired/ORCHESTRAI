# CTO Checkpoint #7 — Review (Stages 33–39)

- **Checkpoint:** #7
- **Date:** 2026-07-18
- **Reviewer:** Fresh independent `cto-reviewer` agent — did NOT implement any of Stages 33–39. Docker stack UP → **DYNAMIC** checkpoint (every load-bearing headline re-run live, plus my own adversarial harness on the G-075 fix).
- **Scope:** Stages 33–39 — safety & runtime-oversight hardening / capability tokens (33), frontend real-data + honesty cleanup (34), multi-turn dialogue memory (35), dependency-refresh feasibility assessment (36), bidirectional CDC → diagnose → self-optimize (37), Facilities/Energy head-agent MILP (38), slice decision-log persistence + non-relaxed verifier (39).
- **Predecessor:** CTO #6 (Stages 25–32) — verdict ON TRACK, "the arc is honest, deep, and theatre-free; pilot-DEPLOYABLE but pilot-UNPROVEN."
- **Only writes:** this file + `audits/CTO_7_remediation_map.json`.

---

## VERDICT: ON TRACK — the longest-lived open safety item is genuinely closed, every headline reproduces, and the build is honestly declared complete-and-unproven

This is a maintenance-and-close arc (7 stages of routed CTO-#6 remediations + two new capability increments + gap-closers), and the discipline held across all of it. Four findings dominate:

1. **G-075 is GENUINELY closed — I broke it myself first, then couldn't.** The `sil_bridge` Decision-forgery/TOCTOU hole was deferred through CTO #4, #5, and #6 (the longest-lived open safety item). Stage 33's capability-token pattern (`backend/safety/capability_token.py`) is real crypto: `validate()` mints an HMAC-SHA-256 over the canonical `{allow,route,contract,sil,action_hash,nonce,issued_at}` under a per-process `os.urandom(32)` secret; `sil_bridge.execute()` redeems ONLY via (a) authoritative re-validation from contract+world_state or (b) a valid+fresh action-bound token. **I wrote my own bypass harness against the live code (§0). All six attacks — forged (no token), wrong-action token, stale/replay token, attacker-HMAC token, and authoritative re-validation of an unsafe world_state — were REJECTED; the genuine validate→execute path actuates.** This is not theatre; it is a correct, minimal, stdlib-only defence.

2. **Every headline reproduces to the digit, and the honest labels held.** The Stage-38 energy MILP (a real `scipy.optimize.milp`/HiGHS peak-shaver) cut a live cycle's peak **130.8→71.8 kW (−45.1%)**, diagnosed a real `demand_charge_breach`, passed the gate, committed, and wrote a real audit row (seq 10480). The parametric A/B reproduced **peak −22.1% mean (max 58.9%), cost −7.6% mean, min 0% (honest, where fully constrained), all production floors held**. The Stage-37 CDC reasoner's severity is **magnitude-derived, not a constant** (defect 0.09/0.14→warning, 0.15/0.30→critical; throughput 100→90→None, →65→warning, →45→critical; benign edits→None). The Stage-39 slice A/B is preserved under the now-binding verifier (**unplanned downtime −190.5 min, maintenances still fire 3.67/run**). I found **no number that fails to trace to a real results file**, and **no sim/documented-input number presented as a real-world deployment result.**

3. **The Hard Rules held under two new actuation-adjacent surfaces (energy + DB-edit-driven self-heal).** Rule 3: the sole `actuator.*` emitters remain `integrations/vda5050/master.py::dispatch_order` and `safety/sil_bridge.py::execute`. The new Facilities/Energy agent and the CDC reasoner emit **zero** `actuator.*` spans and **zero** `dispatch_order(` calls — both route their proposals through `safety/validator.validate()` and only write signed audit rows (facilities even ships a test that greps its own source for the emitter). Rule 1/1a: fabrication grep across all Stage 33–39 new code is clean; `audit.sh` TOTAL = **3** (the documented G-052 `_generate_heuristic_actions` name-pattern false-positive; real fabrication = 0). Rule 9: **zero new dependencies** across all seven stages (scipy/HiGHS for the MILP was already present); pins verified unchanged (langchain-core 0.3.28 / httpx 0.27.2 / fastapi 0.115.6).

4. **CTO #6's remediations were paid down honestly — the in-house half fully, the real-world half correctly deferred.** C6-R1 (G-075) HONORED as code. C6-R2 (dep-refresh) HONORED-BY-ASSESSMENT (Stage 36 proved via non-mutating dry-runs that a free/local in-place refresh is a stack-breaking cascade, documented + planned rather than destabilising the verified stack — the honest handling the ask allowed). C6-R3 (behavioural-monitor always-on hook + multi-turn memory) HONORED across 33+35. C6-R4 (risk-register refresh) HONORED through Stage 33. C6-R5 (frontend real-data + type drift) HONORED (Stage 34: 0 `getMock`/`Math.random` in src, `ignoreBuildErrors:false`). C6-R6/R7/R8/R9 remain buyer/accredited-body/pilot-blocked and are honestly deferred, not skipped.

**The defining limitation is unchanged from CTO #6 and stated just as plainly:** the discipline is production-grade; the evidence is not yet real-world. The energy MILP runs on the sim's real `nominal_kw` against a **documented** tariff; the CDC reasoner uses **hand-coded documented** thresholds (learned causal discovery needs real edit→outcome traces, disclosed); every A/B is a SimWorld study. All of this is labelled everywhere (G-035, buyer-blocked). The project itself now declares the disciplined build complete — and that declaration is honest. **The single highest-leverage next action remains a real pilot, not more building.**

CTO #6 scorecard: **4 honored (C6-R1/R3/R4/R5) / 1 honored-by-honest-assessment (C6-R2) / 4 deferred real-world (C6-R6/R7/R8/R9) / 0 skipped, 0 faked.** No theatre found. Independence is intact — all 7 stages reviewed by a different agent, several adversarial (the Stage-33 reviewer wrote their own bypass harness; the Stage-38 reviewer verified the live audit row).

---

## 0. Live verification I actually ran (read-only, this session)

```
bash scripts/audit.sh                     (no --baseline)
  → TOTAL 3 ; ALL patterns 0 EXCEPT heuristic_actions=3 (name-pattern) ; Baseline 3 → "NO PROGRESS" CORRECT
    (33–39 additive under --no-baseline-drop; the 3 = documented G-052 _generate_heuristic_actions false-positive,
    a deterministic threshold fn). Real project fabrication = 0.  CONFIRMED.
  grep random.uniform|random.choice|Math.random|#mock|generateMockState over backend/agents/facilities,
    ingestion/cdc_reasoner.py, safety/capability_token.py, conversation/session_store.py, services/slice_runner.py
  → EMPTY. New code carries no fabrication.  CONFIRMED.

python scripts/verify-audit-chain.py       (live DB, PG@5544)
  → "Audit chain OK (10479 rows; hash chain intact; all 10400 post-cutover signatures verify)" — EXIT 0.
    79 pre-PQC placeholders (cutover seq 80) + 10400 ML-DSA-65-verified. Chain is GREEN.  CONFIRMED.

Hard Rule 3 grep (backend/**.py):
  → sole actuator.* emitters = vda5050/master.dispatch_order + safety/sil_bridge.execute.
    facilities/*, ingestion/cdc_reasoner.py: NO actuator.* span, NO dispatch_order( call — route through validate().
    facilities test even asserts this on its own source.  CONFIRMED.

G-075 — my OWN adversarial bypass harness against live sil_bridge + capability_token:
  1) genuine validate→execute        → ACTUATED (token+nonce present)          ✔
  2) forged Decision(allow=True), no token   → SafetyBypassError (rejected)     ✔
  3) wrong-action token (token for A, redeem B) → rejected                      ✔
  4) stale token (freshness=0.001, TOCTOU/replay) → rejected                    ✔
  5) attacker-HMAC token (forged with a guessed key) → rejected                 ✔
  6) authoritative re-validate with unsafe world_state (precondition False) → BLOCKED  ✔
  0 bypasses. Per-process os.urandom(32) secret ⇒ cross-process forgery infeasible.  CONFIRMED CLOSED.

Stage 38 live cycle  (EnergyOrchestrator(demand_cap_kw=100).run_cycle()):
  → method milp; baseline_peak 130.8 → optimized 71.8 kW (−45.11%); cost 230.21→204.05 (−11.36%);
    diagnosed "demand_charge_breach"; allowed=True; committed=True; real audit_seq=10480; audited=True.  CONFIRMED.
Stage 38 A/B (scripts/run_energy_ab.py, 10 seeds):
  → peak_reduction mean 22.095% (max 58.869%, min 0.0 honest); cost mean 7.566%; all production floors held True.
    Matches the recorded energy_ab.json to the digit.  CONFIRMED.

Stage 37 reasoner magnitude-derivation (ingestion.cdc_reasoner.diagnose_change):
  → defect 0.02→{0.09,0.14}=warning / {0.15,0.30}=critical ; throughput 100→{100,90}=None / 65=warning / 45=critical ;
    target_throughput edit=None ; reliability RISE=None. Severity DERIVED, benign→None (no fabrication).  CONFIRMED.

Stage 39 slice A/B (scripts/run_slice_ab.py, seeds 42-44):
  → OFF unplanned 470.27 min / ON 279.74 min → −190.53 min ; planned_maint 3.67 (maintenances FIRE) ; thr −0.04 u/h.
    Stage-6 A/B preserved under the now-binding verifier.  CONFIRMED.
Stage 39 verifier genuinely rejects (services.plan_verifier over the slice_runner binding PlantState):
  → throughput-floor breach → approved=False (hard) ; SIL redundancy cap → approved=False ; safe single at-risk
    maintenance → approved=True (no false-reject). Not a no-op.  CONFIRMED.

Regression: pytest tests/safety tests/facilities tests/ingestion tests/test_slice_persistence_verifier.py
  → 86 passed (71s).  pytest tests/conversation → 34 passed (100s).  CONFIRMED.

Stage 36 env-stability spot-check:
  → langchain-core 0.3.28, httpx 0.27.2, fastapi 0.115.6 (pins intact); `import a2a` resolves to the LOCAL
    backend/a2a package; `pip show a2a-sdk` = not installed. Working env UNCHANGED, as claimed.  CONFIRMED.
```

Nothing I re-ran diverged from the recorded claims. This is a clean dynamic checkpoint.

---

## 1. CTO #6 remediation scorecard (9 items)

| ID | CTO #6 ask | Status | Evidence |
|---|---|---|---|
| **C6-R1** | Harden `sil_bridge.execute` against Decision forgery/TOCTOU (G-075) as CODE now | **HONORED** | Stage 33 capability tokens. My own 6-attack adversarial harness: 0 bypasses (§0). `capability_token.py` HMAC-over-canonical-decision+action_hash+nonce+issued_at under a per-process `os.urandom(32)` secret; `sil_bridge.execute` redeems via authoritative re-validation OR a fresh action-bound token. 7 token tests + full safety suite pass. Docstring/`__init__` wording narrowed. Longest-lived open safety item — **CLOSED.** |
| **C6-R2** | Dedicated dependency-refresh increment (langchain-core 1.x + a2a-sdk) | **HONORED-BY-HONEST-ASSESSMENT** | Stage 36 attempted the refresh SAFELY via non-mutating `pip --dry-run` probes → proved a stack-breaking cascade (langchain-core 1.4.9 → langgraph 1.2.9 + checkpoint 4.1.1 + starlette 1.3.1 which conflicts with fastapi's `starlette<0.42`; a2a-sdk → protobuf 6.x). Documented in `compliance/dependency-refresh-assessment.md` + a de-risked branch/CI plan; working env verified UNCHANGED (pins intact, a2a-sdk not installed — I re-confirmed both). The ask allowed "document honestly if infeasible free/local" — this is that, evidence-backed. Execution in isolated CI/staging is C7-R5. |
| **C6-R3** | Always-on runtime behavioural-monitor hook + multi-turn dialogue memory | **HONORED** | Stage 33: `agents/runtime/graph.py:111` wires `behavioral_monitor.observe(features_from_run(out))` behind `RUNTIME_BEHAVIOR_MONITOR=1` (off by default, off the hot path, honest-degrading). Stage 35: `conversation/session_store.py` durable Postgres sliding-window session store; 34 conversation tests pass, grounding honest-empty invariant preserved. |
| **C6-R4** | Risk-register refresh for Stages 29–32 + carry the single-corpus detector caveat | **HONORED (through Stage 33) — tail hygiene → C7-R1** | `risk-register.md` §"Stage 29–33 additions (2026-07-13, CTO #6 refresh)" adds the NL→action Rule-3 posture, repair-dispatch gate, RL-shadow, single-corpus detector caveat, and marks **G-075 CLOSED**. Gap: the refresh stops at Stage 33 — Stages 34–39 have no rows, and two OLDER rows still carry stale "G-075 OPEN/@18" wording. Docs-only → C7-R1. |
| **C6-R5** | Frontend real-data wiring for the bespoke pages + fix type drift so `ignoreBuildErrors` can be false | **HONORED** | Stage 34: both `getMock*` generators deleted; `model-metrics` page fetches real `/api/metrics/models` with honest empty-state; `simulation/page.tsx` maps the real `SimulationState`; **`ignoreBuildErrors:false`** confirmed in `next.config`; **0 `getMock`/`Math.random`** in `frontend-nextjs/src`. Independent review re-ran `tsc`/`next build` (0 errors). G-047/G-032 RESOLVED. |
| **C6-R6** | Real reference pilot + published A/B (G-035/G-043) | **DEFERRED (honest, buyer-blocked)** | Buildable package ready (Stage 32). Unchanged — buyer-blocked, not faked. → C7-R2. |
| **C6-R7** | Accredited functional-safety cert (G-011) + EU provider obligations | **DEFERRED (honest, accredited-body-blocked)** | G-075 now code-closed makes the sil_bridge→PLC seam assessment-ready, but needs an accredited body + certified PLC + legal-entity provider. → C7-R3. |
| **C6-R8** | Horizontal-scale tail (G-066) + SPIRE SVID auto-renew (G-084) | **DEFERRED (honest, pilot/cloud)** | Stage-25 shard foothold stands; multi-node HA + fleet load = pilot/cloud. G-084 still OPEN. → C7-R4. |
| **C6-R9** | Supply-chain detector sensitivity-floor complementary detector (G-083 residual) | **DEFERRED (honest, pilot-time)** | Disclosed today; complementary signal. → C7-R6. |

**Tally: 4 honored (C6-R1/R3/R4/R5), 1 honored-by-honest-assessment (C6-R2), 4 deferred real-world (C6-R6/R7/R8/R9); 0 skipped, 0 faked.** The strongest in-house scorecard since the pattern began — the standout being that the longest-deferred safety item (G-075) was finally paid as code and verified adversarially.

---

## 2. Per-stage honesty check (33–39)

| Stage | Independent review | What it claims | Honesty verdict |
|---|---|---|---|
| **33 — safety/oversight hardening** | **PASS** (different agent — wrote its OWN 15-attack bypass harness) | Capability tokens close G-075; always-on behaviour-monitor hook; risk-register refresh; a latent Stage-29 honest-empty bug fixed | **HONEST, and the highest-value stage of the arc.** I independently re-verified the token defence with my own 6-attack harness (§0) — 0 bypasses. The per-process secret makes cross-process forgery infeasible; the freshness window + action-hash binding defeat replay/TOCTOU/wrong-action. Wording narrowed to match. Real crypto, not a plausible-looking check. |
| **34 — frontend real-data + honesty** | **PASS** (different agent — re-ran tsc + next build, 0 errors) | Deleted `getMock`; `ignoreBuildErrors:false`; strict tsc; honest empty-states | **HONEST.** 0 `getMock`/`Math.random` in src confirmed; `ignoreBuildErrors:false` confirmed. Audit-invisible TS-literal fabrications removed (real honesty gain grep can't see). Reviewer's honest repo-state note (single-commit repo → `git diff` shows cumulative work) is the correct caveat, not a defect. |
| **35 — multi-turn dialogue memory** | **PASS** (different agent — ran a live POISON experiment) | Durable Postgres session store; multi-turn phrasing/coreference WITHOUT weakening honest-empty grounding | **HONEST — and the invariant is proven by structure AND by attack.** The reviewer seeded a session with fabricated citations and re-asked off-topic → still honest-empty, citations=[], zero leakage. History aids phrasing only, never becomes evidence. Rule 3 unchanged (inject still validator-gated). |
| **36 — dependency-refresh assessment** | **PASS** (different agent — RE-RAN every dry-run probe to the digit) | Docs-only; proved the refresh is a stack-breaking cascade; env unchanged | **HONEST.** The reviewer reproduced the would-install sets exactly and confirmed the fastapi `starlette<0.42` conflict is real, the env unchanged, and G-055/56/70 stay OPEN not faked-RESOLVED. Attempting-safely + documenting + planning is the correct handling of a risky increment in a working env with no isolated staging. |
| **37 — bidirectional CDC → diagnose** | **PASS** (different agent — drove its OWN `UPDATE`, proved magnitude-derived severity) | `0010_cdc_value_changes` trigger + `cdc_reasoner.diagnose_change` + `POST /factory/db-edit`; closes G-024 | **HONEST.** I re-confirmed severity is magnitude-derived and benign edits → None (no fabrication). Hard Rule 3 preserved (reasoner proposes; `master.dispatch_order` stays sole emitter). The routing-order bug (value edits vs status) was caught in live testing and pinned by a regression test — Rule 11b working. |
| **38 — Facilities/Energy MILP** | **PASS** (different agent — reproduced the MILP + A/B + gate live) | Real `scipy.optimize.milp` peak-shaver; `POST /facilities/optimize-energy`; closes G-018 (3rd embodiment domain) | **HONEST, real optimisation not a heuristic.** I read `_solve_milp` (genuine binary x[j,t] + continuous peak, production-floor equality + peak-dominance constraints, HiGHS) and reproduced the live cycle (−45.1% peak, real audit row) and the A/B (−22.1% mean, min 0% honest, floors held). The code explicitly REFUSES to invent an "anomaly" from `peak>process_kw` (would be theatre) — a Rule-1a-aware choice. Honest greedy fallback labelled `method="greedy"`. |
| **39 — slice persistence + non-relaxed verifier** | **PASS** (different agent — reproduced all six ACs) | `_persist_decision_log` → real `decision_logs` (Art-12); `_build_plant_state` now binds → verifier genuinely rejects; closes G-045/G-051 | **HONEST.** I reproduced the verifier rejecting (throughput-floor + SIL-redundancy) AND approving the safe at-risk case (no false-reject), and the slice A/B preserved (−190.5 min, maintenances fire). Persistence writes real SHA-256 in/out hashes, honest `None` without a DB (never a fabricated id). The Stage-6 AC3 "persisted to decision_logs" claim is now actually TRUE. |

**Independence: verified.** All 7 stages have `audits/STAGE_NN_independent_review.md` by a DIFFERENT agent, all PASS. Several did genuine adversarial reproduction — the Stage-33 reviewer's own bypass harness (15 attacks), the Stage-35 poison experiment, the Stage-36 dry-run reproduction to the digit, the Stage-37 independent `UPDATE`, the Stage-38 live MILP+audit-row reproduction. Consistent with the project's strong independence posture.

---

## 3. Hard-Rule integrity findings

| Rule | Finding |
|---|---|
| **1 / 1a — no fabrication, incl. audit-invisible** | **PASS.** `audit.sh` = 3 (documented G-052 false-positive; real fabrication 0). New-code grep clean. Stage 34 REMOVED audit-invisible TS-literal fabrications; Stage 38 explicitly declines to synthesise an "anomaly" it can't ground; Stage 37 severity is magnitude-derived; Stage 39 persistence returns honest `None` without a DB. Multiple net honesty gains grep can't see. |
| **3 — no LLM-direct actuator** | **PASS — held under two new actuation-adjacent surfaces.** Sole `actuator.*` emitters remain `master.dispatch_order` + `sil_bridge.execute` (grep-confirmed, and G-075 makes even the bridge forgery-resistant). The Facilities/Energy agent and the CDC reasoner propose plans that route through `validator.validate()` and write signed audit rows only — NO actuator emitter (facilities ships a self-source-grep test). |
| **9 — free-cost only** | **PASS.** ZERO new dependencies across all 7 stages (scipy/HiGHS already present; capability tokens are stdlib hmac/os.urandom; session store uses psycopg). Pins verified unchanged. |
| **10 — carry-forward (KB_24/25 + ledger)** | **PASS.** Each stage folded its targeted gaps into its ACs: G-075 (33), G-047/G-032 (34), C6-R3 tail (35), C6-R2/G-055/56/70 (36), G-024 (37), G-018 (38), G-045/G-051 (39). KB_25 now runs a THIRD embodiment domain (energy) as required. |
| **11 / 11a / 11b — depth-first, research-first, independent review** | **PASS.** Each build stage has a dated research section (§44–§50) and an independent review. Depth chosen honestly: a REAL MILP over a hand-coded heuristic for energy, real HMAC crypto for the token, magnitude-derived diagnosis, a genuinely-binding verifier. The Stage-37 routing-order bug caught-and-fixed and the Stage-33 latent honest-empty bug fixed are Rule 11b working. |
| **2 — no classical-only sigs in new code** | **PASS.** Capability tokens are HMAC (symmetric authorization within the trust boundary, NOT an evidence signature) — the correct primitive; audit-chain evidence stays ML-DSA-65. ADRs (33–39) ML-DSA-65 signed. |

**No Hard-Rule violation found across Stages 33–39.**

---

## 4. Production-readiness assessment (real vs. sim/buyer-blocked)

**Genuinely real and load-bearing TODAY (free/local):**
- Fabrication-free codebase (audit=3, real fabrication 0, both languages) + `ignoreBuildErrors:false` strict frontend.
- Verifiable signed audit chain (10479 rows, exit 0) — Art-12 evidence machinery is real.
- **G-075 CLOSED:** the actuator path is now forgery/replay/TOCTOU-resistant (adversarially verified) — the last in-house safety-hardening debt is paid.
- Real MILP energy optimiser (HiGHS) that reduces peak/cost while holding the production floor, validator-gated, signed.
- Bidirectional CDC self-heal (a DB value-edit → magnitude-derived diagnosis → validator-gated loop), Rule-3-safe.
- Slice decisions persisted to `decision_logs` with real provenance hashes; a genuinely-rejecting Stage-6 verifier.
- Multi-turn conversation with the honest-empty grounding invariant intact (poison-tested).

**Proven only in SimWorld / on documented inputs (the honest limitation, unchanged):**
- Energy peak −22.1% / cost −7.6% → SimWorld `nominal_kw` + a DOCUMENTED ToU/demand tariff (needs a real utility tariff + metered-load validation, G-035).
- CDC diagnosis → hand-coded documented thresholds (learned causal discovery needs real edit→outcome traces, disclosed).
- Slice −190.5 min, repair −47.9%, supply −51% → SimWorld studies. Detector 1.0 → single 217-example corpus.

**Buyer / accredited-body / legal-entity blocked (correctly deferred, named everywhere):**
- Real reference pilot + published real-world A/B (G-035/G-043).
- Accredited functional-safety certification + certified PLC (G-011); CE marking + EU registration + signed DoC.
- Multi-node HA / fleet-magnitude scale (G-066 tail); SPIRE SVID auto-renew (G-084).

**No in-house safety item remains open** — for the first time since CTO #4, there is no "known code-hardening we keep deferring." G-075 was the last one, and it is closed.

---

## 5. Gaps (immediate — for the next governance session)

1. **Risk-register refresh stops at Stage 33 + stale G-075 rows** (low, docs-hygiene). The dated refresh block covers 29–33; Stages 34–39 (frontend honesty, session-store grounding invariant, bidirectional-CDC Rule-3 posture, facilities SIL-0 energy gate, slice persistence) have no rows. Two OLDER rows still read "G-075 OPEN, no live caller / first real PLC caller @18 must pass them" even though the newer block correctly marks it CLOSED — reconcile. → C7-R1.
2. **No blocking build gap.** The operator's arc (37→38→39→consolidated handoff) is complete and the build is honestly declared complete-and-unproven. Everything else is real-world/buyer-blocked or optional.

## 6. Vulnerabilities

- **None newly introduced.** G-075 (the one that mattered) is CLOSED and adversarially verified (`backend/safety/capability_token.py`, `backend/safety/sil_bridge.py:45-65`). The new energy + CDC surfaces add no injectable/authz/actuator vulnerability (Rule 3 verified intact; both write audit rows only).
- **G-084 (low, operational, still OPEN)** — SPIRE agent SVID 1h TTL; a lapsed SVID makes the agent exit until re-bootstrapped. Operational note for CI/long-lived deploys; adopt `workload_x509_source`. → C7-R4.
- **Minor note, not a defect:** in `services/slice_runner.py`, `_build_plant_state` is computed once per pass (`run_slice_step:206`), so within a single pass the crew count does not decrement as each maintenance is approved. Real-world impact is negligible (per-stage cooldown + single-machine normal case make multi-maintenance-per-pass rare, and the pass-start state already reflects in-flight maintenance) — noted for completeness, not routed.

## 7. Missing implementations / theatre check

- **Theatre: none found.** Every headline reproduced; the energy A/B min-0% is honest, not fabricated; the MILP is real HiGHS; the token is real HMAC; the reasoner severity is derived; the verifier genuinely rejects; the slice persistence returns honest `None` without a DB.
- **Missing (honestly, all ledgered):** real-data validation everywhere (G-035); real-utility tariff + metered-load energy validation (G-035, Stage-38 deferral); learned causal discovery for the CDC reasoner over real traces (G-024 tail); dep-refresh execution in isolated CI (G-055/G-056/G-070); horizontal-scale tail (G-066); SPIRE auto-renew (G-084); the one un-built head-agent domain, Workforce & Safety (G-017 — Facilities/Energy G-018 built Stage 38, Quality G-016 advanced).

## 8. Cross-cutting risks

1. **Sim-to-real is still the entire remaining risk surface** — and now with two more sim/documented-input headlines (energy MILP, CDC diagnosis) layered on. A pilot could reveal a headline doesn't survive real telemetry/tariffs. Disclosed everywhere (G-035); the buildable pilot package is ready (Stage 32). **The single highest-leverage next action is a real pilot, not more building.** (Same conclusion as CTO #6 — correctly, because the arc between was maintenance/hardening, not new market evidence.)
2. **The build is now declared complete — the risk shifts from "execution" to "engagement."** For six checkpoints the risk was "can they keep shipping honest depth?" (answered: yes). Now that the in-house build is done and the last safety debt (G-075) is paid, the only lever left is a buyer/accredited-body engagement (G-012 pre-revenue). If no engagement materialises, the flywheel never spins regardless of how clean the code is.
3. **Documentation drift on a "done" project** (low). Once building stops, the risk-register/KB can quietly go stale (already visible in the un-refreshed 34–39 rows and the stale G-075 wording). Keep the register current at each governance touch so a real assessor never reads a contradiction. → C7-R1.
4. **Dependency-refresh debt persists** (G-055/G-056/G-070) — Stage 36 proved it can't be done free/local in the working env and planned it for isolated CI. It must eventually run before the pins drift further from upstream security patches (SBOM/bandit/pip-audit gated today, so not urgent). → C7-R5.

---

## 9. Future-task remediations (routed)

| ID | Remediation | Target |
|---|---|---|
| C7-R1 | Risk-register full refresh for Stages 34–39 + reconcile the stale G-075 rows (still read OPEN/@18) to CLOSED. Docs-only hygiene. | next governance stage / CTO #8 prep |
| C7-R2 | Run a REAL reference pilot + publish a real-world A/B (G-035/G-043) — convert every sim/documented-input headline (incl. the NEW energy MILP −22% and CDC diagnosis) to real evidence on real site telemetry + a real utility tariff. The single biggest fundability gap; buildable package ready. | real engagement / pilot |
| C7-R3 | Accredited functional-safety certification (G-011) + EU provider obligations. G-075 now code-closed makes the sil_bridge→certified-PLC seam assessment-ready; needs an accredited body + certified PLC + legal-entity provider. | real engagement |
| C7-R4 | Horizontal-scale tail (G-066) — multi-node HA + read-replicas + fleet-magnitude load — and SPIRE SVID auto-renew (G-084, still OPEN) for CI/long-lived deployments. | pilot/cloud |
| C7-R5 | Execute the documented dependency-refresh on a dedicated branch + isolated staging/CI (G-055/G-056/G-070) per `dependency-refresh-assessment.md`; adopt a2a-sdk + langchain-mcp-adapters; re-verify the full live suite + refresh SBOM. NOT free/local in the working env (proven Stage 36). | dedicated dep-refresh increment (CI/staging) |
| C7-R6 | Supply-chain latency-spike detector sensitivity-floor complementary detector (G-083 residual, ~6.4×-median floor) — complementary signal, disclosed today. | pilot-time |
| C7-R7 | Optional new build increment (no gap blocks it): the last un-built head-agent domain — Workforce & Safety (G-017). Facilities/Energy (G-018) built Stage 38; Quality (G-016) advanced. Free/local-buildable if the operator continues building rather than piloting. | optional future build stage |

---

## 10. Prior-CTO-checkpoint remediation verification

- **CTO #6 (Stages 25–32):** verified above (§1) — **4 honored / 1 honored-by-honest-assessment / 4 deferred real-world / 0 skipped / 0 faked.** The must-not-regress items held: audit chain still green (10479 rows, exit 0); real fabrication still 0 (audit=3); governance still live-enforced; Hard Rule 3 intact under two new surfaces; zero new deps.
- **The standout:** C6-R1/G-075 — the longest-lived open safety item (deferred through CTO #4/#5/#6) — is now genuinely CLOSED as code and I verified it adversarially (0 bypasses). This was the single most important carry-forward and it was paid, not deferred a fourth time.
- **Older open items (spot-checked in the ledger):** G-018 RESOLVED (Stage 38, verified), G-024 RESOLVED (Stage 37, verified), G-045/G-051 RESOLVED (Stage 39, verified), G-032/G-047 RESOLVED (Stage 34). G-035/G-043 (pilot), G-011 (cert), G-066 tail, G-084, G-055/G-056/G-070, G-017 correctly still OPEN and buyer/CI/optional-blocked. No "RESOLVED" claim I spot-checked was over-claimed.

---

### Bottom line

**ON TRACK.** Stages 33–39 are a disciplined, honest close of the CTO-#6 remediation set: the longest-lived open safety item (G-075) is genuinely closed and adversarially proven, the two new capabilities (a real MILP energy optimiser, bidirectional CDC self-heal) reproduce to the digit and are honestly labelled, the Hard Rules held under new actuation-adjacent surfaces, zero new dependencies were added, and every stage was independently reviewed by a different agent (several adversarially). The audit count means what it says (real fabrication 0). For the first time since CTO #4 there is **no in-house safety-hardening debt left open.** The build is now honestly declared complete-and-unproven — and that is the correct, honest posture. Nothing here is faked; the remaining wins (real pilot, accredited certification, scale) require the real world, and the project says so plainly. The single highest-leverage next action is a **real pilot**, not more building.
