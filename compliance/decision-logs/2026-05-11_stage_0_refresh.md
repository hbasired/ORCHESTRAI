# ADR — Stage 0 refresh: plan update + KB bootstrap

- **Date**: 2026-05-11
- **Status**: accepted
- **Stage**: 0 (planning)

## Context

The original master plan was written on 2026-05-04. By 2026-05-11, several developments warranted a refresh:
1. The EU AI Act high-risk obligations enforcement date (2 Aug 2026) is now ~12 weeks out and is the gating compliance event for any EU pilot.
2. NIST released the AI RMF Agentic Profile in Feb 2026, formally enumerating new attack vectors (prompt injection via tool outputs, cross-session memory persistence, tool-chain poisoning) that our RAG-over-system-state design is directly exposed to.
3. The multi-agent framework landscape consolidated: LangGraph won (AutoGen in maintenance after Microsoft pivot to its broader Agent Framework).
4. Industrial PdM SOTA shifted to multi-scale Transformers (MsFormer); world-model SOTA shifted to JEPA-style (LeWorldModel single-GPU stable).
5. NVIDIA Isaac Sim went Apache 2.0; warehouse digital twins are now free to generate.
6. MVTec AD's research-only license was flagged as a pilot-deployment blocker.
7. PRD specified <500 ms decision latency but the plan had no per-hop budget.

## Decision drivers

- Pilot-readiness must be possible for EU customers without re-architecting later.
- Demo failure modes (Groq outage during VC call, Colab session death, dataset 404) must have documented fallbacks.
- The plan must remain executable in ~30 weeks of solo bandwidth without scope creep.
- Honesty discipline: nothing in the plan should claim a model is working when it's a `random.uniform()` fallback.

## Considered options

### Option A — Full rewrite of the master plan

**Pro**: Cleanest expression of the new reality.
**Con**: Loses the audit + research trail that grounded the original plan. Future sessions can't see how thinking evolved.

### Option B — Surgical edits to the master plan + append-only research update + create KB folder (CHOSEN)

**Pro**: Preserves the original plan as a historical record (Appendices A–C, original audit, original research stay intact). Adds a "Stage 0.5 — Refresh Log" section + per-stage update bullets. Research file gets a new Section 6 with all May-2026 findings, tagged. KB folder bootstraps the cycle protocol from this stage onward.
**Con**: Slightly longer documents.

### Option C — Defer the refresh to Stage 1's actual code work

**Pro**: Less planning overhead.
**Con**: Stage 1 task doc would be written without the refresh insights; EU AI Act scaffolding would land too late.

## Outcome

Option B was chosen.

Concrete deliverables shipped in this stage:
- `research/initial-research.md` — appended Section 6 (May 2026 refresh) with the audit re-verification, 12 new findings, and updated source rollup.
- `yor-are-an-agentic-optimized-cookie.md` — inserted "Stage 0.5 — Refresh Log" + per-stage "Update (2026-05-11)" bullets on all 15 stages.
- `knowledge-base/` folder created with 13 files (README + 11 body + TASK_LOG), seeded with audit + research + refresh deltas.
- `compliance/` folder created (risk-register, model-cards/, decision-logs/, human-oversight, incident-playbook) — EU AI Act + NIST RMF Agentic Profile structure.
- `scripts/audit.sh` created — the recurring re-audit script that gates every stage close.
- `tasks/STAGE_01_foundation_and_kb.md` created — the initial executable task document.
- `tasks/TASKS_README.md` created — the one-pager explaining the iterative cycle.

No code in `backend/` or `frontend-nextjs/` was touched. Stage 1 owns the first code changes.

## Subordinate decisions (locked at Stage 0)

- **Coordinator substrate**: bespoke for Stages 1–10, LangGraph migration evaluated at Stage 11.
- **Defect dataset**: Real-IAD primary, MVTec AD secondary (research-only, comparison-only).
- **Simulation library**: SimPy, not SALABIM. SALABIM logged as v2 fallback if animation pipeline becomes a bottleneck.
- **World model**: LSTM v1, LeWorldModel/JEPA-2026 v2 swap behind stable interface.
- **Frontend stack**: pin Next 15.x LTS + React 18.3 + Tailwind 3 LTS (drop bleeding-edge Next 16/React 19/Tailwind 4 to avoid demo-day breakage).
- **LLM fallback**: Ollama-local is the mandatory fallback when Groq is unreachable (Stage 11 acceptance criterion).

## Consequences

- Stage 1 has more scope than the original plan (it now also creates compliance/ scaffolding, the audit script, the KB cycle), but every later stage gets simpler because the structure is in place.
- Decision-log discipline starts here: every architectural decision from now on lives in `compliance/decision-logs/`, including this one.
- The 30-week solo bandwidth estimate becomes harder to hit but more defensible — a pilot diligence call cannot kill the deal in the first hour due to missing compliance scaffolding.

## Links

- Original plan: `yor-are-an-agentic-optimized-cookie.md`
- Original research: `research/initial-research.md` Sections 1–5 + new Section 6
- Stage 1 task doc: `tasks/STAGE_01_foundation_and_kb.md`
- EU AI Act Article 6 + Annex III: https://artificialintelligenceact.eu/article/6/
- NIST AI RMF Agentic Profile (Feb 2026): https://labs.cloudsecurityalliance.org/agentic/agentic-nist-ai-rmf-profile-v1/
- LangGraph 2026 framework comparison: https://gurusup.com/blog/best-multi-agent-frameworks-2026


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:02+00:00 -->
<!-- signature: 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 -->
