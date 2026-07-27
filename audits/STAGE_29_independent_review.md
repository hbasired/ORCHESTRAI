# Stage 29 — Independent Review (Conversational Factory Intelligence)

- **Stage:** 29 — `tasks/STAGE_29_conversational_factory_intelligence.md`
- **Scope:** ask-the-factory (G-022) + NL problem injection (G-023) + active diagnosis (G-026)
- **Reviewer:** `task-auditor` (independent — did NOT implement this stage)
- **Date:** 2026-07-12
- **Method:** read every new/modified source + test file; re-ran the full stage suite (incl. the 2 LIVE Groq tests);
  re-ran `audit.sh` + `verify-audit-chain.py`; wrote an independent throwaway script to reproduce the active-diagnosis
  math from scratch and adversarially probe for fabrication; captured a live Groq answer and checked every cited handle
  against the real signed store.

## TOP-LINE VERDICT: **PASS**

Stage 29 is honest, real, and theatre-free. All seven acceptance criteria independently confirmed. The grounding is
genuine (LLM cites only real audit seqs / SOP ids — zero invented handles), the active-diagnosis math is exact Bayes +
Shannon entropy (reproduced to the digit, confidence genuinely *derived* not constant), Hard Rule 3 is preserved (the
conversation subsystem never emits an actuator command), and the audit baseline holds at 3 with no new fabrication and
no new dependencies. No close-blocking gaps. One cosmetic wording nuance (non-blocking) noted below.

## Claim-by-claim evidence table

| # | Claim | What I independently measured | Verdict |
|---|---|---|---|
| AC1 | **G-022 ask honest-empty (Verifier)** — no evidence → literally "I have no evidence for that.", never fabricates | `test_ask.py::test_honest_empty_...` PASS; code path (`ask.py:57-62`) returns the fixed string + `citations:[]` when `bundle.grounded` is False, BEFORE any LLM call. `test_conversation_routes.py::test_ask_honest_empty` PASS (route level). | **CONFIRMED** |
| AC2 | **G-022 grounded answer cites REAL handles, not invented** | LIVE Groq run: `grounded=True, llm=groq`, citations `['audit:seq=426','audit:seq=424','sop:SOP-001',...]`. Adversarial diff of handles-in-answer-text vs real-evidence-set = **empty (0 invented)**. Seqs 424 & 426 are real `decision.trace` rows in the DB (verified by direct SQL). `test_llm_live.py::test_live_ask_...` PASS (genuinely ran, not skipped). | **CONFIRMED (live)** |
| AC3 | **G-023 Hard Rule 3 preserved** — LLM parses NL → structured incident but NEVER actuates | Grep of `conversation/` + `conversation_routes.py`: the ONLY "actuator/dispatch" mentions are docstrings stating the LLM does not actuate. `master.dispatch_order` (the sole actuator emitter) lives only in `integrations/vda5050/master.py:131` and is called by NO conversation file. `inject_and_run` routes to `world.inject()` (state mutation) + `run_incident` (validator-gated loop). Incident vocabulary matches the real `simulation.entities.incident.IncidentType` enum exactly (Postgres CHECK-constrained). Tests PASS. | **CONFIRMED** |
| AC4 | **G-026 active diagnosis is REAL math** — genuine mutual information, exact Bayes, localizes + abstains, timeout=fault | Independent repro script: `entropy()` = manual Shannon (0.881291 match); Bayes update exact (posterior 0.900000/0.100000 for tpr .9/fpr .1); `expected_info_gain()` = manual MI (0.531004 match); localizes scripted fault s3 @ 0.9733 in 4 probes; ABSTAINS when tpr≈fpr (conf 0.4167, no commit); timeout→fault localizes s2 @ 0.9746. **Adversarial: confidence VARIES across faults [0.9529,0.963,0.9733,0.871] and with tpr → derived, not a constant.** 9/9 tests PASS. | **CONFIRMED** |
| AC5 | **Active diagnosis over LIVE sim; honest-unavailable without a world** | `test_diagnose_honest_unavailable_without_world` PASS (`{"available":false}`); `test_diagnose_localizes_over_a_bound_sim` PASS (localizes `fault:stage-2` over a bound sim via real `snapshot()` probes). Route reads real `world.stages[...].snapshot()`. | **CONFIRMED** |
| AC6 | **Free-cost + no regression + chain intact** | `audit.sh` TOTAL = **3** (= baseline); the 3 hits are all `_generate_heuristic_actions` in the pre-existing `backend/ml/rl_policy.py` (documented G-052 false positive), **none in any Stage 29 file**; Stage 29 files grep clean for theatre patterns. `verify-audit-chain.py` **exit 0** (10,076 rows; hash chain intact; all 9997 post-cutover ML-DSA-65 sigs verify) — and `read_recent` left the chain unmutated. Regression subset **26 passed**. Conversation suite **25 passed** (23 offline + 2 live). New deps: **none** (subsystem imports only fastapi/pydantic/stdlib; requirements.txt diff is accumulated across all uncommitted stages, nothing conversation-specific). | **CONFIRMED** |
| AC7 | **Research-first + explainer + independent review** | `research/initial-research.md §40` present (dated 2026-07-12, sub-sections 40.1/40.2/40.3). `research/stage-explainers/STAGE_29/index.html` present (9994 bytes). This document is the independent review by a different agent. | **CONFIRMED** |

## Fabrication / theatre check (Rule 1a — adversarial)

