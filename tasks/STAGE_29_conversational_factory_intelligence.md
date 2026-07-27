---
status: done
stage: 29
slug: conversational_factory_intelligence
created: 2026-07-12
---

# Stage 29 — Conversational Factory Intelligence

> The interactive/adoption capstone on top of Stage 28's GraphRAG grounding: an operator can now **ask the factory**
> ("what's the status of X" / "why did Y happen?") and get answers grounded ONLY in real evidence (Art-12 signed
> decision traces + Stage-28 GraphRAG + live sim), **tell the factory** about a problem in plain English (parsed to
> a validated structured incident that enters the same validator-gated self-healing loop — Hard Rule 3 preserved),
> and the coordinator runs **active diagnosis** (an information-gain probe policy) to confirm/deny a fault hypothesis
> BEFORE intervening (KB_25 §1b, previously a no-op). Free/local (Groq→Ollama, Rule 9). Research §40; closes
> G-022/G-023/G-026.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_29/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 28 (GraphRAG grounding), 24 (Art-12 decision trace), 13 (CDC), 12 (audit_chain), 11 (runtime), 11.5 (MCP)
- Decision logs honoured: `2026-07-04_stage28_graphrag_adoption_ux.md`, `2026-06-29_stage24_ga.md` (Art-12), `2026-07-02_strategic_audit_and_post_ga_roadmap.md`
- KB files at minimum version: KB_25 (self-healing engine incl. §1b active diagnosis), KB_06 (message protocol), KB_16 (MCP)
- Gaps ledger rows pulled in (IDs): **G-022** (ask-the-factory chatbot), **G-023** (NL problem injection), **G-026** (active diagnosis), G-027 (free-cost, ongoing)

## Acceptance criteria

- [x] **AC1 (G-022) — ask the factory answers ONLY from real evidence, honest-empty otherwise.** `POST /factory/ask`
  gathers real evidence (Art-12 `decision.trace` rows via `audit_chain.read_recent` + Stage-28 GraphRAG + live sim
  snapshot) with citable handles; no evidence → `"I have no evidence for that."` (the Verifier pattern, §40.1).
  Verified: `tests/conversation/test_ask.py` + `test_conversation_routes.py::test_ask_honest_empty`.
- [x] **AC2 (G-022) — the LLM answer is constrained to the evidence and cites handles; degrades honestly.** With a
  free LLM (Groq) it synthesizes a cited answer; with none it returns a deterministic digest of the SAME real
  evidence. Verified live: `test_llm_live.py::test_live_ask_is_grounded_and_cites_real_handles` (Groq answer cited
  `[sop:SOP-001]` + real audit seqs).
- [x] **AC3 (G-023) — NL problem injection parses to a VALIDATED structured incident; Hard Rule 3 preserved.**
  `POST /factory/inject` parses NL → strict Pydantic `InjectedIncident` (LLM structured output, re-ask on failure;
  deterministic keyword fallback; honest abstain on unknown) → the SAME validator-gated self-healing loop; the LLM
  never actuates. Verified: `test_nl_inject.py` + `test_conversation_routes.py` (deterministic + abstain + Rule-3 note);
  live LLM parse in `test_llm_live.py`.
- [x] **AC4 (G-026) — active diagnosis selects probes by information gain, Bayes-updates, commits or abstains.**
  `run_active_diagnosis` picks the max-mutual-information `diagnose.request`, updates the belief exactly (Bayes +
  Shannon entropy), localizes the true fault (incl. timeout=fault), and ABSTAINS when evidence is ambiguous.
  Verified: `test_active_diagnosis.py` (9 tests) + `test_conversation_routes.py::test_diagnose_localizes_over_a_bound_sim`.
- [x] **AC5 — active diagnosis runs over the LIVE sim; honest-unavailable without a world.** `POST /factory/diagnose`
  probes real stage health (`snapshot()`); no bound sim → `{"available": false}`. Verified in `test_conversation_routes.py`.
- [x] **AC6 — free-cost (Rule 9) + no regression + chain intact.** New deps: none. Groq→Ollama only. Audit holds 3
  (additive real code). `verify-audit-chain.py` exit 0 (10,076 rows). Full touched-area regression green.
