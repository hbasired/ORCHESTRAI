---
status: done
stage: 32
slug: pilot_readiness_package
created: 2026-07-13
---

# Stage 32 — Pilot-readiness package

> The final build-arc stage (docs-only, no backend code): completes the pilot-prep so the buyer-blocked real
> engagement can start day-one and convert the sim-proven value into published real-world evidence (G-035/G-043).
> Ships a **Pilot Charter template** (predefined success criteria + Scale/Iterate/Pivot/Stop gates — the discipline
> ~60% of AI pilots skip), a **capability-readiness matrix** (the honest sim-vs-real inventory with every measured
> number), and an **A/B protocol** covering every value driver Stages 26–31 added, extending the Stage-22 kit.
> Research §43. The real pilot itself stays honestly deferred (buyer-blocked).

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_32/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 26–31 (all the capabilities the package covers), 22 (the base pilot kit + runbook)
- Decision logs honoured: `2026-06-22_stage22_pilot_deployment_runbook.md`, `2026-07-13_stage31_detector_eval_hardening.md`, the Stage 26–30 ADRs
- KB files at minimum version: KB_26 (product/market strategy — pilot/GTM), KB_18 (governance/EU-AI-Act deployer)
- Gaps ledger rows pulled in (IDs): **G-035** (real-data re-fit) + **G-043** (reference pilot + published A/B) — the buyer-blocked halves this package prepares for; G-012 (pre-revenue)

## Acceptance criteria

- [x] **AC1 — Pilot Charter template with PREDEFINED success criteria + decision gates.** `compliance/pilot-charter-template.md`
  fixes scope/intended-purpose, per-capability success metrics + thresholds (each with its sim precursor), two hard
  safety/evidence gates, timeline, and the Scale/Iterate/Pivot/Stop gates (research §43.1). Verifiable: file exists +
  contains the four decision gates + the two hard gates.
- [x] **AC2 — capability-readiness matrix, honest sim-vs-real.** `compliance/capability-readiness-matrix.md` inventories
  every capability with its readiness tag, the REAL measured number (cited to its stage/results file), the real-data
  dependency (G-035), and the pilot A/B hypothesis. Every number traces to a closed stage — no new/aspirational claims.
- [x] **AC3 — A/B / proof-of-value protocol for the full capability set.** `compliance/pilot-ab-protocol.md` predefines
  the design (baseline window, assignment unit, primary + guardrail metrics, paired test + CI) and 5 per-capability
  hypotheses + 2 hard gates, reusing the Stage-6/26/30 A/B harnesses.
- [x] **AC4 — the base kit extended for Stages 26–31.** `compliance/pilot-onboarding-kit.md §6` adds the data-intake for
  the demand forecaster / supply-chain / GraphRAG corpus / detector real-traffic — so the new capabilities have a re-fit path.
- [x] **AC5 — honesty: no real number is claimed as a deployment result.** Every figure is labelled sim/benchmark and
  tied to G-035/G-043; the two hard gates (0 unsafe actuations, chain verifies) are stated as production-ready properties.
- [x] **AC6 — docs-only, audit holds, research-first + explainer + independent review.** No backend/frontend code
  touched; audit holds 3. Research §43 appended BEFORE writing; `research/stage-explainers/STAGE_32/index.html`;
  independent review by a DIFFERENT agent = PASS (checks the numbers match the closed stages; no overclaim).

## Files to CREATE

| Path | Purpose |
|---|---|
| `compliance/pilot-charter-template.md` | predefined success criteria + Scale/Iterate/Pivot/Stop gates + hard safety/evidence gates |
| `compliance/capability-readiness-matrix.md` | honest sim-vs-real inventory of every capability with its measured number + real-data dependency |
| `compliance/pilot-ab-protocol.md` | per-capability A/B design (baseline, metrics, paired test + CI) reusing the sim A/B harnesses |
| `research/stage-explainers/STAGE_32/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `compliance/pilot-onboarding-kit.md` | §6 addendum — data-intake for the Stages-26–31 capabilities (forecaster/supply/GraphRAG/detector) |
| `knowledge-base/KB_26_Product_Market_Strategy.md` | pilot-readiness package + capability-readiness posture |
| `audits/OPEN_GAPS_LEDGER.md` | note the buildable pilot-prep is COMPLETE (G-035/G-043 remain buyer-blocked) |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive docs stage |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_26_Product_Market_Strategy.md` (pilot readiness / GTM posture)

## Verification commands

```bash
bash scripts/audit.sh                    # holds at 3 (docs-only; no code touched; --no-baseline-drop)

# the package exists + is internally consistent (numbers trace to closed stages)
ls compliance/pilot-charter-template.md compliance/capability-readiness-matrix.md compliance/pilot-ab-protocol.md
grep -c "G-035" compliance/capability-readiness-matrix.md   # every sim number carries its real-data caveat
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — DOCS-ONLY governance/pilot-prep stage; no backend/frontend code touched;
  zero fakery patterns introduced.

## Role

- Primary: `agentic-governance-engineer` / `compliance-engineer` (pilot governance + honest claim discipline)
- Secondary: `product-manager` (GTM / ICP posture — KB_26)

## Risks / unknowns

- The package is a TEMPLATE + the sim precursors — no real A/B has been run (buyer-blocked, G-035/G-043); the docs
  must never present a sim number as a deployment result (honesty-audited).
- Certification (accredited functional-safety + CE/registration, G-011) needs an accredited body — a real-engagement item.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The pilot-prep is COMPLETE: a charter with predefined success criteria + gates, an honest capability-readiness
    matrix (every capability's real measured number + real-data dependency), an A/B protocol for the full capability
    set, and the data-intake for everything Stages 26–31 added — a real engagement can start day-one.
  - The four post-Stage-28 build stages (29–32) are done.
- What the next task (CTO #6) starts with:
  - A read-only every-10 CTO checkpoint across Stages 29–32 (run `scripts/cto-review.sh`) — the operator sequenced it
    AFTER the four stages.
- Open items deferred to a future stage:
  - The real pilot + real-data re-fits + published A/B (G-035/G-043) and accredited certification (G-011) — all
    buyer/accredited-body-blocked, not free/local-buildable.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-13T06:08:04Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_31_detector_eval_hardening.md)


- What is now true that wasn't before this stage:
  - The injection detector has a learned tier (detection 0.9935→1.0, FPR 0.0156→0.0, held-out CV) + an LLM-judge
    escalation; a continuous runtime behavioural anomaly monitor exists and consumes real `run_incident` output.
- What the next stage (32 — pilot-prep) starts with:
  - A hardened, honestly-measured defence surface + a fully-live loop — ready to package the pilot onboarding kit +
    A/B protocol against a real buyer's incidents (G-035/G-043, buyer-blocked).
- Open items deferred to a future stage:
  - Real-traffic / multilingual detector validation + threshold tuning on live data (pilot, G-035).
  - Wiring the behavioural monitor as an always-on runtime hook (currently consumes results post-hoc via `features_from_run`).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