- **No `random.*` / `Math.random` / mock literals** anywhere in `backend/conversation/` or `conversation_routes.py`.
- **`ask`**: the honest-empty string is a literal *abstention*, not a fabricated answer; the LLM prompt hard-constrains
  to evidence and the live run confirms it cited only real handles + even self-limited ("I have no evidence for the
  specific steps"). The no-LLM path (`_templated_answer`) is a deterministic digest of the SAME real evidence.
- **`active_diagnosis`**: every probability is computed (exact Bayes + Shannon entropy) over a *documented* noisy sensor
  model (tpr/fpr) — diagnostic knowledge, not a synthetic constant. The anomaly thresholds (`torque_z>=3`, `error_rate
  >=0.2`, `defect_rate_effective>=0.08`, `time_broken_seconds>0`) are honest signal thresholds on the real snapshot,
  not fake outputs. Confidence is proven to vary with inputs (adversarial check) → genuinely derived.
- **`nl_inject`**: abstains (returns `None`/`accepted:false`) on an unparseable report; never guesses a type; the LLM is
  an *input parser* only. `InjectRequest` domain validation (target_id required per type) is enforced by the real sim
  schema; a bad parse surfaces as an honest `inject_error`, not a silent fabrication.
- **`audit_chain.read_recent`**: read-only (SELECT only); raises `AuditChainUnavailable` on DB failure so callers
  degrade honestly. Chain verified intact after the suite ran.

## Commands I actually ran (real outputs)

```
$ docker ps  → ai-agent-postgres 0.0.0.0:5544->5432, ai-agent-neo4j 7687, ai-agent-redis 6379 (all up)

$ python -c "...SELECT count(*),max(seq) FROM audit_chain"
  audit_chain rows,maxseq = (10076, 10076)

$ python -m pytest tests/conversation/ -q     # env: DATABASE_URL, MEM0_EMBED_MODEL=bge-small, RUN_EMBEDDER_TESTS=1
  25 passed, 1 warning in 70.79s
  # live-LLM breakdown (NOT skipped):
  test_live_ask_is_grounded_and_cites_real_handles PASSED
  test_live_nl_parse_into_validated_schema         PASSED

$ bash scripts/audit.sh
  heuristic_actions 3 ; all other patterns 0 ; TOTAL 3 ; Baseline 3
  # the 3 hits are all backend/ml/rl_policy.py (pre-existing G-052 false positive), none in Stage 29 files

$ python scripts/verify-audit-chain.py
  hash-chain: 10076 rows; pre-PQC placeholder rows: 79; ML-DSA-65-verified rows: 9997
  Audit chain OK (10076 rows; hash chain intact; all 9997 post-cutover signatures verify)
  EXIT=0

$ python repro_diag.py   # independent from-scratch reproduction
  entropy: manual=0.881291 got=0.881291 match=True
  bayes:   posterior s1=0.900000 s2=0.100000 sums-to-1=True
  info-gain: manual MI=0.531004 got=0.531004 match=True
  localize: committed=True hyp=fault:s3 conf=0.9733 probes=4
  abstain(tpr≈fpr): committed=False abstained=True hyp=None conf=0.4167
  timeout:  probe(s2) timed_out=True anomalous=True → localized fault:s2 conf=0.9746
  adversarial confs across faults: [0.9529, 0.963, 0.9733, 0.871]  (varies → derived, not constant)

$ python -c "ask_factory('...stage torque anomaly / crack risk?', use_llm=True)"   # LIVE Groq
  grounded=True llm=groq
  citations=['audit:seq=426','audit:seq=424','sop:SOP-001','sop:SOP-001','sop:SOP-001']
  invented handles (in text but not real evidence): set()   # ZERO fabricated cites
  $ SELECT seq,action FROM audit_chain WHERE seq IN (424,426)
    (424,'decision.trace','runtime')  (426,'decision.trace','agent:embodied')   # cited handles are REAL rows

$ python -m pytest tests/test_health.py tests/test_websocket_smoke.py tests/memory/ tests/api/test_adoption_routes.py -q
  26 passed

$ grep G-022/G-023/G-026 audits/OPEN_GAPS_LEDGER.md  → all three marked "RESOLVED 2026-07-12 (Stage 29)"

$ grep conversation-specific deps in backend/requirements.txt diff  → none
  conversation subsystem 3rd-party imports: fastapi, pydantic (both pre-existing)
```

## Gaps found

| ID | Severity | Close-blocking? | Note |
|---|---|---|---|
| (obs) | cosmetic | **No** | ADR §3 says active diagnosis "localizes … at 0.96 confidence in ~3 probes." My reproduction (4 stages + `no_fault`, noiseless probe) gives 4 probes and confidence 0.871–0.9733 depending on which stage is faulty. The ADR figure is an honest *approximation* ("~"), within the observed range, and the numbers are genuinely derived — not a fabrication. No action required; could tighten wording if desired. |

No theatre, no bypass, no Hard-Rule-3 breach, no fabrication, no new deps, no baseline regression. Nothing close-blocking;
nothing to append to `OPEN_GAPS_LEDGER.md`.

## Bottom line

**PASS.** Stage 29 delivers a genuinely interactive layer that is honest end-to-end: `ask` answers only from real signed
evidence and abstains otherwise (proven live — zero invented citations), `inject` parses NL to a validated incident that
enters the existing validator-gated loop without the LLM ever actuating (Hard Rule 3 intact), and `diagnose` is a real
information-theoretic active-diagnosis policy (exact Bayes + mutual information, reproduced to the digit, confidence
derived not constant, abstains under ambiguity, timeout=fault). Audit holds at 3 (additive real code, `--no-baseline-drop`
justified), the signed chain verifies (exit 0, 10,076 rows), 25/25 stage tests pass including the 2 live Groq tests, and
no new dependencies were added. G-022/G-023/G-026 are legitimately RESOLVED. Cleared to close.