- [x] **AC7 — research-first (Rule 11) + explainer + independent review.** Research §40 appended BEFORE implementing;
  `research/stage-explainers/STAGE_29/index.html` shipped; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/conversation/__init__.py` | package doc |
| `backend/conversation/evidence.py` | G-022 evidence layer — real decision traces + GraphRAG + live sim with citable handles; never fabricates |
| `backend/conversation/ask.py` | G-022 ask-the-factory — Verifier honest-empty + LLM-constrained cited synthesis + deterministic degradation |
| `backend/conversation/nl_inject.py` | G-023 NL→validated `InjectedIncident` (LLM structured output + deterministic fallback + abstain) → validator-gated loop |
| `backend/conversation/active_diagnosis.py` | G-026 information-gain (entropy) probe policy + exact Bayes belief + commit/abstain |
| `backend/api/conversation_routes.py` | `/factory/ask` + `/factory/inject` + `/factory/diagnose` |
| `backend/tests/conversation/test_ask.py` | ask honest-empty + evidence grounding |
| `backend/tests/conversation/test_nl_inject.py` | deterministic parser + abstain + schema validation |
| `backend/tests/conversation/test_active_diagnosis.py` | entropy/info-gain/Bayes/localize/abstain/timeout (9 tests) |
| `backend/tests/conversation/test_conversation_routes.py` | route smoke (honest degradation everywhere) |
| `backend/tests/conversation/test_llm_live.py` | live Groq path (gated on key+embedder) |
| `research/stage-explainers/STAGE_29/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/memory/audit_chain.py` | add `read_recent(actions, limit, target_substr)` — read-only evidence query over the signed store |
| `backend/main.py` | mount `conversation_routes.router` |
| `knowledge-base/KB_06_Agent_Coordination_Protocol.md` | active-diagnosis message pair now IMPLEMENTED (G-026) |
| `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` | §1b active diagnosis: no-op → information-gain probe policy |
| `knowledge-base/KB_07_API_Contracts.md` | `/factory/*` endpoints |
| `audits/OPEN_GAPS_LEDGER.md` | G-022/G-023/G-026 → RESOLVED |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive stage |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_06_Agent_Coordination_Protocol.md` (active-diagnosis pair now implemented)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (§1b active diagnosis: no-op → info-gain probe policy)
- `knowledge-base/KB_07_API_Contracts.md` (`/factory/*` endpoints)

## Verification commands

```bash
# Audit holds at 3 (additive real code — close with --no-baseline-drop)
bash scripts/audit.sh

# Stage-29 suite (25 tests: 23 offline + 2 live-LLM when GROQ_API_KEY+embedder present)
cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing \
  MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5 MEM0_EMBED_DIM=384 HF_HUB_DISABLE_XET=1 \
  python -m pytest tests/conversation/ -q

# No regression + chain intact + routes mount
cd backend && python -m pytest tests/test_health.py tests/test_websocket_smoke.py tests/memory/ tests/api/test_adoption_routes.py -q
python scripts/verify-audit-chain.py
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — additive real code (new conversation subsystem); zero new
  `random.*`/mock/`RESPONSES={}`/`MODELS=[]` introduced; the legacy de-mock was completed in Stage 28.

## Role

- Primary: `agentic-governance-engineer` (conversational reasoning + traceability + KB_06/KB_25 protocol)
- Secondary: `backend-engineer` (FastAPI routes), `ml-engineer` (LLM grounding / information-gain diagnosis)

## Risks / unknowns

(Append-only as the stage progresses. Convert resolved items to ADRs in `compliance/decision-logs/`.)

-

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The factory is INTERACTIVE: `/factory/ask` (grounded, cited QA + honest-empty), `/factory/inject` (NL → validated
    incident → validator-gated loop), `/factory/diagnose` (information-gain active diagnosis over live sim).
  - The self-healing loop can now be interrogated (KB_25 §1b active diagnosis is real, not a no-op) and driven by
    natural language — both feed the same signed Art-12 evidence trail.
  - `audit_chain.read_recent` gives any surface a read-only, honest query over the signed evidence store.
- What the next stage (30 — live-wire the self-healing loop) starts with:
  - The conversational layer will DRIVE a fully-live loop; Stage 30 wires G-005 (cross-fleet repair dispatch),
    G-025-tail (live RL-intervention), G-036 (demand_forecaster into the live path).
- Open items deferred to a future stage:
  - Real-user conversational + adoption validation needs a pilot (G-035/G-043, buyer-blocked).
  - Multi-turn dialogue memory / chat history persistence (incremental; the current endpoints are single-turn).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-12T10:03:28Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_28_graphrag_adoption_ux.md)

- What becomes true: explanations are graph-grounded + cited (measurably fewer factual errors) and the operator
  experience is persona-shaped + trust-calibrated + progressive-autonomy + WIIFM-framed — the adoption differentiator.
  Real-user adoption validation still needs a real pilot (G-035/043, buyer-blocked).

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
