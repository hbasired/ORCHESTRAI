# ADR — Stage 34: Frontend real-data wiring + honesty cleanup (G-047 + G-032)

- **Date:** 2026-07-13
- **Status:** Accepted
- **Stage:** 34 (`tasks/STAGE_34_frontend_realdata_honesty.md`) — the CTO-#6 **C6-R5** frontend cleanup (post-arc
  in-house hygiene).
- **Roles:** `frontend-engineer` (Next.js real-data wiring + strict types) + `agentic-governance-engineer`
  (honesty discipline).
- **Research:** `research/initial-research.md §45` (honest-empty over fabricated fallback; strict type-checking) —
  appended BEFORE implementing (Hard Rule 11). Honest note: the live web-search leg was rate-limited this session, so
  §45 grounds the decision in the project's OWN established pattern (Stage-28 `useLiveState`), not invented citations.

## Context

Two long-open frontend gaps CTO #6 routed to a frontend cleanup stage: **G-047** — `frontend-nextjs/src/lib/api.ts`
returned hardcoded FABRICATED metrics on a fetch error (`getMockModelMetrics`/`getMockEmbodiedComparison`), and the
`model-metrics` page shipped its OWN separately-hardcoded fake model array — the frontend twin of the Rule-1a
audit-invisible fabrication class (TS object literals, so `audit.sh`'s grep can't see them). **G-032** — 11 TypeScript
errors in `simulation/page.tsx` reading fields the real `SimulationState` doesn't carry, masked by
`next.config.ts ignoreBuildErrors:true`.

## Decisions & outcomes

1. **G-047 — no fabricated data.** Deleted both `getMock*` generators; `getModelMetrics` returns `{}` and
   `getEmbodiedComparison` returns `null` on a fetch error / a backend 503 (the metrics endpoints honestly 503 until
   real metrics are recorded — the frontend now matches that honesty instead of fabricating). Rewrote the
   `model-metrics` page: removed the hardcoded fake model array; it now FETCHES `/api/metrics/models` and renders real
   metrics OR an explicit "no live metrics recorded" empty-state that points to where the real, measured numbers live
   (`compliance/model-cards/` + `models/*.metrics.json`). This extends the Stage-28 `useLiveState` honest-empty pattern
   (already used by the primary dashboard) to the last fabricating surfaces.
2. **G-032 — real state shape + strict type-checking.** `simulation/page.tsx` now maps to the REAL `SimulationState`:
   the System Health panel reads live fields (`metrics.current.conflicts`/`robot_collisions`/`bottlenecks`/
   `overall_score`, `scenario`) instead of the stale schema (`mode`/`conflicts_detected`/`overall_health`); the 3D
   scenes map real `Robot[]`/`ProductionStage[]` (`robot_id`→`id`) with a labelled deterministic demo-layout fallback;
   the fabricated initial metrics (`robot_issues: 2`, `overall_health: "degraded"`) are removed. `ignoreBuildErrors`
   flipped to `false` — `tsc --noEmit` = **0 errors** and `npm run build` type-checks strictly (**exit 0**, all routes
   generated).

## Honesty notes (Rule 1a — verified)

- **The frontend is now fabrication-clean:** `grep -rE 'Math\.random|getMock' frontend-nextjs/src` = 0 (the
  honestly-labelled `detRand` deterministic demo layout — used only as 3D-scene fallback geometry, never claimed as
  real telemetry — excepted). The removed fabrications were audit-INVISIBLE (object literals), so `audit.sh` still
  reads 3 — the honesty gain is real but grep can't see it (documented for the reviewer; same class as the Stage-30
  `confidence` removal).
- **Scope honesty:** the 5 bespoke visual pages + the 3D scenes still use a labelled demo layout as fallback geometry;
  the primary dashboard + model-metrics + simulation System Health now read real data. Per-visual real-data wiring of
  every bespoke element is incremental. Visual/interaction correctness of the 3D scenes is not browser-verified here
  (no running-app screenshot) — the change is type-checked + build-verified.

## Consequences

- New: `research/stage-explainers/STAGE_34/index.html`. Modified: `frontend-nextjs/src/lib/api.ts`,
  `app/model-metrics/page.tsx`, `app/simulation/page.tsx`, `next.config.ts`, `audits/OPEN_GAPS_LEDGER.md`, KB_07.
  **No backend code touched; new deps: none.** G-047 + G-032 marked RESOLVED.
- **Audit holds 3** (`--no-baseline-drop`: the removed frontend fabrications were audit-invisible; no new
  `Math.random`/mock introduced). Verification: `tsc --noEmit` 0 errors; `npm run build` exit 0 with strict
  type-checking; `grep getMock` 0; backend `verify-audit-chain.py` unaffected.
- Deferred honestly: per-visual real-data wiring of every bespoke element (incremental); the ESLint eslintrc→flat-config
  migration (`ignoreDuringBuilds` stays on — separate from type safety); C6-R2 dependency-refresh (pin-blocked); the
  real-world items (pilot G-035/G-043, cert G-011, scale G-066) stay buyer/accredited-body-blocked.

## References
- research §45 · `research/stage-explainers/STAGE_34/index.html` · `frontend-nextjs/src/lib/api.ts` ·
  `frontend-nextjs/src/app/{model-metrics,simulation}/page.tsx` · `frontend-nextjs/next.config.ts` · KB_07 ·
  G-047 / G-032 (`audits/OPEN_GAPS_LEDGER.md`) · `audits/CTO_6_review.md` (C6-R5) · Stage-28 `lib/liveState.ts`
  (`useLiveState` honest-empty precedent).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-18T07:05:24+00:00 -->
<!-- signature: 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 -->
