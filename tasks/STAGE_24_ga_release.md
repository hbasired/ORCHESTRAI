---
status: not-started
stage: 24
slug: ga_release
created: 2026-06-29
---

# Stage 24 — ga_release (TITLE — edit me)

> One-paragraph statement of what this stage is and why it happens now. Cross-link to PRD §, KB files, prior stage hand-off.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_24/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: (list of prior stages this depends on)
- Decision logs honoured: (list of ADRs)
- KB files at minimum version: (list)
- Gaps ledger rows pulled in (IDs): (from `audits/OPEN_GAPS_LEDGER.md`)

## Acceptance criteria

(Independently testable bullets. Each must be verifiable with a command in §Verification commands. Aim for 5–10.)

- [ ]
- [ ]
- [ ]

## Files to CREATE

| Path | Purpose |
|---|---|
| | |

## Files to MODIFY

| Path | Change |
|---|---|
| | |

## Files to DELETE

| Path | Reason |
|---|---|
| | |

## KB files this stage updates

(The KB-diff CI gate enforces these. Every listed file must have a non-trivial diff in the closing PR.)

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_NN_<topic>.md`

## Verification commands

```bash
# Audit baseline strictly decreases (or hold with explicit --no-baseline-drop justification)
bash scripts/audit.sh

# Tests pass
cd backend && pytest -q
cd frontend-nextjs && npm test && npm run build

# Stage-specific
```

## Audit target

- Pre-stage baseline: (capture from `.audit-baseline` at stage open)
- Target: (strictly less than pre-stage; specify expected drop and which patterns fall)

## Role

- Primary: (per CLAUDE.md §3 decision tree — `backend-engineer` / `ml-engineer` / ... )
- Secondary (hand-offs): (list)

## Risks / unknowns

(Append-only as the stage progresses. Convert resolved items to ADRs in `compliance/decision-logs/`.)

-

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-06-29T12:19:33Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_23_conformity_dryrun.md)


- What is now true: the system has been rehearsed for external conformity assessment; gaps surfaced before the real one.
- Next stage (24) is GA release; Stage 24.5 is CTO #5 final audit.

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)
- G-080: **Governance MAC/RBAC/traceability has no live enforcement call site.** `backend/governance/{mac,rbac,traceability}.py` is correct, tested pure-logic (9/9), but�  (target: Stage 24 (GA); status: OPEN � wire MAC `require_read/write` into a data-access path, RBAC `require_function` into the agent dispatch / A2A boundary, and `record_decision_trace` into the runtime decision node; then verify audited rows appear (Docker up).)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
