# ADR — Stage 35: Multi-turn dialogue memory for the conversational endpoints (CTO #6 C6-R3 tail)

- **Date:** 2026-07-18
- **Status:** Accepted
- **Stage:** 35 (`tasks/STAGE_35_multi_turn_dialogue_memory.md`) — the last routed CTO-#6 **C6-R3** item (multi-turn
  dialogue memory over the Stage-29 conversational endpoints).
- **Roles:** `backend-engineer` (session store + endpoint wiring) + `agentic-governance-engineer` (grounding-invariant
  preservation).
- **Research:** `research/initial-research.md §46` (multi-turn conversational memory: sliding window vs. summarization;
  the grounding invariant) — appended BEFORE implementing (Hard Rule 11).

## Context

The Stage-29 `/factory/ask` + `/factory/inject` endpoints are SINGLE-TURN — an operator must re-state context on every
question. CTO #6 routed multi-turn dialogue memory (C6-R3 tail) as an incremental in-house item. The hard constraint:
adding history must NOT weaken the Stage-29 grounding/Verifier honest-empty invariant (the anti-hallucination property).

## Decisions & outcomes

1. **Durable sliding-window session store.** `backend/conversation/session_store.py`: a Postgres `conversation_turns`
   table (lazy-create), keyed by `session_id`; `append_turn` / `recent_turns(window=N)` / `format_history`. Sliding
   window (last N turns) over summarization — the robust choice for the typical short operator dialogue, no
   over-summarization risk (research §46.1). Honest-degrading: no DB → `append`=False / `recent`=`[]` (single-turn
   behaviour, never a fabricated history). No new deps (psycopg present).
2. **Wired into `/factory/ask`** (`ask_factory(session_id=)`): the last N turns are loaded as a DIALOGUE HISTORY block
   passed to the LLM for phrasing/coreference; the user Q + the answer are appended. **The grounding invariant is
   preserved:** the evidence bundle is still gathered for the CURRENT question, honest-empty ("I have no evidence for
   that.") still fires when nothing grounds it (even inside a session), and the history is EXPLICITLY labelled
   "for coreference/phrasing only — NOT evidence" and never cited.
3. **Wired into `/factory/inject`** (`parse_incident/inject_and_run(session_id=)`): the history is passed to the LLM
   parse so it resolves coreference ("it is getting worse" → the machine named earlier) into the validated
   `InjectedIncident`. **Hard Rule 3 unchanged** — the LLM still only produces a proposed structured incident that
   enters the same validator-gated loop; history aids the parse, it does not actuate.

## Honesty notes (Rule 1a — verified)

- **History is never a substitute for evidence.** Verified by test: with a `session_id`, an ungrounded question STILL
  returns the fixed honest-empty string, and prior turns are never in the evidence/citations. The history block carries
  an explicit "NOT evidence" disclaimer.
- **No fabrication:** the store persists real turns or honest-degrades to `[]` (no fabricated history); no `random.*`.
- **Measured live (Groq):** turn 1 "welding cell 3 is overheating" → machine_crack/target 3; turn 2 "it is getting
  worse, now vibrating too" (pure coreference) → machine_crack/target 3 — genuine cross-turn coreference resolution.

## Consequences

- New: `backend/conversation/session_store.py` + `backend/tests/conversation/test_session_store.py` (6 tests).
  Modified: `conversation/ask.py`, `conversation/nl_inject.py`, `api/conversation_routes.py` (optional `session_id`).
  **New deps: none.** KB_14 + KB_07 updated.
- **Audit holds 3** (`--no-baseline-drop`: additive real code; no new fakery). Conversation regression (Stage 29 + 35)
  = **31 passed**; `verify-audit-chain.py` unaffected.
- Deferred honestly: summarization for very long (20+-turn) sessions (§46.1 over-summarization risk); full
  coreferential GROUNDING in `/factory/ask` (query rewriting) — history currently aids phrasing there, and the inject
  parse resolves coreference. This completes the routed in-house CTO-#6 items except C6-R2 (dependency-refresh, its own
  pin-blocked increment); the real-world items (pilot G-035/G-043, cert G-011, scale G-066) stay buyer-blocked.

## References
- research §46 · `research/stage-explainers/STAGE_35/index.html` · `backend/conversation/session_store.py` ·
  `backend/conversation/{ask,nl_inject}.py` · KB_14 · KB_07 · `audits/CTO_6_review.md` (C6-R3) · ADR
  `2026-07-12_stage29_conversational_factory_intelligence.md` · explainx.ai conversation-history-2026.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-18T08:00:34+00:00 -->
<!-- signature: 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 -->
