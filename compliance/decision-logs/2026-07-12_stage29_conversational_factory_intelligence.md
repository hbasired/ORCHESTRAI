# ADR — Stage 29: Conversational Factory Intelligence (ask / inject / active diagnosis)

- **Date:** 2026-07-12
- **Status:** Accepted
- **Stage:** 29 (`tasks/STAGE_29_conversational_factory_intelligence.md`) — first of the operator-chosen post-Stage-28
  arc (29 conversational intelligence → 30 live-wire loop → 31 detector hardening → 32 pilot-prep → CTO #6).
- **Roles:** `agentic-governance-engineer` (traceability/KB_06/KB_25 protocol) + `backend-engineer` (FastAPI) +
  `ml-engineer` (LLM grounding + information-gain diagnosis).
- **Research:** `research/initial-research.md §40` (conversational operational QA + NL→action safety + active/sequential
  diagnosis SOTA) — appended BEFORE implementing (Hard Rule 11).

## Context

The roadmap (PRD v3 §18) ended at Stage 25; Stages 26–28 were the out-of-band strategic-reset extension, now complete
and theatre-free (baseline 3). With no pre-defined next stage, the operator directed building all four remaining
free/local ledger directions as Stages 29–32 capped by CTO #6. Stage 29 is the highest-leverage of these: it makes the
system **interactive** on top of Stage-28's GraphRAG grounding, closing three long-open gaps — G-022 (ask the factory),
G-023 (NL problem injection), G-026 (active diagnosis, KB_25 §1b, previously a no-op).

## Decisions & outcomes (every number a live command this session)

1. **G-022 — "ask the factory" grounded in real evidence, Verifier honest-empty** (`backend/conversation/evidence.py`
   + `ask.py` + `POST /factory/ask`). Evidence is gathered ONLY from real stores — Art-12 `decision.trace` rows (new
   read-only `audit_chain.read_recent`), Stage-28 GraphRAG (SOP + ISA-95), and the live SimWorld snapshot — each item
   carrying a citable handle (`audit:seq=…` / `sop:SOP-…` / `sim:…`). Following the SOTA RCA **Verifier** pattern
   (§40.1), **no evidence → "I have no evidence for that."** (never a fabricated answer). When a free LLM is reachable
   (Groq→Ollama, Rule 9) it synthesizes an answer CONSTRAINED to the evidence that must cite handles (temp 0.1, the
   question re-appended to anchor attention); with no LLM it returns a deterministic digest of the SAME real evidence.
   **Verified live:** the Groq answer cited `[sop:SOP-001]` + real audit seqs 424/426.
2. **G-023 — NL problem injection into the validator-gated loop, Hard Rule 3 preserved** (`nl_inject.py` +
   `POST /factory/inject`). NL is parsed to a STRICT Pydantic `InjectedIncident` (the 2026 structured-output gold
   standard, §40.2): the LLM returns JSON validated against the schema with ONE re-ask on failure; a deterministic
   keyword parser is the offline fallback; both **ABSTAIN honestly** on an unknown report. The parsed incident enters
   `SimWorld.inject()` / the LangGraph self-healing loop exactly like a sensor-fired one — **the LLM never actuates**
   (it is an input parser; the only actuator emitter remains `master.dispatch_order`, validator + trace-paired).
   **Verified live:** Groq parsed "number 3 welding cell vibrating and overheating, urgent" → `machine_crack`,
   target 3, `critical`, conf 0.9.
3. **G-026 — active diagnosis = information-gain probe policy (KB_25 §1b no-op → real)** (`active_diagnosis.py` +
   `POST /factory/diagnose`). The coordinator holds a belief over fault hypotheses (one per candidate agent + a
   `no_fault` hypothesis), selects the `diagnose.request` with **maximum expected mutual information**
   `I(hypothesis; probe_outcome)` (entropy reduction — the classic active-diagnosis formulation, §40.3), reads the
   `diagnose.report` (a real health vector; **timeout/exception ⇒ anomalous = fault**), does an **EXACT Bayes update**,
   and COMMITS only when a posterior clears the confidence threshold — otherwise ABSTAINS/escalates. Misdiagnosis is a
   recorded outcome; each report is best-effort ledged. **Measured (independent-review repro):** over 4 candidate stages
   with a true fault it localizes to the faulty stage at **~0.87–0.97 confidence in ~3–4 probes** — the figure VARIES
   by which stage is faulty and the probe reliability (tpr/fpr), which itself proves the confidence is DERIVED from the
   Bayes/entropy math, not a hardcoded constant; a near-uninformative sensor model (tpr≈fpr) makes it ABSTAIN rather
   than guess. Wired over the live sim stages at `/factory/diagnose` (honest-unavailable without a world).

## Honesty notes (Rule 1a — verified against the actual code path)

- **Nothing here fabricates.** `ask` abstains with a fixed honest string when evidence is empty; the LLM answer is
  constrained to real evidence handles; `inject` abstains on an unparseable report; `diagnose` abstains below the
  confidence threshold. The active-diagnosis probabilities are exact Bayes + Shannon entropy over a DOCUMENTED noisy
  sensor model (true-/false-positive probe rates) — diagnostic knowledge, not a synthetic constant.
- **Hard Rule 3 is preserved on the write path:** `/factory/inject` produces a *proposed structured incident*; the
  actuator boundary is unchanged (validator-gated `master.dispatch_order`). Confirmed by reading the path.
- **Blocking work runs off the event loop:** `ask`/`inject` dispatch the blocking evidence/DB reads and `run_incident`
  via `asyncio.to_thread` — which also lets `graphrag.retrieve`'s internal asyncio loop run (it can't run inside the
  request loop), so the graph leg is not silently dropped.

## Consequences

- New: `backend/conversation/{__init__,evidence,ask,nl_inject,active_diagnosis}.py` +
  `backend/api/conversation_routes.py` + `backend/tests/conversation/` (25 tests: 23 offline + 2 live-LLM gated on
  key+embedder). Modified: `backend/memory/audit_chain.py` (`read_recent`), `backend/main.py` (mount). **New deps:
  none** (Rule 9). KB_06/KB_07/KB_25 updated; G-022/G-023/G-026 marked RESOLVED.
- **Audit holds 3** (`--no-baseline-drop`: additive real subsystem — zero new `random.*`/mock/`RESPONSES={}`/`MODELS=[]`;
  the legacy de-mock completed in Stage 28). `verify-audit-chain.py` exit 0 (10,076 rows; `read_recent` is read-only).
  Regression 53 passed across conversation + health + ws + memory + adoption + audit-signing.
- Deferred honestly: real-user conversational + adoption validation needs a pilot (G-035/G-043, buyer-blocked);
  multi-turn dialogue memory / chat-history persistence is incremental (the endpoints are single-turn today).

## References
- research §40 · `research/stage-explainers/STAGE_29/index.html` · `backend/conversation/*` ·
  `backend/api/conversation_routes.py` · KB_25 §1b · KB_06 · KB_07 · G-022/G-023/G-026 (`audits/OPEN_GAPS_LEDGER.md`) ·
  ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md` · arxiv 2506.22405 (Sequential Diagnosis with LMs) ·
  1207.1418 (entropy test selection) · autoheal.ai agentic-RCA (Verifier pattern).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-12T15:38:23+00:00 -->
<!-- signature: 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 -->
