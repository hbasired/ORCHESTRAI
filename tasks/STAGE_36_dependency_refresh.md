---
status: done
stage: 36
slug: dependency_refresh
created: 2026-07-18
---

# Stage 36 — Dependency-refresh feasibility assessment (CTO #6 C6-R2)

> The last routed CTO-#6 in-house item (C6-R2, the coordinated langchain-core 1.x + a2a-sdk refresh). Handled
> APPROPRIATELY: I attempted the refresh SAFELY via non-mutating `pip install --dry-run` resolution probes, which prove
> it is a CASCADING multi-major migration (langchain/langgraph runtime + fastapi/starlette API + httpx/protobuf) that
> would very likely break the verified GA'd stack in this working env (no isolated staging/CI). So — rather than
> execute a stack-breaking, low-value migration or fake a "done" — this stage DOCUMENTS the exact blockers + a
> de-risked migration plan (`compliance/dependency-refresh-assessment.md`). Docs-only; the working env is UNCHANGED.
> Research §47. Gaps G-055/G-056/G-070 stay OPEN, now with hard evidence attached.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_36/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 35 (CTO-#6 in-house predecessor); CTO #6 done
- Decision logs honoured: `audits/CTO_6_review.md` (C6-R2); the Stage-11/14/18 pin-rationale ADRs
- KB files at minimum version: — (docs-only)
- Gaps ledger rows pulled in (IDs): CTO-#6 **C6-R2**; **G-055** (langgraph/checkpoint skew), **G-056** (langchain-mcp-adapters), **G-070** (a2a-sdk), G-065 (dep hygiene)

## Acceptance criteria

- [x] **AC1 — the refresh was attempted SAFELY (non-mutating).** `pip install --dry-run` resolution probes were run for
  both halves (httpx≥0.28.1+a2a-sdk; langchain-core≥1.0+langgraph+langchain-mcp-adapters); no package was installed.
  Verified: the working env is UNCHANGED (langchain-core 0.3.28 / httpx 0.27.2 / fastapi 0.115.6 / langgraph 0.2.60 /
  starlette 0.41.3) and a safety smoke test still passes.
- [x] **AC2 — the cascade + hard blockers are documented with real evidence.** `compliance/dependency-refresh-assessment.md`
  records the dry-run would-install sets and the confirmed hard conflict (`fastapi 0.115.6` requires `starlette<0.42`
  vs. the langchain-core-1.x chain's starlette 1.3.1; langgraph-checkpoint 4.x re-introduces the Stage-11 Reviver break;
  a2a-sdk pulls protobuf 6.x).
- [x] **AC3 — honest conclusion + de-risked plan.** The doc concludes C6-R2 is NOT safely executable free/local in the
  working env (a cascading multi-major migration; no isolated staging/CI; low value — pins are SBOM/bandit/pip-audit
  gated, not stale-and-vulnerable) and leaves a concrete branch/staging + CI migration plan.
- [x] **AC4 — gaps ledgered honestly.** G-055/G-056/G-070 stay OPEN with the assessment + plan attached; nothing faked
  as "done"; G-065 mitigation reaffirmed.
- [x] **AC5 — docs-only, env unchanged, audit holds 3.** No requirements.txt / lockfile / code changed; new deps: none.
- [x] **AC6 — research-first (§47) + explainer + independent review.** Research §47 (the dry-run evidence) appended;
  `research/stage-explainers/STAGE_36/index.html`; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `compliance/dependency-refresh-assessment.md` | dry-run evidence + hard blockers + honest verdict + de-risked migration plan |
| `research/stage-explainers/STAGE_36/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `audits/OPEN_GAPS_LEDGER.md` | G-055/G-056/G-070 — attach the assessment + plan (stay OPEN, evidenced) |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | docs-only assessment; NO requirements.txt / lockfile / code changed |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)

## Verification commands

```bash
bash scripts/audit.sh                    # holds at 3 (docs-only; --no-baseline-drop)

# the working env is UNCHANGED (the dry-run installed nothing)
cd backend && python -c "import importlib.metadata as m; print(m.version('langchain-core'), m.version('httpx'), m.version('fastapi'), m.version('langgraph'), m.version('starlette'))"
# expect: 0.3.28 0.27.2 0.115.6 0.2.60 0.41.3  (all pinned versions intact)

# reproduce the resolution evidence (non-mutating)
cd backend && python -m pip install --dry-run "langchain-core>=1.0" "langgraph>=0.3" "langchain-mcp-adapters" 2>&1 | grep -i 'would install'
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — DOCS-ONLY feasibility assessment; NO requirements/lockfile/code changed;
  the working env is unchanged; zero fakery patterns introduced.

## Role

- Primary: `devops-sre` (dependency / supply-chain hygiene)
- Secondary: `agentic-governance-engineer` (honest deferral + evidence discipline)

## Risks / unknowns

- The assessment is a DEFERRAL, not a fix — G-055/G-056/G-070 stay OPEN. The honest risk it names: the frozen pins may
  miss upstream security patches (G-065), mitigated today by the SBOM + bandit + `dependency-exceptions.md`. The actual
  migration (langchain 1.x + fastapi major + httpx/a2a) needs a dedicated branch/staging + CI the project lacks
  free/local — attempting it in the working env would risk the verified GA'd stack.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - C6-R2 is honestly resolved as far as is safe free/local: attempted (dry-run), proven a cascading stack-breaking
    migration, and documented with hard evidence + a de-risked plan. The working env is unchanged; nothing faked.
  - **All routed CTO-#6 in-house items are now addressed (C6-R1 G-075 ✓ Stage 33, C6-R3 hook ✓ Stage 33, C6-R4 ✓
    Stage 33, C6-R5 ✓ Stage 34, C6-R3-tail ✓ Stage 35, C6-R2 assessed ✓ Stage 36).**
- What the next stage starts with:
  - Only real-world engagement remains (pilot G-035/G-043, cert G-011, scale G-066 — buyer/accredited-body-blocked) OR
    the actual dep-refresh migration when a dedicated branch/staging + CI exists.
- Open items deferred to a future stage:
  - The dep-refresh migration itself (G-055/G-056/G-070) → a dedicated branch/CI increment per the plan; G-065 hygiene.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-18T08:08:43Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_35_multi_turn_dialogue_memory.md)


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

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
