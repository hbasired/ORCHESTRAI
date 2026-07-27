# Stage 34 — Independent Review (Frontend real-data wiring + honesty cleanup)

- **Stage:** 34 — "Frontend real-data wiring + honesty cleanup" (CTO #6 **C6-R5**; closes **G-047** + **G-032**)
- **Reviewer:** independent `task-auditor` agent (did NOT implement Stage 34)
- **Date:** 2026-07-17
- **Mode:** adversarial fabrication/honesty audit + static read + live build/type-check verification
- **ADR under review:** `compliance/decision-logs/2026-07-13_stage34_frontend_realdata_honesty.md`

## VERDICT: **PASS**

All five claims independently confirmed. The two `getMock*` fabrication generators are gone, error paths return
honest empty (`{}`) / unavailable (`null`), the `model-metrics` page fetches the real endpoint and renders an honest
empty-state (no hardcoded fake model array), `simulation/page.tsx` reads the real `SimulationState` shape,
`ignoreBuildErrors` is `false`, and `tsc --noEmit` + `npm run build` both pass **exit 0 with strict type-checking on**
(a type error would now fail the build). No new deps; frontend-only substantive change. Only cosmetic (non-blocking)
label staleness found.

## Claim-by-claim

| # | Claim | What I ran / read | Verdict |
|---|-------|-------------------|---------|
| 1 | No fabricated data left (G-047): `getMock*` gone; error paths honest | `grep -c getMock frontend-nextjs/src/lib/api.ts` = **0**; READ `api.ts` — `getModelMetrics()` returns `{}` on 503/error, `getEmbodiedComparison()` returns `null`; READ `model-metrics/page.tsx` — fetches `/api/metrics/models`, renders `<EmptyState/>` when list empty, **no hardcoded fake model array** | **PASS** |
| 2 | Frontend fabrication-clean | `grep -rnE 'Math\.random\|getMock\|generateMockState' frontend-nextjs/src \| grep -v detRand` = **0 matches**; `detRand` (simulation/page.tsx:12-18) is a genuine deterministic splitmix32-style PRNG seeded from a constant `0x2f6e2b1`, used only as labelled 3D/demo-layout fallback geometry ("Offline (Mock Data)"), never claimed as real telemetry — consistent w/ Stage 28. `audit.sh`: `math_random_ts` 0, `mock_detections` 0, `generate_mock_state` 0, `get_demo_metrics` 0 | **PASS** |
| 3 | G-032 type drift fixed + strict checking ON | READ `simulation/page.tsx` — reads `state.metrics?.current?.{conflicts,robot_collisions,bottlenecks,overall_score}`, `state.scenario`, `state.events` (real `SimulationState`), fabricated init removed; `grep -n ignoreBuildErrors next.config.ts` → `false`; **`tsc --noEmit` = 0 errors**; **`npm run build` exit 0**, 18/18 routes generated with strict type-check | **PASS** |
| 4 | No overclaim / nothing papered over | READ ADR honesty notes vs reality: removed fabrications ARE audit-invisible object literals → audit holds 3 (**confirmed:** residual 3 = all `heuristic_actions` = the documented G-052 backend false-positive; all frontend categories 0); 3D scenes DO use labelled demo layout (confirmed in code); "build-verified not browser-verified" stated honestly. ADR also honestly discloses the web-search leg was rate-limited (research §45 grounds in the project's own Stage-28 pattern) | **PASS** |
| 5 | Scope: frontend-only, no new deps | `git diff -- package.json package-lock.json` = **0 lines** (no dep change); ADR + ledger scope it frontend-only; all Stage-34 file edits read are frontend/docs. **NOTE:** repo has a single commit ("first commit") so `git diff --stat` shows CUMULATIVE working-tree changes from ALL prior stages — backend/* appears but is prior-stage work, NOT Stage 34 (git cannot isolate one stage here). Substantive scope check holds via the package files + ADR + read files. | **PASS (with repo-state note)** |

## Commands run (outputs)

```
grep -c getMock frontend-nextjs/src/lib/api.ts            -> 0
grep -rnE 'Math\.random|getMock|generateMockState' frontend-nextjs/src | grep -v detRand -> (no matches)
grep -n ignoreBuildErrors frontend-nextjs/next.config.ts  -> 14 (comment), 21: ignoreBuildErrors: false
grep getMock (whole frontend/src)                         -> (no matches)

# tsc --noEmit
(no output)  ->  exit 0

# npm run build (tail)
Route (app)                        Size   First Load JS
┌ ○ /                             5.33 kB   114 kB
├ ○ /model-metrics                3.82 kB   113 kB
├ ○ /simulation                   6.22 kB   148 kB
...  (18 routes, all ○ Static prerendered)
=== build exit: 0 ===

# scripts/audit.sh (tail)
  heuristic_actions   3     <- documented G-052 backend name-pattern false-positive
  math_random_ts      0
  mock_detections     0
  TOTAL               3   (baseline 3; --no-baseline-drop justified: removed frontend fabrications were audit-invisible object literals)
```

## Gaps found

None close-blocking. Minor cosmetic observations only (severity: trivial, NOT close-blocking):

- **Stale section label (cosmetic):** `api.ts` line 265-267 keeps a `// MOCK DATA FOR OFFLINE/DEMO` banner above the
  now-honest `emptyState()` (which returns genuine zeros/empty arrays). The label reads "mock" though the code is
  honest; consider renaming to "HONEST OFFLINE STATE." No fabrication — cosmetic wording only.
- **Dead-but-honest method:** `getEmbodiedComparison()` has no consumer in `frontend-nextjs/src` (only its own
  definition). It returns `null` on error (honest), so this is harmless; could be removed in a later cleanup.
- **Repo-state artifact (informational):** the single-commit repo means `git diff --stat` cannot mechanically isolate
  Stage 34's scope to "frontend + docs only." Scope was instead confirmed via the unchanged `package.json`/
  `package-lock.json` (no new deps) and reading the actual edited files. Not a defect of Stage 34.

## Bottom line

Stage 34 does exactly what it claims and nothing is papered over. Both long-open frontend gaps are genuinely closed:
G-047 (the `getMock*` fabrication generators + the hardcoded fake model array are removed; error/503 paths now return
honest empty/`null`; the `model-metrics` page fetches the real endpoint and shows an honest empty-state) and G-032
(the type drift is fixed against the real `SimulationState` and strict build-time type-checking is turned back ON —
`tsc` 0 errors, `npm run build` exit 0 across all 18 routes). The frontend is fabrication-clean (the only remaining
non-real geometry is the honestly-labelled deterministic `detRand` demo fallback, consistent with Stage 28). The audit
holding at 3 is correct and honestly justified (the removed fabrications were audit-invisible object literals; the
residual 3 is the pre-existing backend G-052 false-positive). No new dependencies, no backend code, no bypassed gate.
**PASS — cleared to close.**
