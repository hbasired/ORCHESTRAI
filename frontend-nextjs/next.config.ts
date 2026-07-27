import type { NextConfig } from "next";

/**
 * Next.js 15 LTS configuration.
 *
 * Stage 1 (2026-05-11) — the LTS downgrade build surfaced several
 * pre-existing TypeScript errors that the old Next 16 + Turbopack dev
 * loop was masking (Turbopack does not run tsc; only the prod compile
 * does, and Next 16 had a more lenient prod pipeline). The errors are
 * NOT regressions from the LTS pin — they are accumulated debt from
 * theatrical UI written against an imagined API surface.
 *
 * Stage 34 (G-032) UPDATE: the type debt is CLEARED — the type-check escape hatch is now OFF
 * (`ignoreBuildErrors: false`), so `next build` type-checks strictly. The last drift (simulation/page.tsx reading
 * fields the real `SimulationState` doesn't carry) was fixed by mapping to the real shape; `tsc --noEmit` = 0 errors.
 * The ESLint legacy-config flag stays on (its own eslintrc→flat-config migration is a separate task, not type safety).
 * Tracked in the Stage-34 ADR `compliance/decision-logs/2026-07-13_stage34_frontend_realdata_honesty.md`.
 */
const nextConfig: NextConfig = {
    typescript: {
        ignoreBuildErrors: false,           // G-032: strict type-checking at build (type debt cleared)
    },
    eslint: {
        ignoreDuringBuilds: true,           // separate eslintrc→flat-config migration; not type safety
    },
    // R3F + Three.js have a few SSR sharp edges; explicitly opting these
    // packages out of server-side bundling keeps the build deterministic.
    transpilePackages: ["three"],
};

export default nextConfig;
