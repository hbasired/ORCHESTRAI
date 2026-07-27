# ADR — Stage 36: Dependency-refresh feasibility assessment (CTO #6 C6-R2)

- **Date:** 2026-07-18
- **Status:** Accepted
- **Stage:** 36 (`tasks/STAGE_36_dependency_refresh.md`) — the last routed CTO-#6 in-house item (C6-R2). Docs-only
  assessment; no requirements/lockfile/code changed.
- **Roles:** `devops-sre` (dependency / supply-chain hygiene) + `agentic-governance-engineer` (honest deferral +
  evidence discipline).
- **Research:** `research/initial-research.md §47` (the dry-run resolution evidence) — appended BEFORE the decision
  (Hard Rule 11).

## Context

CTO #6 routed **C6-R2** — the coordinated dependency-refresh (langchain-core 1.x to unblock `langchain-mcp-adapters`,
G-055/G-056; httpx≥0.28.1 to unblock `a2a-sdk`, G-070) — as "its own dedicated increment ... full live re-test." The
appropriate way to "do" C6-R2 is to attempt it SAFELY, determine feasibility, and act honestly on the result — not to
force a migration or fake a "done."

## Decision & outcome

**C6-R2 is NOT safely executable free/local in the working env — assessed, documented, and planned, NOT executed.**

1. **Attempted safely (non-mutating).** `pip install --dry-run` resolution probes for both halves. They RESOLVE on
   metadata but reveal a CASCADE: httpx≥0.28.1+a2a-sdk pulls **protobuf 6.x**; langchain-core≥1.0 pulls
   langchain-1.3.14 / langchain-core-1.4.9 / langgraph-1.2.9 / **langgraph-checkpoint-4.1.1** / **starlette-1.3.1**.
2. **Confirmed hard blocker:** `fastapi 0.115.6` declares `starlette<0.42.0,>=0.40.0` — so the langchain-core-1.x
   chain's starlette 1.3.1 conflicts with the pinned fastapi → the refresh FORCES a **fastapi major bump** as well;
   langgraph-checkpoint 4.x re-introduces the Stage-11 `Reviver` break the 0.2.60 pin resolved.
3. **Honest verdict + plan.** A full C6-R2 is a cascading multi-major migration across the runtime (langchain/langgraph),
   the API layer (fastapi/starlette), and the HTTP layer (httpx → a2a/mcp/langfuse). Executing it in this working dev
   env (no isolated staging + no CI gate free/local) would very likely break the verified GA'd stack, for a low-value
   hygiene item (the pins are SBOM-attested + bandit/pip-audit gated under `dependency-exceptions.md`, G-065 — not
   stale-and-vulnerable). So this stage ships `compliance/dependency-refresh-assessment.md`: the dry-run evidence, the
   exact blockers, the current mitigation, and a de-risked branch/staging + CI migration plan.

## Honesty notes (Rule 1a — verified)

- **Nothing faked as done.** G-055/G-056/G-070 stay OPEN (now with hard evidence + a plan attached); the assessment is
  an honest deferral, not a fix. **The working env is UNCHANGED** — verified: langchain-core 0.3.28 / httpx 0.27.2 /
  fastapi 0.115.6 / langgraph 0.2.60 / starlette 0.41.3 (all pinned versions intact); a safety smoke test still passes.
- The dry-run evidence is real + reproducible (`pip install --dry-run "langchain-core>=1.0" ...` — non-mutating).

## Consequences

- New: `compliance/dependency-refresh-assessment.md` + `research/stage-explainers/STAGE_36/index.html`. Modified:
  `audits/OPEN_GAPS_LEDGER.md` (G-055/G-056/G-070 evidence-backed). **No requirements.txt / lockfile / code changed;
  new deps: none.**
- **Audit holds 3** (`--no-baseline-drop`: docs-only assessment). **All routed CTO-#6 in-house items are now
  addressed** (C6-R1 G-075 + C6-R3 hook + C6-R4 → Stage 33; C6-R5 → Stage 34; C6-R3-tail → Stage 35; C6-R2 assessed →
  Stage 36).
- What remains is a real-world engagement (pilot G-035/G-043, cert G-011, scale G-066 — buyer/accredited-body-blocked)
  OR the actual dep-refresh migration when a dedicated branch/staging + CI exists.

## References
- research §47 · `compliance/dependency-refresh-assessment.md` · `research/stage-explainers/STAGE_36/index.html` ·
  `audits/CTO_6_review.md` (C6-R2) · G-055/G-056/G-070 + G-065 (`audits/OPEN_GAPS_LEDGER.md`) ·
  `compliance/dependency-exceptions.md`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-18T13:57:17+00:00 -->
<!-- signature: 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 -->
