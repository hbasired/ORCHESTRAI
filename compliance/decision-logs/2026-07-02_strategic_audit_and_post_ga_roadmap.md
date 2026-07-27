# ADR — Post-GA Strategic Audit & Roadmap Extension (Stages 26–28)

- **Date:** 2026-07-02
- **Status:** Accepted
- **Type:** Out-of-band strategic reset (NOT a numbered build stage; no backend code; audit baseline untouched at 364).
  Precedents: 2026-05-18, 2026-06-11, 2026-06-14, 2026-06-29.
- **Role:** `agentic-governance-engineer` + `product-manager`.
- **Deciders:** operator + implementing agent.

## Context

The build is complete through Stage 24 (GA v1.0.0) + all five CTO checkpoints (verdict at #5: "GA is real and honest,"
zero must-fix). The operator requested, post-GA: a full-system production-readiness audit; competitive intelligence,
positioning, and perceptual mapping; an honest "gamechanger / adoptability / efficacy" verdict; a fresh SOTA web-research
pass (Kagenti and resilient-agent methods, IBM agent-building stack, recent implementable papers, design-thinking +
behavioural science); an end-user/ICP adopter list + outreach; and the next-stage tasks that make the product more
operational and adoptable by major industries (incl. "complete supply-chain automation").

This ran as the **out-of-band strategic-reset pattern**: fresh research → `research/initial-research.md §35` (mandatory
per Hard Rule 11) → strategy artifacts → this ADR → out-of-band `KB_TASK_LOG` entry. No `close-task.sh`, no `--baseline`,
no backend/frontend code edited; append-only rules held throughout.

## Findings (audit — verified, not asserted)

- **Engineering is real and honest.** 24 stages closed, 344 tests green / 0 failing, 7 real trained models + cards, real
  FIPS PQC (ML-DSA-65 / ML-KEM-768 / SLH-DSA), append-only ML-DSA-signed audit chain (426 rows, verifier green),
  governance (MAC/RBAC/Art-12) live-enforced, no committed secrets (`.env`/creds gitignored). The GA'd LangGraph runtime
  is fabrication-free.
- **Disclosed residual (G-082):** the superseded legacy FastAPI demo path still fabricates with `random.*` and is the
  bulk of the 364 baseline — ledgered, not hidden; targeted for de-mock/removal (drives baseline down in Stage 28).
- **Not production-SCALED.** Single-node/single-worker (G-066); models on proxy/benchmark data, never real site telemetry
  (G-035/043); not certified/CE-marked/EU-registered (G-011, needs accredited body + legal-entity provider); thin
  operator UX. Production-grade *discipline* + pilot-*deployable*, but ready for one controlled pilot site, not enterprise
  magnitude.

## Competitive & market read (sourced — research §35.4/§35.6)

- Market: AI-driven PdM $2.61B (2026) → $19.27B (2032), 39.5% CAGR; Deloitte 80% of manufacturers plan agentic-AI invest.
- Players leave our niche open: Palantir/Cognite (data layer, closed), Siemens (vendor-locked), IBM watsonx Orchestrate
  (generic agent control plane, no OT/SIL/PQC — a **channel**, not a war), Augury/Samsara (point PdM), Kagenti/kagent
  (OSS agent infra — adopt their SPIFFE identity pattern, be a compatible agent), NVIDIA physical AI (complement — makes
  robots smart, not provable to a regulator; we sit above).
- EU AI Act high-risk deadlines EXTENDED (critical infrastructure → **2 Dec 2027**), harmonised standards delayed to H2
  2026/H1 2027 — more runway; the "evidence-ready before the deadline" wedge is real and dated.

## Decision

1. **Positioning holds and is reinforced:** the neutral, certifiable, PQC, self-healing trust/safety/evidence layer that
   rides ABOVE whatever platform the customer bought + a channel-fit agent (A2A / Kagenti AgentCard) for IBM Orchestrate
   / CNCF platforms. (KB_26 §12.)
2. **Honest verdict:** a credible gamechanger *candidate* in its niche, not a proven one; adoption is earned pilot-by-pilot
   (not viral) but the OSS/$0-shadow/HITL/loss-aversion wedge lowers the barrier; works as software, unproven as a
   real-world outcome engine until a real-data pilot. Convert by closing four gaps in order: real pilot (G-035/043) →
   scale (G-066) → certification (G-011) → adoption UX.
3. **Extend the roadmap with three free/local build stages** (full-depth-first, independently reviewed):
   - **Stage 26 — Complete supply-chain automation:** multi-agent consensus-seeking + disruption monitoring over SimWorld
     suppliers + Neo4j + A2A (neutral+safe answer to the supply-chain-agent category).
   - **Stage 27 — Resilience & anti-fragility:** SPIFFE/SPIRE-pattern rotating workload identity + mesh mTLS + Kagenti/
     kagent-compatible AgentCard + durable-execution hardening (idempotent compensable effects, circuit breakers, saga)
     + chaos-as-anti-fragility; closes go-live identity gaps R4/G-4/G-064-network + a G-066 scale foothold.
   - **Stage 28 — GraphRAG grounding + design-thinking/behavioural adoption UX:** graph-grounded cited explanations
     (~30–40% fewer factual errors) + persona-shaped UX + trust calibration + progressive autonomy + WIIFM reporting;
     the stage that should finally move the 364 baseline DOWN (frontend mock removal + G-082 legacy de-mock).
4. **Buyer/body-blocked items stay deferred, not faked:** real pilot + published A/B on real telemetry (G-035/043),
   accredited certification + CE marking + EU-database registration (G-011), full multi-node HA + fleet-magnitude load
   (G-066 tail), first-real-PLC safety wiring (R5). These need a customer, an accredited body, or a legal-entity provider.

## Consequences

- KB_26 gains §12 (July-2026 refresh: CI, positioning, differentiators, adopter list, adoption-UX, production verdict,
  EU-AI-Act timeline). `research/strategic-audit-2026-07/index.html` is the reader-facing artifact. Stages 26–28 task
  docs seeded. Audit baseline unchanged (strategic/doc work only). No new deps; Rule 9 (free/local/OSS) holds.
- Roadmap note: Stage 25 (post-GA ops) remains; 26–28 extend it. CTO-checkpoint cadence continues (next at Stage 30).

## References
- `research/initial-research.md §35` · `research/strategic-audit-2026-07/index.html` ·
  `knowledge-base/KB_26_Product_Market_Strategy.md §12` · `tasks/STAGE_{26,27,28}_*.md` ·
  `audits/OPEN_GAPS_LEDGER.md` (G-082/G-035/G-043/G-011/G-066) · `knowledge-base/KB_TASK_LOG.md` (2026-07-02 out-of-band).
  Sources: kagenti.github.io; ibm.com/products/watsonx-orchestrate (Think 2026); lfaidata.foundation (ACP+A2A); temporal.io;
  marketsandmarkets 56600288; artificialintelligenceact.eu (art 6/16); nvidianews.nvidia.com; Microsoft GraphRAG;
  arxiv 2604.05987 / 2605.03205 / 2504.05755; digitalapplied.com change-management-2026.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-07-02T17:31:08+00:00 -->
<!-- signature: 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 -->
