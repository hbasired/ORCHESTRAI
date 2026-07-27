# ADR — Stage 24: GA release (v1.0.0) + governance live-enforcement (G-080) + provider placing-on-market readiness

**Date**: 2026-06-22
**Status**: Accepted (Stage 24 — follows Stage 23 conformity dry-run)
**Author personas**: `agentic-governance-engineer` (primary) + `compliance-engineer` + `backend-engineer` + `security-pqc-engineer`
**Relates**: KB_18 (governance evidence), KB_10 (production hardening). Research §34. Hard Rule 9 (free/local), Rule 1a
(no fabrication / honest framing), Rule 11 (research-first). Pays **G-080** + ISO-42001 **NC-1/NC-2**; rehearses EU-AI-Act
provider placing-on-market (Art-16).

---

## Context
GA the OSS control plane (the public contract is stable across Stages 0–23), wire the Stage-23 governance layer into LIVE
enforcement (G-080 — the assessor's "where is it enforced?"), close the doable ISO-42001 nonconformities, and rehearse
the EU-AI-Act provider obligations for placing a high-risk system on the market (Art-16). All free/OSS/local — the real
pilot + certification + CE/registration remain post-GA (need a buyer/accredited body/legal-entity provider).

## Decisions

**D1 — G-080: governance LIVE-enforced.** Wired the Stage-23 `backend/governance/` layer into real call sites:
- A2A boundary (`a2a/server.py::a2a_rpc`): every external caller is an **L0 peer** → `rbac.check_function_access` confines
  it to the `a2a_capability` category, and `mac.can_read` (no-read-up) clamps it to ≤"internal" clearance; allow/deny
  audited; composes with the peer-key gate + ZeroTrustGateway. Honest ImportError degradation.
- Runtime (`agents/runtime/nodes.py::log`): `traceability.record_decision_trace` appends the Art-12 pre/post state
  snapshot per live decision (atop the per-decision audit row).
- **Verified live:** a `run_incident` wrote a `decision.trace` row (seq 425); the live `audit_chain` now carries
  `decision.trace` + `rbac.check` + `mac.read` rows; chain green (426 rows, all 347 post-cutover verify); a2a + governance
  + runtime tests **31 passed / 2 skipped**.

**D2 — ISO-42001 NCs closed.** NC-1: `compliance/iso-42001-internal-audit/2026-Q4_management-review.md` (clause 9.3 —
inputs/results, GA approval). NC-2: `compliance/iso-42005-impact-assessment.md` (ISO 42005:2025 10-step impact assessment).
NC-3 (customer/supplier records) stays OPEN — blocked on a real pilot (G-035/G-043); accepted as a known limitation.

**D3 — Provider placing-on-market readiness (Art-16).** `compliance/eu-declaration-of-conformity.md` (Art-47/Annex V DoC
TEMPLATE — honest rehearsal: no legal-entity provider, no harmonised standard → no presumption, internal-control/Annex-VI
route, no notified body) + `compliance/ga-release-checklist.md` (maps each Art-16 obligation → readiness; CE marking +
EU-database registration DEFERRED).

**D4 — GA = OSS v1.0.0.** `RELEASE_NOTES_v1.0.0.md` summarises the build (Stages 0–24). Semver 1.0.0 (stable public
contract). HONEST: GA of the free/OSS platform — conformity-assessment-READY, NOT certified/CE-marked/registered/piloted/sold.

## Verified live (Docker up, 2026-06-29)
| check | result |
|---|---|
| G-080 A2A RBAC+MAC gate | 31 a2a/governance/runtime tests pass; gate doesn't block legit `forecast_oee`; audited |
| G-080 runtime traceability | live `run_incident` → `decision.trace` row (seq 425); chain green 426/347 |
| governance row types live | `decision.trace` + `rbac.check` + `mac.read` in the real `audit_chain` |
| Annex IV pack (DB up) | 14 sections, audit-summary populated, ML-DSA-65 signed |
| Full suite | (Stage 23) 344 passed / 10 skipped / 0 failed; `audit.sh` holds **364** |

## Consequences
- New: `compliance/{iso-42001-internal-audit/2026-Q4_management-review.md, iso-42005-impact-assessment.md,
  eu-declaration-of-conformity.md, ga-release-checklist.md}`, `RELEASE_NOTES_v1.0.0.md`. Modified: `a2a/server.py` +
  `agents/runtime/nodes.py` (G-080 live wiring), KB_18, ledger, risk-register. **No new deps.** Audit holds **364**.

## Honest residual / ledger
- **RESOLVED:** G-080 (governance live-enforced + verified), NC-1 (management review), NC-2 (ISO-42005 impact assessment).
- **DEFERRED (need a buyer/accredited body/legal-entity provider — Rule 9):** the real pilot + published A/B (G-035/G-043),
  accredited certification (G-011), CE marking + EU-database registration, NC-3 customer/supplier records. Post-GA ledger:
  G-066 (scale), G-060 (pgaudit), G-067 (Langfuse-UI), G-070 (a2a-sdk).
- GA is the OSS v1.0.0 — NOT a certified/sold product. Nothing faked.

## References
- `backend/a2a/server.py` · `backend/agents/runtime/nodes.py` · `backend/governance/*` · `RELEASE_NOTES_v1.0.0.md` ·
  `compliance/{eu-declaration-of-conformity,ga-release-checklist,iso-42005-impact-assessment}.md` · research §34.
  EU AI Act Art-16/47/48/Annex-V; ISO/IEC 42001 §9.3; ISO/IEC 42005:2025; semver.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-29T14:31:11+00:00 -->
<!-- signature: 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 -->
