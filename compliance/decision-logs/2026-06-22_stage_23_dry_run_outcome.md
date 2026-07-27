# ADR — Stage 23: Conformity Assessment Dry-Run + governance MAC/RBAC/traceability (outcome)

**Date**: 2026-06-22
**Status**: Accepted (Stage 23 — follows Stage 22 pilot deployment runbook)
**Author personas**: `compliance-engineer` (primary) + `agentic-governance-engineer` + `robotics-integration-engineer`
**Relates**: KB_18 (governance evidence), KB_17 (functional safety). Research §33. Hard Rule 9 (free/local), Rule 1a
(no fabrication / honest framing), Rule 11 (research-first). Pays CTO #4 **R10** + KB_18 wishlist **G-028/G-029/G-030** +
defines **G-011** (cert path).

---

## Context

CTO #4 R10: run the Annex IV pack + risk register + safety case through a mock notified-body assessment; close the KB_18
governance wishlist (Bell-LaPadula MAC / agent-hierarchy RBAC / total traceability); define the SIL-cert + certified-PLC
path (G-011). This is an INTERNAL rehearsal — a fresh-agent "sympathetic reviewer", NOT a real notified body (no buyer/
accredited engagement yet — Rule 9). Research §33.1 establishes the honest route: our Annex-III category is points 2-8
(industrial/infrastructure), so the EU-AI-Act route is **internal control (Annex VI)** — a notified body is mandated only
for point-1 biometrics, and no harmonised AI standard is published yet (no presumption of conformity). So Stage 23
produces + rehearses the internal-control conformity FILE; it does NOT claim certification.

## Decisions

**D1 — Governance access-control layer (`backend/governance/`, G-028/029/030).**
- `mac.py` (G-030) — Bell-LaPadula confidentiality MAC: `SecurityLabel`(level + categories), `dominates`
  (level-dominance + category-containment), `can_read` (no-read-up), `can_write` (no-write-down ⋆-property), audited
  allow/deny. The Stage-17 safety wrapper is the Biba integrity dual.
- `rbac.py` (G-029) — agent-hierarchy function-scoped RBAC: `AgentTier` L3_EMBODIED→L2_HEAD→L1_WORKER→L0_PEER +
  `check_function_access` (tier ≥ function-min-tier AND least-privilege grant; L0 external peer confined to
  `a2a_capability`, assume-breach); composes with the Stage-17 ZeroTrustGateway.
- `traceability.py` (G-028) — `record_decision_trace` captures `state_snapshot(pre/post)` + decision → one signed
  `audit_chain` row (Art-12), atop the existing per-decision rows + spans.
- All decisions are PURE/deterministic + DB-independent; the audit record is best-effort (honest degradation:
  `audited=False`, never a fabricated seq). 9/9 pure-logic tests pass.

**D2 — Conformity dry-run artefacts.**
- `compliance/iso-10218-risk-assessment.md` — ISO 10218-2:2025 §6 RA (absorbs ISO/TS 15066): hazard catalogue H1-H9 +
  the Stage-17 safeguards as risk-reduction + the honest scope boundary (we are the AI decision/actuation-gate layer,
  the integrator owns the complete-cell RA) + §5 the **G-011 certification path**.
- `compliance/iso-42001-internal-audit/2026-Q4_audit.md` — internal audit of the 9 Annex-A objectives / clauses 4-10
  against live evidence: 7/9 Conformant, 2 Partial, 0 major NC; 3 minor NCs (NC-1 mgmt-review record, NC-2 ISO-42005
  impact-assessment doc, NC-3 customer/supplier records [needs a pilot]) → Stage 24.
- `compliance/annex-iv-packs/2026-06-22_dry_run.{pdf,html}` — the Annex-VI internal-control file (14 sections,
  ML-DSA-65 signed). HONEST: generated with Docker DOWN → the audit-chain-summary section is degraded
  ("unavailable"); regenerate with the DB up for the final dry-run pack (Docker-gated).

**D3 — Mock notified-body assessment.** A FRESH, different agent plays the sympathetic external reviewer + independent
task-auditor: reviews the pack + risk register + ISO 10218 RA + ISO 42001 audit + governance code against EU AI Act /
ISO 42001 / ISO 10218; writes `audits/STAGE_23_external_review.md` (conformity findings) + `audits/STAGE_23_independent_review.md`
(task-auditor verdict). Findings route to Stage 24.

## Honest framing (no overclaim)
- This is a **self-audit dry-run**, NOT an accredited certification or a real notified-body assessment.
- EU-AI-Act route for our category = **internal control (Annex VI)**; no notified body mandated; no harmonised standard
  published → no presumption of conformity yet.
- The governance audit-wiring + the Annex-IV audit-summary are **Docker-gated** (verified live when Docker is up; the
  pure logic is tested now).

## Consequences
- New: `backend/governance/{__init__,mac,rbac,traceability}.py`, `backend/tests/governance/test_governance.py`,
  `compliance/iso-10218-risk-assessment.md`, `compliance/iso-42001-internal-audit/2026-Q4_audit.md`,
  `compliance/annex-iv-packs/2026-06-22_dry_run.{pdf,html}`, `audits/STAGE_23_external_review.md`. Modified: KB_18/KB_17,
  risk-register, ledger (G-028/029/030 RESOLVED, G-011 path-defined). **No new deps.**
- Audit holds **364** (additive governance code [real, no theatre] + docs).

## Honest residual / ledger
- **RESOLVED:** G-028 (traceability), G-029 (RBAC), G-030 (MAC); **G-011 path defined** (still open as actual cert —
  needs an accredited body + certified PLC + a real cell, post-build).
- **NCs → Stage 24:** NC-1 management-review record, NC-2 ISO-42005 impact-assessment doc, NC-3 customer/supplier records.
- **Docker-gated (verify when up):** governance audit-wiring live + the Annex-IV audit-summary section in the final pack.
- **Deferred (needs a buyer/accredited body):** the REAL notified-body engagement + certification (G-035/G-043/G-011 cert).

## References
- `backend/governance/*` · `compliance/iso-10218-risk-assessment.md` · `compliance/iso-42001-internal-audit/2026-Q4_audit.md`
  · `compliance/annex-iv-packs/2026-06-22_dry_run.pdf` · research §33. EU AI Act Art-43/Annex-VI/VII; ISO 10218-2:2025; ISO/IEC 42001; Bell-LaPadula.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-29T11:52:53+00:00 -->
<!-- signature: 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 -->
