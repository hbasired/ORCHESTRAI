# Stage 23 — External Conformity Assessment (MOCK Notified-Body / Sympathetic Reviewer)

**Date**: 2026-06-29
**Reviewer**: Fresh, independent agent acting as a sympathetic external conformity assessor (mock notified body).
**Scope**: EU AI Act (Annex IV / Annex VI internal control) + ISO/IEC 42001 (AIMS) + ISO 10218-2:2025 (robot-cell RA),
assessed against the Stage-23 dry-run conformity evidence.
**Posture**: This is a **DRY-RUN rehearsal**. I am NOT an accredited notified body; no certification is conferred or
implied by this document. My job is to read the evidence as an assessor would and report whether the file would survive
a real assessment, plus the gaps a real assessor would raise.

> **Important honesty note up front:** the submitter has framed this correctly throughout — every artefact says
> "self-audit dry-run / NOT certified / NOT a real notified body." I confirm that framing is honest (see §4).

---

## 1. Evidence reviewed

| Artefact | Path | Read? |
|---|---|---|
| Conformity outcome ADR | `compliance/decision-logs/2026-06-22_stage_23_dry_run_outcome.md` | yes |
| ISO 10218-2:2025 risk assessment | `compliance/iso-10218-risk-assessment.md` | yes |
| ISO/IEC 42001 internal audit | `compliance/iso-42001-internal-audit/2026-Q4_audit.md` | yes |
| Annex IV / Annex-VI internal-control pack | `compliance/annex-iv-packs/2026-06-22_dry_run.{pdf,html}` | yes (html) |
| Governance code (MAC/RBAC/traceability) | `backend/governance/{mac,rbac,traceability}.py` | yes |
| Risk register row (G-011 / conformity) | `compliance/risk-register.md` | yes |
| Gaps ledger (G-028/029/030/G-011) | `audits/OPEN_GAPS_LEDGER.md` | yes |

---

## 2. Conformity findings (as an assessor would frame them)

### 2.1 EU AI Act route classification — CORRECT
- The submitter classifies the system as Annex-III **points 2-8** (industrial / infrastructure safety component),
  for which the conformity-assessment route is **internal control (Annex VI)** — a notified body is mandated only
  for Annex-III **point 1 (biometrics)**.
- Consequence stated honestly: **no notified body is required** for this category, and because **no harmonised AI
  standard is yet published**, there is **no presumption of conformity** — the obligation is to maintain the
  technical-documentation file (Annex IV) and re-assess as standards land. **This is the correct reading of the
  Regulation.** A real assessor would accept this framing.

### 2.2 ISO 10218-2:2025 risk assessment — ADEQUATE for the declared scope
- The RA correctly declares the **scope boundary**: this layer is the **AI decision / actuation-gate**, not the robot
  OEM or cell integrator; the integrator owns the complete-cell RA. This is the honest and conventional division of
  responsibility for a sub-system supplier.
- Hazard catalogue H1–H9 is plausible and each hazard is tied to a **real risk-reduction measure that exists in the
  codebase** (validator/sil_bridge, VDA freshness gate, HMAC, HITL, STO/SS1, self-healing). Residual ratings are
  conservative and honest (several "Med — until site re-fit / pilot offboarding owed").
- §5 lays out a concrete **G-011 certification path** (accredited IEC-61508/ISO-13849-1 assessment of the
  validator+sil_bridge+STO/SS1 path integrated with a certified PLC; integrator completes the cell RA). Good.

### 2.3 ISO/IEC 42001 internal audit — CREDIBLE pre-cert self-audit
- Covers clauses 4–10 + the 9 Annex-A control objectives, each rated against **cited live file paths**.
- Verdict 7/9 Conformant, 2 Partial, **0 major NCs, 3 minor NCs** is a realistic outcome for a project of this
  maturity. The three NCs (NC-1 management-review record, NC-2 ISO-42005 standalone impact assessment, NC-3
  customer/supplier records) are exactly the gaps a real auditor would flag and are **honestly disclosed and routed
  to Stage 24** — not hidden.

### 2.4 Annex IV / Annex-VI pack — STRUCTURALLY COMPLETE, with disclosed degradation
- 14 sections present; ML-DSA-65 signed footer; honestly labelled **conformity-assessment-READY, not a certificate**.
- **Disclosed degradation (correct):** section 8 (Record-keeping / Art-12) reads "audit_chain: DB not reachable at
  generation time — run `verify-audit-chain.py` against the live DB" because Docker was down at generation; section 7
  reports the **heuristic-only** red-team detection 0.7582 (not the full hybrid 0.9935 — i.e. it did NOT inflate the
  number). An assessor wants disclosed limitations, not silent gaps — this passes.

---

## 3. Readiness verdict (mock assessor)

**READY-FOR-DRY-RUN / SUBSTANTIALLY CONFORMANT for a pre-certification internal-control file — NOT certifiable today.**

The internal-control conformity FILE is real, self-attesting (signatures, cited evidence), and honestly bounded. For a
*real* assessment to proceed the submitter must close the 3 minor NCs, regenerate the pack with the DB up (Art-12
section), and (for the functional-safety claim) engage an accredited body + certified PLC (G-011). None of these is a
showstopper for the *dry-run*; all are correctly routed forward.

---

## 4. Honesty check (no overclaim)
- No artefact claims certification, an accredited body, a real notified body, or a completed customer pilot. **Confirmed.**
- The Docker-down degradation of the Art-12 audit-chain summary is **explicitly disclosed** in the pack and the ADR.
- The functional-safety posture is consistently "amenable to / SIL-amenable, NOT certified."

---

## 5. ADDITIONAL gaps a real assessor would raise → route to Stage 24

| # | Finding (assessor view) | Severity | Route |
|---|---|---|---|
| EA-1 | NC-1 management-review record (ISO 42001 cl. 9.3) not authored | minor | Stage 24 (already NC-1) |
| EA-2 | NC-2 standalone **ISO/IEC 42005** AI-system impact assessment not authored (inputs exist) | minor | Stage 24 (already NC-2) |
| EA-3 | NC-3 customer/supplier AI-responsibility records — needs a real pilot | minor (blocked) | Stage 24 / pilot (G-035/G-043) |
| EA-4 | Final Annex-IV pack must be **regenerated with the DB up** so the Art-12 record-keeping section is populated + `verify-audit-chain.py` exit-0 attached as evidence | medium | Stage 24 (Docker-gated) |
| EA-5 | The governance MAC/RBAC layer is **not yet wired into a live enforcement point** (pure-logic library + tests only); an assessor would ask "where is it called in the runtime?" — wire it into a request/decision path so the audited allow/deny rows actually appear in `audit_chain` | medium | Stage 24 |
| EA-6 | Functional-safety certification (G-011) — accredited IEC-61508 assessment + certified PLC at the `sil_bridge` seam | high (cert) | post-build / pilot |

These are recorded as new ledger rows (EA-4, EA-5) in `audits/OPEN_GAPS_LEDGER.md`; EA-1/2/3/6 are already ledgered
(NC-1/2/3, G-011).
