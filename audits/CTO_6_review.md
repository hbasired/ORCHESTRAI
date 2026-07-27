# CTO Checkpoint #6 — Review (Stages 25–32)

- **Checkpoint:** #6
- **Date:** 2026-07-13
- **Reviewer:** Fresh independent `cto-reviewer` agent — did NOT implement any of Stages 25–32. Docker stack UP → **DYNAMIC** checkpoint (every headline re-run live).
- **Scope:** Stages 25–32 — post-GA operations (25), supply-chain automation (26), resilience & anti-fragility (27), GraphRAG + adoption UX + G-082 de-mock (28), and the operator's post-Stage-28 arc: conversational factory intelligence (29), live-wire self-healing loop (30), detector/eval hardening (31), pilot-readiness package (32).
- **Predecessor:** CTO #5 (Stage 24.5, Stages 22–24) — verdict ON TRACK, "GA is real and honest."
- **Only writes:** this file + `audits/CTO_6_remediation_map.json`.

---

## VERDICT: ON TRACK — the arc is honest, deep, and theatre-free; the system is pilot-DEPLOYABLE but still pilot-UNPROVEN

This is the largest span any checkpoint has covered (8 stages) and the discipline held across all of it. Three findings dominate:

1. **The de-mock finally landed and the baseline is now REAL.** Stage 28 drove `.audit-baseline` from a venv-inflated 364 to a project-true **3** (venv-scoping hygiene + a genuine legacy-path de-mock). I reproduced it live: `audit.sh` TOTAL **3**, and the 3 residual hits are all the single documented G-052 false-positive (`_generate_heuristic_actions` — a deterministic threshold function with zero RNG). **Real project fabrication = 0** in both Python and the frontend. For the first time the audit count means what it says.

