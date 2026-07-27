---
status: done
stage: 34
slug: frontend_realdata_honesty
created: 2026-07-13
---

# Stage 34 — Frontend real-data wiring + honesty cleanup (CTO #6 C6-R5)

> The CTO-#6 frontend cleanup: closes **G-047** (catch-path *fabricated* data in `lib/api.ts` + the `model-metrics`
> page's own hardcoded fake model array — the frontend twin of the Rule-1a audit-invisible fabrication class) and
> **G-032** (11 TypeScript errors in `simulation/page.tsx` reading fields the real `SimulationState` doesn't carry,
> masked by `ignoreBuildErrors:true`). Extends the Stage-28 `useLiveState` honest-empty pattern to the last fabricating
> surfaces + turns ON strict build-time type-checking. Research §45. Free/local; frontend-engineer role.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_34/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 28 (the `useLiveState` honest-empty pattern + primary dashboard), 33 (CTO #6 predecessor)
- Decision logs honoured: `2026-07-04_stage28_graphrag_adoption_ux.md`; CTO_6_review.md (C6-R5)
- KB files at minimum version: KB_07 (API contracts — the metrics endpoints)
- Gaps ledger rows pulled in (IDs): **G-047** (frontend catch-path fabrications) + **G-032** (frontend type drift) — CTO-#6 C6-R5; G-027 (free-cost, ongoing)

## Acceptance criteria

- [x] **AC1 (G-047) — no fabricated data in `lib/api.ts`.** Both `getMockModelMetrics`/`getMockEmbodiedComparison` are
  DELETED; `getModelMetrics` returns `{}` and `getEmbodiedComparison` returns `null` on a fetch error / 503 (honest
  unavailable, never fabricated). Verified: `grep -c getMock src/lib/api.ts` = 0.
- [x] **AC2 (G-047) — the `model-metrics` page renders real data or an honest empty-state.** Its own hardcoded fake
  model array is removed; it fetches `/api/metrics/models` and shows an explicit "no live metrics recorded" state that
  points to the model cards + `models/*.metrics.json` (the backend honestly 503s until real metrics are recorded).
- [x] **AC3 (G-032) — `simulation/page.tsx` uses the real `SimulationState` shape.** The System Health panel reads live
  fields (`metrics.current.*`, `scenario`); the 3D scenes map real `Robot[]`/`ProductionStage[]` with a labelled demo
  fallback; the fabricated initial metrics are removed. Verified: `tsc --noEmit` = 0 errors.
- [x] **AC4 (G-032) — strict type-checking is ON.** `next.config.ts` `ignoreBuildErrors` flipped to `false`;
  `npm run build` type-checks strictly and passes (exit 0, all routes generated).
- [x] **AC5 — the frontend is fabrication-clean + no regression.** `grep -rE 'Math\.random|getMock' frontend-nextjs/src`
  = 0 (the honestly-labelled `detRand` deterministic demo layout excepted). Backend audit holds 3; new deps: none.
- [x] **AC6 — research-first (§45) + explainer + independent review.** Research §45 appended BEFORE implementing;
  `research/stage-explainers/STAGE_34/index.html`; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `research/stage-explainers/STAGE_34/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `frontend-nextjs/src/lib/api.ts` | delete the 2 mock generators; `getModelMetrics`→`{}` / `getEmbodiedComparison`→`null` on error (honest) |
| `frontend-nextjs/src/app/model-metrics/page.tsx` | remove the hardcoded fake model array; fetch real `/api/metrics/models` + honest empty-state |
| `frontend-nextjs/src/app/simulation/page.tsx` | map to the real `SimulationState` shape (metrics.current.*, scenario, robot_id→id); remove fabricated init |
| `frontend-nextjs/next.config.ts` | `ignoreBuildErrors: false` (strict type-checking on) |
| `audits/OPEN_GAPS_LEDGER.md` | G-032 + G-047 RESOLVED |

## Files to DELETE

| Path | Reason |
|---|---|
| (inline) `getMockModelMetrics` / `getMockEmbodiedComparison` in `lib/api.ts` | fabricated catch-path data (G-047) |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_07_API_Contracts.md` (frontend consumes real metrics endpoints / honest-empty; G-047/G-032 note)

## Verification commands

```bash
bash scripts/audit.sh                                  # holds at 3 (frontend fabrications were audit-invisible)

cd frontend-nextjs
grep -rE 'Math\.random|getMock' src | grep -v detRand  # 0 (fabrication-clean; detRand demo layout excepted)
node_modules/.bin/tsc --noEmit                          # 0 errors
npm run build                                           # strict type-check ON (ignoreBuildErrors:false) -> exit 0
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — the removed frontend fabrications were audit-INVISIBLE object literals
  (`getMock*` / hardcoded arrays), so the grep count is unchanged; the honesty gain is real but grep can't see it. No
  new `Math.random`/mock introduced.

## Role

- Primary: `frontend-engineer` (Next.js real-data wiring + strict types)
- Secondary: `agentic-governance-engineer` (honesty discipline)

## Risks / unknowns

- The 5 bespoke visual pages (factory/manufacturing/robotics/supply-chain) + the simulation 3D scenes use a
  DETERMINISTIC demo layout (`detRand`) as fallback geometry — honestly labelled (Stage 28), NOT claimed as real
  telemetry; per-visual real-data wiring of every bespoke element is incremental (the primary dashboard + model-metrics
  + simulation System Health now read real data). Visual/interaction correctness of the 3D scenes is not browser-verified
  here (no running-app screenshot); the change is type-checked + build-verified.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

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

## Pre-populated by start-task.sh (2026-07-13T15:49:19Z)

### Suggested role (from slug heuristic)

**frontend-engineer** — open `.claude/skills/frontend-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_TASK_LOG.md`
- `knowledge-base/KB_07_API_Contracts.md`
- `knowledge-base/KB_08_Frontend_Pages_Spec.md`
- `knowledge-base/KB_09_UX_Scenarios.md`

### Pre-requisites (from previous stage's hand-off — STAGE_33_safety_oversight_hardening.md)


- What is now true that wasn't before this stage:
  - The longest-lived open safety item (G-075) is CLOSED: a forged/stale/wrong-action Decision can no longer actuate
    via `sil_bridge` (capability tokens + mandatory re-validation).
  - The behavioural monitor runs on 100% of live incidents (gated on); the risk register covers Stages 29–33.
- What the next task starts with:
  - The remaining CTO #6 in-house items: C6-R2 (dependency-refresh — its own dedicated increment) + C6-R3 tail
    (multi-turn dialogue memory) + C6-R5 (frontend real-data wiring). The big real-world items (pilot G-035/G-043,
    cert G-011, scale G-066) stay buyer/accredited-body-blocked.
- Open items deferred to a future stage:
  - C6-R2 dependency-refresh (langchain-core 1.x + a2a-sdk, pin-blocked — dedicated increment).
  - The real pilot + certification (buyer/accredited-body-blocked).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
