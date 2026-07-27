---
status: done
stage: 35
slug: multi_turn_dialogue_memory
created: 2026-07-18
---

# Stage 35 — Multi-turn dialogue memory for the conversational endpoints (CTO #6 C6-R3 tail)

> The last routed CTO-#6 C6-R3 item: the Stage-29 `/factory/ask` + `/factory/inject` endpoints are single-turn. This
> adds a DURABLE (Postgres) sliding-window session store so an operator can hold a coreference-resolving conversation
> ("welding cell 3 is overheating" → "it is getting worse") without re-stating context — while STRICTLY preserving the
> Stage-29 grounding/Verifier invariant (history aids phrasing/coreference; each answer's evidence is still gathered
> per-current-question, honest-empty still fires, prior turns are never cited as evidence). Research §46. Free/local.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_35/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 29 (conversational endpoints), 33/34 (CTO #6 in-house predecessors)
- Decision logs honoured: `2026-07-12_stage29_conversational_factory_intelligence.md`; CTO_6_review.md (C6-R3)
- KB files at minimum version: KB_14 (agent memory architecture), KB_07 (API contracts)
- Gaps ledger rows pulled in (IDs): CTO-#6 **C6-R3** tail (multi-turn dialogue memory); G-027 (free-cost, ongoing)

## Acceptance criteria

- [x] **AC1 — durable sliding-window session store.** `conversation/session_store.py` persists turns in Postgres
  (`conversation_turns`, lazy-create) keyed by `session_id`; `recent_turns(window=N)` returns the last N chronological;
  honest no-op (`append`→False, `recent`→`[]`) when the DB is unreachable — never fabricates history. Verified:
  `tests/conversation/test_session_store.py` (round-trip, sliding window, honest-noop).
- [x] **AC2 — the grounding/Verifier invariant is PRESERVED.** With a `session_id`, an ungrounded question STILL returns
  "I have no evidence for that." (history is never a substitute for evidence), the turn is still recorded, and prior
  turns are never cited as evidence. Verified: `test_ask_honest_empty_still_fires_with_a_session_and_records_the_turn`.
- [x] **AC3 — multi-turn coreference works.** `/factory/ask` (phrasing) + `/factory/inject` (parse coreference) accept
  an optional `session_id`; the LLM resolves "it/the same machine" from the sliding window. Verified live (Groq): turn 1
  "welding cell 3 is overheating" → machine_crack/3; turn 2 "it is getting worse, now vibrating" → machine_crack/3.
- [x] **AC4 — Hard Rule 3 unchanged.** `/factory/inject` still produces a validated `InjectedIncident` that enters the
  same validator-gated loop; history only aids the parse — the LLM never actuates.
- [x] **AC5 — free-cost + no regression.** New deps: none (psycopg present). Audit holds 3. Conversation regression
  (Stage 29 + 35) = 31 passed.
- [x] **AC6 — research-first (§46) + explainer + independent review.** Research §46 appended BEFORE implementing;
  `research/stage-explainers/STAGE_35/index.html`; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/conversation/session_store.py` | durable Postgres sliding-window session store (append/recent/format; honest-degrading) |
| `backend/tests/conversation/test_session_store.py` | 6 tests — round-trip, sliding window, honest-noop, grounding invariant |
| `research/stage-explainers/STAGE_35/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/conversation/ask.py` | `ask_factory(session_id=)` — history for LLM phrasing; grounding stays per-question; records turns |
| `backend/conversation/nl_inject.py` | `parse_with_llm/parse_incident/inject_and_run(session_id/history_block)` — coreference in the parse |
| `backend/api/conversation_routes.py` | `AskRequest`/`InjectRequestBody` gain optional `session_id` |
| `knowledge-base/KB_14_Agent_Memory_Architecture.md` + `KB_07_API_Contracts.md` | multi-turn dialogue memory layer + endpoint change |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive stage |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_14_Agent_Memory_Architecture.md` (multi-turn dialogue memory layer)
- `knowledge-base/KB_07_API_Contracts.md` (`/factory/*` gain optional `session_id`)

## Verification commands

```bash
bash scripts/audit.sh                    # holds at 3 (additive; --no-baseline-drop)

cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing \
  MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5 MEM0_EMBED_DIM=384 HF_HUB_DISABLE_XET=1 \
  python -m pytest tests/conversation/ -q     # 31 pass (25 Stage-29 + 6 Stage-35)
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — additive real code (session store + endpoint wiring); zero new
  `random.*`/mock; the store uses stdlib/psycopg, honest-degrades, never fabricates history.

## Role

- Primary: `backend-engineer` (session store + endpoint wiring)
- Secondary: `agentic-governance-engineer` (grounding-invariant preservation)

## Risks / unknowns

- Summarization for very long (20+-turn) sessions is deferred (research §46.1 — over-summarization risk); the sliding
  window is the robust choice for the typical short operator dialogue.
- Coreference in `/factory/ask` grounding: history aids the LLM's PHRASING, but the evidence is gathered on the current
  question — a pure-coreference follow-up that doesn't ground on its own text returns honest-empty (query-rewriting for
  full coreferential grounding is a future increment); the `/factory/inject` parse DOES resolve coreference (the LLM
  produces the structured incident using history).

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The conversational endpoints are multi-turn: a durable Postgres session store holds the sliding-window dialogue;
    `/factory/ask` + `/factory/inject` resolve coreference across turns (verified live), while the Stage-29
    grounding/Verifier honest-empty invariant is strictly preserved (history is never evidence).
- What the next task starts with:
  - The remaining CTO #6 in-house item C6-R2 (dependency-refresh — its own pin-blocked, risky increment). The
    real-world items (pilot G-035/G-043, cert G-011, scale G-066) stay buyer/accredited-body-blocked.
- Open items deferred to a future stage:
  - Summarization for long sessions; full coreferential grounding (query rewriting) in `/factory/ask`.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-18T07:14:03Z)

### Suggested role (from slug heuristic)

**backend-engineer** — open `.claude/skills/backend-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_TASK_LOG.md`
- `knowledge-base/KB_01_System_Architecture.md`
- `knowledge-base/KB_04_Data_Schema.md`
- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_07_API_Contracts.md`
- `knowledge-base/KB_14_Agent_Memory_Architecture.md`
- `knowledge-base/KB_15_Observability_Evidence_Pipeline.md`
- `knowledge-base/KB_16_A2A_MCP_Protocols.md`

### Pre-requisites (from previous stage's hand-off — STAGE_34_frontend_realdata_honesty.md)


- What is now true that wasn't before this stage:
  - The frontend is fabrication-clean (0 `getMock`/`Math.random` outside the labelled `detRand` demo layout); the
    model-metrics + simulation pages read real backend data with honest empty/unavailable states; strict build-time
    type-checking is ON (`ignoreBuildErrors:false`, `next build` passes).
- What the next task starts with:
  - The remaining CTO #6 in-house items: C6-R2 (dependency-refresh — its own pin-blocked increment) + C6-R3 tail
    (multi-turn dialogue memory). The big real-world items (pilot G-035/G-043, cert G-011, scale G-066) stay
    buyer/accredited-body-blocked.
- Open items deferred to a future stage:
  - Per-visual real-data wiring of every bespoke element (incremental); ESLint flat-config migration
    (`ignoreDuringBuilds` stays on — separate from type safety); C6-R2 dependency-refresh.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
