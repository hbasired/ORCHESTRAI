# GA Release Checklist — v1.0.0 (Stage 24)

> General-availability release readiness for the OSS Industrial Agent Control Plane. **GA = the open-source v1.0.0
> release** (the public contract is stable across Stages 0–23) + the EU-AI-Act provider placing-on-market READINESS
> rehearsal. Research §34. Honest scope: GA of the free/OSS/local platform — **NOT** a certified or commercially-sold
> product; the real customer pilot + certification are post-GA (need a buyer/accredited body — G-035/G-043/G-011).

## 1. Engineering readiness

| Item | Status | Evidence |
|---|---|---|
| All build stages 0–23 closed | ✅ | `knowledge-base/KB_TASK_LOG.md` |
| Full test suite green | ✅ | 344 passed / 10 skipped / 0 failed (live, Docker up) |
| Audit baseline held (no theatre) | ✅ | `.audit-baseline` = 364 across 24 stages |
| Every stage independently reviewed (different agent) | ✅ | `audits/STAGE_*_independent_review.md` |
| 4 CTO checkpoints passed | ✅ | `audits/CTO_{1..4}_review.md` |
| Audit chain verifies (Art-12) | ✅ | `verify-audit-chain.py` exit 0 (426 rows, all post-cutover verify) |
| DR backup + tested restore | ✅ | `scripts/restore/restore-verify.sh` (RTO ~4 s); `dr-runbook.md` |
| Red-team gate | ✅ | OWASP-LLM01 0.9935 hybrid / NIST 14/14; CI `phoenix-evals` + nightly |
| Governance MAC/RBAC/traceability LIVE-enforced | ✅ | G-080: A2A boundary + runtime decision.trace; live audited rows |
| SBOM + SAST + crypto gate | ✅ | CI `sbom` (blocking) + `bandit` + `crypto-openssl35` (OpenSSL 3.5) |
| No new/paid deps; free-cost (Rule 9) | ✅ | Groq free / Ollama / OSS / local throughout |

## 2. Documentation / release

| Item | Status |
|---|---|
| Version = **v1.0.0** (semver — stable public contract) | ✅ this stage |
| Release notes (`RELEASE_NOTES_v1.0.0.md`) | ✅ this stage |
| LICENSE (Apache-2.0 / MIT per PRD) | ⬜ confirm at tag (repo LICENSE) |
| README / getting-started current | ⬜ polish at tag |
| Stage explainers (research/stage-explainers/) | ✅ Stages 6–24 |

## 3. EU AI Act — provider placing-on-market obligations (Art-16) — READINESS

| Obligation | Readiness | Evidence / gap |
|---|---|---|
| Conformity assessment (Annex VI internal control) | rehearsed | Stage 23 dry-run; mock assessor SUBSTANTIALLY CONFORMANT |
| EU Declaration of Conformity (Art-47/Annex V) | template ready | `compliance/eu-declaration-of-conformity.md` (rehearsal) |
| CE marking (Art-48) | **DEFERRED** | needs completed conformity + legal-entity provider |
| EU-database registration (Art-49/71) | **DEFERRED** | needs the provider entity |
| Risk-management system (Art-9) | ✅ | `risk-register.md` + per-stage |
| Data governance (Art-10) | ✅ | dataset CARDs; real-fleet re-fit plan (onboarding kit) |
| Technical documentation (Art-11) | ✅ | Annex IV pack (14 sections, signed) |
| Record-keeping / logging (Art-12) | ✅ | `audit_chain` (append-only, ML-DSA-65 signed, verifies) |
| Transparency (Art-13) | ✅ | SHAP/DiCE explanations + docs |
| Human oversight (Art-14) | ✅ | HITL `interrupt()` on SIL-1+ |
| Accuracy/robustness/cybersecurity (Art-15) | ✅ | evals + PQC + hybrid TLS + zero-trust |
| ISO/IEC 42001 AIMS | ✅ internal | 2026-Q4 internal audit + management review |
| ISO/IEC 42005 impact assessment | ✅ | `iso-42005-impact-assessment.md` |

## 4. Honest GA statement / what GA does NOT mean
GA means: the OSS platform is **v1.0.0 stable, fully tested, independently reviewed, and conformity-assessment-READY**.
GA does **NOT** mean: certified, CE-marked, EU-registered, running a real pilot, or sold. Those require a legal-entity
provider + an accredited body + a buyer/real fleet, and are honestly deferred (G-011 cert, G-035/G-043 pilot, CE/registration).
Remaining open ledger items are post-GA (G-066 scale, G-060 pgaudit, G-067 Langfuse-UI, G-070 a2a-sdk, NC-3 customer records).

## 5. Sign-off
GA v1.0.0 approved by the 2026-Q4 management review (`iso-42001-internal-audit/2026-Q4_management-review.md`). Next:
Stage 24.5 — CTO Checkpoint #5 (final).
