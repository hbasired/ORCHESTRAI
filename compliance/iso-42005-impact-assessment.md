# ISO/IEC 42005:2025 — AI System Impact Assessment (Stage 24, closes NC-2)

> AI system impact assessment per ISO/IEC 42005:2025, following its 10-step process. Closes **NC-2** from the Stage-23
> internal audit. Research §34.3. Assesses the AI system's impact on individuals, groups, and society across the
> lifecycle; consolidates existing inputs (intended purpose, risk register, ISO-10218 RA, human-oversight, red-team).

## 1. Scoping
**System:** a vendor-neutral, EU-AI-Act-grade agent control plane for industrial robot / OT fleets (predict → diagnose →
reason → verify → intervene). **Intended purpose:** advise/﻿gate maintenance + coordination decisions in a manufacturing
cell, under human oversight. **EU AI Act class:** high-risk (Annex III, industrial/infrastructure management — points 2-8).
**Boundary:** the AI decision/actuation-gate layer; the robot OEM + cell integrator own the physical safety case.

## 2. Responsibility assignment
Provider/owner: the project owner. Roles: agentic-governance (coordination), compliance (this assessment),
robotics-integration (safety), security-pqc (crypto/identity). Deployer obligations: `pilot-deployment-runbook.md` §3 (Art-26).

## 3. Threshold (does it warrant a full assessment?)
**Yes** — high-risk + physical-actuation-adjacent + worker-affecting → full impact assessment required (this document).

## 4–5. Execution + analysis — impacts on individuals / groups / society

| Stakeholder | Potential POSITIVE impact | Potential NEGATIVE impact | Likelihood × severity | Mitigation (in-system) |
|---|---|---|---|---|
| Plant workers | fewer unplanned breakdowns; unsafe-command refusal; less hazardous manual diagnosis | wrong maintenance call disrupts work; over-reliance; job-task change | med × med | HITL approval (Art-14); shadow→assisted canary; worker-information duty (runbook §3); no-LLM-actuator |
| Operators / overseers | decision explanations (SHAP/DiCE); audit trail | alert fatigue; automation bias | med × low | confidence + rationale surfaced; override always available + audited |
| The public / environment | safer, more reliable industrial operation | a safety-critical wrong action (if uncontrolled) | low × high | SIL-rated validator + STO/SS1 (Stage 17); trace-pairing CI invariant; G-011 cert path before real actuation |
| Data subjects | namespace-isolated incident memory | cross-tenant leakage of operational data | low × med | mem0 `_authorize` + Postgres RLS (connection-role, Stage 22); MAC no-read-up (Stage 23) |
| Society / fairness | open, auditable, vendor-neutral governance layer | mis-fit model on un-representative data → biased decisions | med × med | real-fleet re-fit + A/B before autonomy (onboarding kit); red-team evals; honest "proxy data" disclosure |

**Fundamental-rights touchpoints:** worker rights (information + oversight — addressed), no biometric/social-scoring use
(out of scope — not Annex-III point 1), data protection (namespacing + RLS). No high-severity unmitigated impact at the
current human-supervised, pre-pilot scope.

## 6. Documentation
This document + the Annex IV pack (intended purpose, risk mgmt, data governance, human oversight) + the ISO-10218 RA +
the risk register. Signed audit_chain is the record-of-decisions evidence.

## 7. Oversight
Human-in-the-loop on SIL-1+ (LangGraph `interrupt()`); shadow→assisted→supervised-autonomous canary; the deployer
monitors operation (Art-26) and can suspend use.

## 8. Monitoring
Post-market monitoring plan (`post-market-monitoring-plan.md`, Art-72): red-team evals, audit-chain integrity, safety
trace-pairing, RLS, DR drills — each with a threshold/trigger feeding back to the risk register.

## 9. Integration into risk-management systems
Impacts here are mirrored as rows in `compliance/risk-register.md` (refreshed every CTO checkpoint) + the
OPEN_GAPS_LEDGER; the ISO-42001 AIMS (clause 6 planning) requires this assessment as a consistent input.

## 10. Review cycles
Re-assess at each CTO checkpoint, before any real-pilot go-live (when proxy models are re-fit to real data — the biggest
impact-profile change), and on any serious incident (Art-72→73).

## Honest status
Conducted at the current scope (pre-pilot, human-supervised, proxy/benchmark-validated models). The impact profile MUST
be re-assessed when a real fleet + real data + autonomous operation enter (G-035/G-043) — that is the material change.
This is a self-conducted 42005 assessment, not an externally-assured one.