2. **Every headline number reproduces to the digit, and every one is honestly labelled sim/benchmark/single-corpus.** Repair −47.9% (CI [7696,12733] excludes 0), supply-chain stockout −51% / bullwhip −98% (paired CIs exclude 0), injection detector 0.9935→1.0 / FPR 0.0156→0.0 on **held-out 5-fold CV explicitly stamped "NOT train-on-test"**, GraphRAG 1.0/1.0/1.0, active-diagnosis math independently re-derived from scratch by the Stage-29 reviewer (entropy 0.881291 / MI 0.531004 match, confidence VARIES across faults proving it's derived not hardcoded). I found **no number that fails to trace to a real results file**, and **no result presented as a deployment/real-world outcome**.

3. **The Hard Rules held under a lot of new surface area.** Rule 3 (no LLM-direct actuator) survived the two riskiest new features — NL problem injection (G-023) and repair-robot dispatch (G-005): the sole actuator emitter is still `master.dispatch_order`, the LLM in the conversation path is an input parser only, and repair dispatch routes through `safety/validator.validate()` under a `repair_dispatch` contract BEFORE any effect. Rule 1a held: Stage 30 **removed** an audit-invisible fabrication (the synthetic per-day demand `confidence` constant) — a net honesty gain the grep can't see. Rule 9 held: across 8 stages the only new deps were `spiffe`/`spiffe-tls` (Apache-2.0, free) in Stage 27; everything else added zero deps.

**The defining limitation of the entire arc — stated plainly:** it is a large body of REAL, deep, honestly-measured capability that has been validated ONLY in SimWorld / on benchmark corpora / on a 217-example detector set. Nothing in Stages 26–32 has touched a real fleet, a real customer's SOP corpus, or real traffic. This is **correctly deferred and honestly disclosed everywhere** (G-035/G-043 buyer-blocked; Stage 32 built the buildable pilot package precisely to convert it) — it is not a defect. But it is the one sentence a buyer/investor needs to hear: **the discipline is production-grade; the evidence is not yet real-world.** Converting sim→real via a pilot is the whole game now.

CTO #5 scorecard: **2 honored / 3 partial (buildable-half done, real-half buyer-blocked) / 2 honestly deferred / 0 skipped.** No theatre found. This is the right posture to continue from.

---

## 0. Live verification I actually ran (read-only, this session)

```
bash scripts/audit.sh
  → TOTAL 3 ; all fabrication patterns 0 EXCEPT heuristic_actions=3 (name-pattern) ; Baseline 3 → "NO PROGRESS" is
    CORRECT (25–32 additive under --no-baseline-drop; the 3 = documented G-052 false-positive).
  → grep of the 3 hits: all `_generate_heuristic_actions` in backend/ml/rl_policy.py (191/214/267) — a deterministic
    threshold fn; rl_policy.py has ZERO `import random`/`random.`. Real fabrication = 0. CONFIRMED.

python scripts/verify-audit-chain.py   (live DB, PG@5544)
  → "Audit chain OK (10469 rows; hash chain intact; all 10390 post-cutover signatures verify)"  — EXIT 0.
    Matches Stage 31's claim exactly. Chain is GREEN.

Results-file reproductions (python json load):
  repair_ab.json         → downtime_saved_pct 47.9 ; ci95 [7696.0,12733.1] ; ci_excludes_zero true ; 10 seeds ;
                           honest_label "SimWorld study (not a real fleet); real-data validation = G-035".  CONFIRMED.
  detector_hardening.json→ baseline_stage20 0.9935/0.0156 ; combined_detector_cv 1.0 det / 0.0 FPR ;
                           note "held-out 5-fold CV ... classifier never train-on-test".  CONFIRMED.
  supply_ab.json         → paired diff greedy−agentic: stockout mean 54.1 CI[12.6,95.6]; bullwhip 73.07 CI[49.0,97.2];
                           orders 3612 CI[3288,3936]; buffer_frac −0.005 CI[−0.039,0.029] (holding equal).
                           honest_label "SimWorld simulation study — NOT real supply-chain evidence".  CONFIRMED
                           (54.1 = 106.3−52.2 = −51%; 73.07 = 74.3−1.21 = −98%; CIs exclude 0 except buffer as claimed).
  graphrag_eval.json     → grounded 1.0 / honest_empty 1.0 / citation_precision 1.0 ; label "SimWorld/SOP-corpus scale
                           eval — NOT a public benchmark".  CONFIRMED.
  supply_drill.json      → injection arm raises latency_spike@supplier:4 during the freeze (ticks 109–111);
                           control arm events=[] (clean).  CONFIRMED (the Stage-26 Gap-1 controlled drill).

cd backend && pytest tests/conversation/ tests/repair/ tests/security/ -q
  → 51 passed, 0 failed (117s).  CONFIRMED.

ADR signature footers (stages 29–32): all four ML-DSA-65 signed, key_id agent-identity:v2.  CONFIRMED.
```

Nothing I re-ran diverged from the recorded claims. This is a clean dynamic checkpoint.

---

## 1. CTO #5 remediation scorecard (7 items)

| ID | CTO #5 ask | Status | Evidence |
|---|---|---|---|
| **R1** | Run a REAL reference pilot + publish an A/B (G-035/G-043) | **PARTIAL — buildable-half DONE, pilot buyer-blocked (honest)** | Stage 32 shipped the full free/local pilot package: `pilot-charter-template.md` (predefined success criteria + Scale/Iterate/Pivot/Stop gates + 2 hard gates), `capability-readiness-matrix.md` (honest sim-vs-real inventory, every number cited to its results file + G-035 dependency), `pilot-ab-protocol.md`. The actual pilot + real-world A/B remain buyer-blocked — correctly not faked. |
| **R2** | Wire the two go-live safety/identity surfaces (R4 A2A live mTLS auth; R5 sil_bridge re-validate) | **PARTIAL — A2A auth DONE; sil_bridge re-validate STILL OPEN** | Stage 27 delivered real SPIFFE/SPIRE identity + **A2A authentication on the mTLS path** (peer SPIFFE ID extracted from the verified client cert via XFCC, trust-domain/allowlist checked, foreign-domain rejected) — G-4/G-064-Network CLOSED on the mTLS path. **But G-075 (sil_bridge trusts caller-set `decision.allow`/`route`; forgeable/TOCTOU) is STILL OPEN** — deferred again to "first real PLC caller." This is now the longest-lived open safety item (since Stage 17 / CTO #4). Sim-only, not a live breach, but must be closed before any real actuation. |
| **R3** | Accredited functional-safety certification (G-011) | **DEFERRED (honest) — needs an accredited body** | Path defined in `iso-10218-risk-assessment.md §5`; unchanged this arc. Correctly named as needing an accredited IEC-61508/ISO-13849-1 body + a certified PLC + a real cell. |
| **R4** | EU provider obligations once a legal entity engages | **DEFERRED (honest) — needs a legal-entity provider** | Declaration of Conformity remains a labelled REHEARSAL; unchanged. Correctly deferred. |
| **R5** | Gate-enforce deep eval leg + observability/detector polish | **HONORED (across Stage 25 + 31)** | Stage 25: `crypto-deep-openssl35` nightly gate + cascade/latency observability UI (`/ops/cascade`, G-021 RESOLVED). Stage 31: learned injection tier (G-077 RESOLVED, held-out 0.9935→1.0/FPR→0) + CONTINUOUS runtime behavioural anomaly monitor (G-064-tail RESOLVED). This is the most fully-honored remediation. |
| **R6** | Horizontal-scale hardening (G-066) | **PARTIAL — foothold DONE, tail deferred (honest)** | Stage 25: `shard_router.py` (sha256 sharding + PG advisory lock + at-most-once ledger; load-proven 8 exactly-once/4 suppressed; the test caught 2 real defects). Multi-node HA + read-replicas + fleet-magnitude load correctly deferred to pilot/cloud (Rule 9). |
| **R7** | Close the low-severity dependency/observability ledger | **MOSTLY HONORED (3 of 5)** | Stage 25 RESOLVED G-060 (pgaudit live), G-067 (Langfuse v3 UI verified live — first bring-up surfaced + fixed 4 real config gaps), G-061 (DVC procedural skill). **Still OPEN (pin-blocked, honest):** G-070 (a2a-sdk needs httpx≥0.28.1) + G-055/G-056 (langchain-core 1.0) — both require a coordinated dependency-refresh increment. |

**Tally: R5 + R7 honored (2); R1/R2/R6 partial with the real-world half correctly buyer/PLC-blocked (3); R3/R4 honestly deferred (2); 0 skipped, 0 faked.** Consistent with the CTO #5 pattern — the buildable halves get built, the real-world halves get named and deferred, nothing is hidden.

---

## 2. Per-stage honesty check (25–32)

| Stage | Independent review | What it claims | Honesty verdict |
|---|---|---|---|
| **25 — post-GA ops** | PASS-WITH-GAPS (different agent, dynamic) | Art-72 sweep live, PQC rotation drill, pgaudit, shard foothold, cascade UI, Langfuse UI | **HONEST.** Ops stage, additive, audit held. Every "RESOLVED" (G-021/G-060/G-061/G-066-foothold/G-067) I cross-checked to real code/config. The 4 must-fix findings were fixed in-stage. Minor: Art-72 evidence-append is best-effort (`try/except→WARN`) — surfaced honestly in the risk register, not hidden. |
| **26 — supply-chain automation** | PASS-WITH-GAPS (different agent — reproduced the A/B to the digit) | 2nd domain of the KB_25 loop; Contract-Net; disruption monitoring; A/B −51%/−98% | **HONEST, with a well-handled scare.** The reviewer's control-arm experiment REFUTED the first disruption-drill claim (the injected 6×-median delay wasn't attributably detected); the team PAID it before close (built the overdue-pending age detector, added a controlled drill with a clean control arm — `supply_drill.json` verified above). The Neo4j crash-loop root-cause (corrupt GDS jar, 742 restarts) was found and fixed. This is exactly the "gaps will appear — ledger and FIX them" discipline (Rule 11b) working. |
| **27 — resilience & anti-fragility** | **PASS** (dynamic, no theatre) | SPIFFE/SPIRE dual-identity; A2A auth on mTLS; durable primitives (EffectLedger/CircuitBreaker/Saga); chaos drills | **HONEST.** Real SVIDs issued (issuer O=SPIFFE), rotation + circuit-breaker chaos drills PASS live, chain verifies. CircuitBreaker raises `CircuitOpenError` (honest, no fabrication). Anonymous fallback named honestly-weaker. G-084 (SPIRE 1h-TTL operational note) ledgered. |
| **28 — GraphRAG + adoption UX + de-mock** | PASS-WITH-GAPS (different agent — reproduced 364→3 to the number) | GraphRAG grounding (honest-empty off-topic); adoption UX (confidence DERIVED from real cosine); **G-082 de-mock**; **G-085 baseline hygiene** | **HONEST — and the most scrutiny-worthy claim in the arc, which held up.** The reviewer independently confirmed the 364→3 change is LEGITIMATE hygiene (venv-scoping) PAIRED with a real de-mock (0 `random.*` in project backend, 0 `Math.random` in frontend src), NOT scope-gaming. Confidence is derived from the retrieval cosine, not a bare score. The 3 minor gaps were fixed in-stage. |
| **29 — conversational factory intelligence** | **PASS** (different agent — re-derived the diagnosis math from scratch) | G-022 ask (grounded/honest-empty); G-023 NL inject (Rule 3 preserved); G-026 active diagnosis (info-gain probe) | **HONEST.** Verifier honest-empty returns the fixed string BEFORE any LLM call; grounded answers cite only REAL handles (adversarial diff = 0 invented); active diagnosis is genuine mutual-information/Bayes (confidence VARIES across faults → derived not constant); Rule 3 confirmed — no actuator emitter in any conversation file. |
| **30 — live-wire self-healing loop** | **PASS** (one minor statistical nit, ledgered) | G-005 repair dispatch (−47.9%); G-025-tail RL shadow (never actuates); G-036 demand forecaster served + fabrication removed | **HONEST.** Reviewer re-ran the A/B (48.2%, CI excludes 0 — reproduces −47.9%); interruptible-repair mechanism genuine; passive path byte-equivalent to legacy; RL shadow runs but NEVER acts (determinism holds); fabricated `confidence` deletion confirmed via git diff. Nit: `_ci95` hardcoded t-value for n≠10 → fixed in-stage (n=10 headline already correct). |
| **31 — detector/eval hardening** | **PASS** (different agent — re-implemented the held-out CV from scratch across 3 seeds) | G-077 learned tier (0.9935→1.0/FPR→0 held-out); G-064-tail continuous behavioural monitor | **HONEST — with an important self-disclosed caveat.** StratifiedKFold trains on train-fold only (NOT train-on-test) — confirmed independently. **The reviewer surfaced the right caveat: the 217-example corpus is nearly perfectly separable in bge space, so the "1.0" is a small SINGLE-CORPUS number** — real-traffic/multilingual validation correctly deferred to a pilot. The team did not overclaim generalisation. |
| **32 — pilot-readiness package** | **PASS** (honesty/number-provenance audit) | Pilot charter + capability-readiness matrix + A/B protocol; docs-only | **HONEST.** Reviewer verified every headline number in the matrix traces EXACTLY to a closed-stage results file; NO real-world number presented as a deployment result; the 2 hard gates (0 unsafe actuations; chain verifies) are production-ready properties that hold today, correctly distinguished from the sim hypotheses. |

**Independence: verified.** All 8 stages have an `audits/STAGE_NN_independent_review.md` by a DIFFERENT agent than the implementer, all with PASS or PASS-WITH-GAPS verdicts. Several reviews did genuine adversarial reproduction (re-derived the diagnosis math, re-ran the A/Bs, re-implemented the CV, ran a control-arm experiment that refuted a claim). This is the strongest independence posture in the project's history.

---

## 3. Hard-Rule integrity findings

| Rule | Finding |
|---|---|
| **1 / 1a — no fabrication, incl. audit-invisible** | **PASS, and improving.** Real project fabrication = 0 (grep clean both languages). Stage 30 REMOVED an audit-invisible synthetic-constant fabrication (per-day demand `confidence`) — a net honesty gain. The held-out-not-train-on-test framing in Stage 31 is the textbook Rule-1a-aware way to report a classifier number. Residual: the G-082 legacy demo state-manager still serves deterministic hardcoded demo constants (`reliability_score:0.92`, tick-derived stage KPIs) — but these are honestly framed as the superseded demo scaffold (Stage 28 removed the `random.*`), not passed off as real telemetry; the real path is the LangGraph runtime. Not new theatre. |
| **3 — no LLM-direct actuator** | **PASS — held under the two riskiest new features.** Sole actuator emitter is `integrations/vda5050/master.py::dispatch_order` (verified: only definition repo-wide; conversation files reference it only in docstrings). NL-injection LLM is an input parser → produces a Pydantic `InjectedIncident` that enters the SAME validator-gated path as a sensor-fired one. Repair dispatch calls `safety/validator.validate()` under `REPAIR_DISPATCH_CONTRACT` and only calls `world.request_repair(...)` when `allowed and robot_id is not None`. RL shadow never actuates. |
| **9 — free-cost only** | **PASS.** New deps across 8 stages: `spiffe`/`spiffe-tls` (Apache-2.0) in Stage 27 only; all others zero. Groq→Ollama free fallback; OSS/local infra throughout. |
| **10 — carry-forward (KB_24/25 + ledger)** | **PASS.** Each stage folded its ledgered gaps into its ACs (G-005/G-021/G-022/G-023/G-025/G-026/G-036/G-060/G-061/G-064/G-066/G-067/G-077/G-082/G-083 all resolved via their target stages). |
| **11 / 11a / 11b — depth-first, research-first, independent review** | **PASS.** Each build stage has a dated research section (§36–§43) and an independent review. Depth chosen honestly: learned causal discovery, Transformer RUL, MaskablePPO, information-gain diagnosis, GraphRAG, SPIFFE/SPIRE, learned LR detector tier — battle-tested libraries and real methods over toys. The Stage-26 control-arm refutation → fix cycle is Rule 11b working as designed. |
| **2 — no classical-only sigs in new code** | **PASS.** ADRs signed ML-DSA-65 (agent-identity:v2); SPIFFE SVID = transport auth (X.509) is the correct dual-identity split, explicitly NOT the evidence-signing path. |

**No Hard-Rule violation found across Stages 25–32.**

---

## 4. Production-readiness assessment (real vs. sim/buyer-blocked)

**Genuinely real and load-bearing TODAY (free/local):**
- Fabrication-free codebase (audit=3, real fabrication 0) — verifiable.
- Verifiable-anytime signed audit chain (10469 rows, exit 0) — EU-AI-Act Art-12 evidence machinery is real.
- Governance MAC/RBAC/traceability live-enforced at the A2A boundary + runtime decision node (CTO #5 verified).
- SPIFFE/SPIRE dual identity + A2A authentication on the mTLS path (real SVIDs).
- Durable-execution primitives (EffectLedger/CircuitBreaker/Saga) with signed transition rows.
- Learned injection detector + continuous behavioural monitor (real held-out CV; binding gate stays the validator).
- Conversational grounding with honest-empty abstention + Rule-3-safe NL injection + information-gain active diagnosis.
- Repair-dispatch, RL-shadow, demand-forecaster served into the loop (all gated/shadow-only/honest-labelled).

**Proven only in SimWorld / on benchmark / single-corpus (the honest limitation):**
- Repair −47.9%, supply −51%/−98% → SimWorld studies.
- Detector 1.0/FPR 0.0 → 217-example single corpus (near-separable in bge space, as the reviewer noted).
- GraphRAG 1.0 → 4-SOP corpus. RUL RMSE 13.80 → C-MAPSS FD001.
- All await real-data re-fit/validation (G-035).

**Buyer / accredited-body / legal-entity blocked (correctly deferred, named everywhere):**
- Real reference pilot + published real-world A/B (G-035/G-043).
- Accredited functional-safety certification + certified PLC (G-011).
- CE marking + EU database registration + signed Declaration of Conformity (R4).

**The one open SAFETY item that is NOT purely buyer-blocked:** G-075 (sil_bridge forgeable/TOCTOU). It is sim-only today (no real caller), but it is a code-hardening task that CAN be done now (re-run `validate()` from contract+world_state inside `execute`, or sign+verify the Decision) and should not wait for the pilot to discover it. It has been deferred through CTO #4, #5, and now #6.

---

## 5. Gaps (immediate — for the next governance session)

1. **G-075 sil_bridge Decision forgery/TOCTOU hardening** (medium, safety) — self-validate in `execute` or verify a signed Decision. Longest-lived open safety item; do it as code-hardening now, don't keep deferring to "first PLC caller." → Stage 33.
2. **Risk-register refresh for Stages 29–32** (low, hygiene) — the most recent dated refresh block is the Stage-25 Q3 refresh; 26–32 rows are implied but the register should carry an explicit 29–32 refresh (conversational-injection Rule-3 posture, repair-dispatch gate, detector single-corpus caveat). → Stage 33.
3. **Always-on runtime hook for the behavioural monitor** (low) — Stage 31's `behavioral_monitor` consumes `run_incident` results post-hoc; wire it as a continuous online hook in the runtime so it runs on 100% of live incidents, not just eval. → Stage 33.

## 6. Vulnerabilities

- **G-075 (medium)** — `backend/safety/sil_bridge.py`: gates only on caller-settable `decision.allow`/`route`; a forged/stale `Decision` actuates. NOT a live breach (sim-only; the real actuator path `master.dispatch_order`→`validate_order` is gated), but the defence-in-depth claim only holds for validator-produced decisions. See §5.1.
- **G-084 (low, operational)** — SPIRE agent SVID 1h TTL; a lapsed SVID + consumed join-token makes the agent exit and unable to re-attest until re-bootstrapped. For CI/long-lived deployments use the auto-renewing `workload_x509_source` or an SVID-renewer sidecar.
- No new injectable/authz vulnerabilities introduced by the conversational or repair surfaces (Rule 3 verified intact).

## 7. Missing implementations / theatre check

- **Theatre: none found.** Grep clean; every headline traces to a real results file; every deferral is labelled. The Stage-26 disruption-drill claim that WAS wrong was caught by the independent reviewer and fixed before close (not shipped as theatre).
- **Missing (honestly, all ledgered):** real-data validation everywhere (G-035); multi-turn dialogue memory for the conversation endpoints (single-turn today); frontend real-data wiring for the 5 bespoke visual pages + type drift (G-032/G-047); pgoutput WAL for non-PG CDC sinks (G-068); bidirectional CDC-triggers-problem (G-024); dep-refresh (G-055/G-056/G-070).

## 8. Cross-cutting risks

1. **Sim-to-real is the entire remaining risk surface.** Eight stages of deep, honest capability all rest on SimWorld/benchmark evidence. A pilot could reveal that a headline (repair −47.9%, detector 1.0) does not survive real telemetry/traffic. This is disclosed everywhere and Stage 32 built the conversion package — but the CTO-level risk is that the flywheel never spins because no buyer engages (G-012 pre-revenue). **The single highest-leverage next action is a real pilot, not more building.**
2. **The single-corpus detector number invites over-reading.** "Injection detection 1.0 / FPR 0.0" is true and honestly caveated in the ADR/review, but it will get quoted without the caveat. Ensure the capability-readiness matrix's caveat travels with the number in any external material.
3. **Safety hardening debt (G-075) is aging.** Deferring a known forgery/TOCTOU gap across three checkpoints is defensible while sim-only, but it becomes a go-live blocker the moment a real PLC is wired. Close it as code-hardening before the pilot needs it.
4. **Dependency-refresh debt is compounding** (G-055/G-056/G-070 — langchain-core 1.0 + a2a-sdk, both pin-blocked). Each stage correctly defers it, but it needs a dedicated increment before the pins drift further from upstream security patches.

---

## 9. Future-task remediations (routed)

| ID | Remediation | Target |
|---|---|---|
| C6-R1 | **Harden `sil_bridge.execute` against Decision forgery/TOCTOU (G-075)** — re-run `validate()` from contract+world_state inside `execute` (or sign+verify the Decision); narrow the defence-in-depth wording to match. Code-hardening, do NOT keep deferring to "first PLC caller." | Stage 33 |
| C6-R2 | **Dedicated dependency-refresh increment (G-055/G-056/G-070)** — coordinated langchain + langgraph major bump to langchain-core 1.x, adopt `a2a-sdk` + `langchain-mcp-adapters` once httpx unpins; full live re-test; refresh SBOM. | Stage 33 (dep-refresh) |
| C6-R3 | **Always-on runtime hook for the behavioural monitor** + multi-turn dialogue memory / chat-history persistence for the conversation endpoints (incremental over Stage 29/31). | Stage 33 |
| C6-R4 | **Risk-register refresh for Stages 29–32** + carry the single-corpus detector caveat into any external-facing material. | Stage 33 |
| C6-R5 | **Frontend real-data wiring** for the 5 bespoke visual pages + fix the type drift (G-032/G-047) so `ignoreBuildErrors` can be turned off. | frontend cleanup stage |
| C6-R6 | **Run a REAL reference pilot + publish a real-world A/B (G-035/G-043)** — re-fit all proxy/benchmark models on real site telemetry per the Stage-32 charter; convert every sim headline to real evidence. The single biggest fundability gap; buildable package is ready. | real engagement / pilot |
| C6-R7 | **Accredited functional-safety certification (G-011)** + **EU provider obligations (R4)** — engage an accredited IEC-61508/ISO-13849-1 body + certified PLC; complete conformity assessment, sign the DoC, CE-mark, register in the EU database once a legal-entity provider engages. | real engagement |
| C6-R8 | **Horizontal-scale tail (G-066 tail)** — multi-node HA + read-replicas/partitioning + fleet-magnitude load test; **SPIRE SVID auto-renew (G-084)** for CI/long-lived deployments. | pilot/cloud |
| C6-R9 | **Supply-chain detector sensitivity-floor complementary detector (G-083 residual b, ~6.4×-median floor)** — a complementary signal; pilot-time option, disclosed today. | pilot-time |

---

## 10. Prior-CTO-checkpoint remediation verification

- **CTO #5 (Stages 22–24):** verified above (§1) — 2 honored / 3 partial (buildable-half done, real-half buyer/PLC-blocked) / 2 honestly deferred / 0 skipped. The must-not-regress items from CTO #5 held: audit chain still green (10469 rows, exit 0 — the CTO #4 chain-break stayed fixed); governance still live-enforced; no fabrication regression (in fact improved to a project-true 3).
- **Older open items (spot-checked in the ledger):** G-035/G-043 (pilot) and G-011 (cert) correctly still OPEN and buyer/body-blocked; G-075 still OPEN (see C6-R1); G-024 (bidirectional CDC), G-045 (slice decision persistence), G-051 (Stage-6 relaxed verify) still OPEN and honestly ledgered. No "RESOLVED" claim I spot-checked (G-005/G-021/G-022/G-023/G-025/G-026/G-036/G-060/G-061/G-064-tail/G-066-foothold/G-067/G-077/G-082/G-083) was found to be over-claimed — each maps to real, verified code.

---

### Bottom line

**ON TRACK.** Stages 25–32 are the disciplined, honest continuation the project needs: the de-mock finally made the audit count mean what it says (project fabrication = 0), every headline reproduces and is honestly labelled, the Hard Rules held under significant new surface area, and independence is stronger than ever (reviewers re-derived math and ran refuting experiments). The system is genuinely pilot-DEPLOYABLE and theatre-free. It is NOT yet pilot-PROVEN — all the impressive numbers are SimWorld/benchmark/single-corpus, disclosed everywhere. The right next move is a real pilot (C6-R6), with one piece of overdue in-house hygiene first: close the aging sil_bridge forgery gap as code-hardening (C6-R1) before a real PLC ever reaches it. Nothing here is faked; the remaining big wins require the real world, and the project says so plainly.
