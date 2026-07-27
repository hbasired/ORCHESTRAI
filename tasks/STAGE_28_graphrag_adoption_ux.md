---
status: done
stage: 28
slug: graphrag_adoption_ux
created: 2026-07-02
---

# Stage 28 — GraphRAG Grounding + Design-Thinking / Behavioural Adoption UX

> Two joined deliverables from the 2026-07-02 strategic reset: (1) **GraphRAG grounding** — ground every diagnosis /
> explanation in the REAL Neo4j ISA-95 equipment graph + SOP corpus with citations, cutting hallucination and lifting
> the trust/explainability moat; (2) **Adoption-as-a-feature** — a design-thinking operator UX + behavioural-science
> onboarding so the product is frictionless to adopt (the operator's design-thinking + behavioural-science ask). Sourced
> in `research/initial-research.md §35.7 / §35.8` (Microsoft GraphRAG; tredence/flur.ee grounding 30–40% fewer factual
> errors; arxiv ChemUnityQA 2605.03205; human-agent-teaming 2504.05755 / 2603.04746 / 2507.21158; change-management-2026
> — 13% trained, $2–3 reskilling per $1). Free/local: bge-small embeddings already present (Rule 9).

## Pre-requisites
- Stage 27 closed (or coordinated). Read KB_24 / KB_25 / `audits/OPEN_GAPS_LEDGER.md` (Rule 10).
- Research-first (Rule 11): append a Stage-28 SOTA section BEFORE implementing (GraphRAG retrieval over property graphs,
  citation/attribution, trust-calibration UX, progressive-autonomy controls).

## Acceptance criteria

- [ ] **GraphRAG retriever** (`backend/knowledge_graph/graphrag.py`): a real retrieval-augmented layer over the Neo4j
  ISA-95 graph (equipment topology, supplier/SKU/stage relations) + an SOP/document corpus embedded with bge-small.
  Multi-hop graph traversal + semantic retrieval → grounded context with **explicit citations** (node/edge IDs + doc
  refs). No fabrication: if the graph has no answer, return honest-empty, not a plausible guess.
- [ ] **Grounded explanations wired into the runtime:** the diagnose/explain nodes cite the GraphRAG evidence; the
  citations flow into the Art-12 `record_decision_trace` snapshot so the signed audit trail carries the grounding.
- [ ] **Measured grounding improvement (honest):** an eval comparing ungrounded-LLM vs GraphRAG-grounded on a fixed
  question set — report a real factuality/citation metric (grounded-answer rate, hallucination rate) with the method
  shown. Label honestly (our corpus/graph scale, not a public benchmark).
- [ ] **Design-thinking operator UX** (`frontend-nextjs/src/app/`): **persona-shaped** views — ops-lead (A/B minutes
  saved + live incidents), compliance officer (the signed evidence pack + Art-12 trace), OT/IT integrator (adapters +
  health), security architect (identity/key-rotation state). Real data from the runtime APIs, no `generateMockState`.
- [ ] **Behavioural adoption layer:** (a) **trust calibration** — every recommendation surfaces confidence + uncertainty
  + the counterfactual + the graph citation (never a bare score); (b) **progressive-autonomy control** — an operator
  toggle across shadow→assisted→supervised→autonomous mapped to the pilot canary ladder + HITL; (c) **WIIFM / loss-
  aversion reporting** — the headline is "prevented downtime we would have suffered" (the Stage-6 counterfactual), not
  "efficiency +X%"; (d) **friction-free onboarding** — a compose-up $0 shadow-mode walkthrough.
- [ ] Tests: `backend/tests/knowledge_graph/test_graphrag.py` (retrieval correctness, citation presence, honest-empty) +
  frontend component tests for the persona views + trust-calibration surfacing. Independent review (DIFFERENT agent) → PASS.
- [ ] Explainer `research/stage-explainers/STAGE_28/index.html`.

## Files to CREATE
| Path | Purpose |
|---|---|
| `backend/knowledge_graph/graphrag.py` | GraphRAG retriever over Neo4j ISA-95 + SOP corpus |
| `backend/knowledge_graph/sop_corpus/` | SOP/document corpus + embedding index |
| `backend/tests/knowledge_graph/test_graphrag.py` | grounding tests |
| `frontend-nextjs/src/app/{ops,compliance,integrator,security}/page.tsx` | persona-shaped views |
| `frontend-nextjs/src/components/TrustCalibration.tsx`, `AutonomySlider.tsx` | behavioural UX components |
| `research/stage-explainers/STAGE_28/index.html` | explainer |

## Files to MODIFY
| Path | Change |
|---|---|
| `backend/agents/runtime/nodes.py` | diagnose/explain cite GraphRAG evidence into the Art-12 trace |
| `backend/ml/failure_explainer.py` | attach graph citations to explanations |
| `knowledge-base/KB_14_Agent_Memory_Architecture.md` | GraphRAG as the semantic-retrieval path |
| `knowledge-base/KB_26_Product_Market_Strategy.md` | adoption-UX shipped (§12.5 → status) |

## KB files this stage updates
- `KB_14_Agent_Memory_Architecture.md`, `KB_15_Observability_Evidence_Pipeline.md`, `KB_26_Product_Market_Strategy.md`,
  `KB_TASK_LOG.md`

## Verification commands
```bash
cd backend && python -m pytest tests/knowledge_graph/ -v
cd frontend-nextjs && npm test
python scripts/verify-audit-chain.py
bash scripts/audit.sh   # <= 364 (frontend mock removal should DROP it)
```

## Audit target
- **Strict decrease** — replacing any `generateMockState`/`Math.random` frontend fabrication with real runtime data drops
  the baseline. This is the stage that should finally move 364 down honestly (with the G-082 legacy de-mock).

## Role
- Primary: `ml-engineer` (GraphRAG) + `frontend-engineer` (persona UX) + `agentic-governance-engineer` (trace/citation).

## Hand-off
- What becomes true: explanations are graph-grounded + cited (measurably fewer factual errors) and the operator
  experience is persona-shaped + trust-calibrated + progressive-autonomy + WIIFM-framed — the adoption differentiator.
  Real-user adoption validation still needs a real pilot (G-035/043, buyer-blocked).
