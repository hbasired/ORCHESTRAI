# ADR — Stage 22: Pilot deployment runbook + post-market monitoring + CTO #4 remediations

**Date**: 2026-06-22
**Status**: Accepted (Stage 22 — follows Stage 21.5 CTO Checkpoint #4)
**Author persona**: `agentic-governance-engineer` (+ devops-sre / compliance / backend / security-pqc)
**Relates**: KB_10 (production hardening), KB_15 (observability), KB_18 (governance evidence). Research §32. Hard Rule 9
(free/local), Rule 1a (no fabrication / honest deferral), Rule 11 (research-first). Pays CTO #4 **R1, R2, R3, R6, R8**
(+ the buildable half of **R11**); routes R4/R5/R7/R9/R12 forward.

---

## Context

CTO #4 (Stage 21.5) said: before a pilot, the system must add the deploy/monitoring half of production-readiness and pay
the doable Stage-22 remediations, gating on G-1 (audit-chain green) + G-2 (register refresh). The REAL customer pilot
(R11/G-035/G-043) needs a buyer + real fleet and is not free/local-buildable — so this stage ships everything that makes
a pilot START possible and is honest that the engagement itself is deferred.

## Decisions

**D1 — Pilot deployment runbook (AC1).** `compliance/pilot-deployment-runbook.md`: a pre-flight gate (audit-chain green,
tested restore, red-team gate, safety trace-pairing, SBOM/SAST, Annex IV builds, DB least-privilege, full suite), an SRE
deploy strategy (shadow → assisted → supervised-autonomous canary; rollback criteria + steps + named owner), SLO drafts,
the EU-AI-Act **Article-26 deployer checklist**, the §4 go-live wiring of the not-yet-load-bearing surfaces (R4/R5), and
on-call/escalation. Pairs with the Stage-21 DR runbook (recovery half).

**D2 — Post-market monitoring (AC2, Art-72).** `compliance/post-market-monitoring-plan.md` maps each Chapter-III §2
dimension → an already-built signal (spans / evals / audit-chain verify / DR drills / RLS) → a threshold/trigger, with
cadence + the serious-incident path. Art-72 requires the PMM plan to be PART OF Annex IV → `generate-annex-iv-doc.py`
now ingests it into section 11 (Human-in-use & post-market monitoring, Art-26/72); pack regenerates (14 sections, signed).

**D3 — R8/G-076: connection-enforced RLS (AC4).** Migration `0009` makes `mem0_app` a NON-superuser LOGIN role;
`mem0_adapter._connect_ns` connects AS `mem0_app` directly (via `_mem0_app_dsn`, password from `MEM0_APP_PASSWORD` →
`POSTGRES_PASSWORD` → dev default), so Postgres FORCE RLS is enforced by the CONNECTION ROLE — it holds even if a path
forgets `SET ROLE`. Honest fallback to superuser + best-effort `SET ROLE` if the login role is unavailable; the Python
`_authorize` stays the first gate. Verified live: a direct `mem0_app` client sees 0 rows with the namespace unset
(connected as a non-superuser), 1 with the right namespace.

**D4 — R1/G-1: durable audit-chain test-isolation (AC5).** `audit_chain._dsn()` prefers `AUDIT_CHAIN_DATABASE_URL`; a
session-autouse conftest fixture (`_isolate_audit_chain`) spins up a throwaway migrated DB for the test run and drops it,
so test runs NEVER pollute the attestable chain. Verified: the real chain head stayed 421 across the full suite; a test
write lands in the isolated DB, not the real one. (Also fixed a latent test bug the isolation exposed — a signing test
read back from the raw DSN instead of the chain's DSN.)

**D5 — R6: OpenSSL-3.5 CI gate (AC7).** New CI job `crypto-openssl35` runs in a `debian:trixie-slim` container (OpenSSL
3.5.6, native ML-KEM/ML-DSA/SLH-DSA) so `tests/crypto/` (hybrid-TLS handshake, SLH-DSA, ML-KEM/ML-DSA) are GATE-enforced
on every PR instead of skipping on the OpenSSL-3.0 ubuntu runners. Verified locally in the same container: 17 passed / 2
skipped (DB-gated).

**D6 — R3: verified already-clean (AC3, honesty).** The CTO #4 R3 finding (two `sbom:` jobs) did NOT reproduce: exactly
ONE blocking `sbom` job (cyclonedx 7.3.0), no version drift, register pip-audit wording already correct — the duplicate
was removed in Stage 18 (ci.yml line-544 note). Recorded as already-resolved, not fabricated.

**D7 — R2 register refresh (AC6)** + **D8 — R11 buildable half (AC9, AC10):** `compliance/pilot-onboarding-kit.md`
(onboarding checklist + data-intake spec + A/B-measurement protocol + real-fleet re-fit plan) so a real engagement can
start day-one; go-live wiring (R4/R5) specified in the runbook §4. The actual customer pilot + published A/B remain
honestly DEFERRED (need a buyer/real fleet — Rule 9), ledgered G-035/G-043.

## Verified live (Docker up, 2026-06-22)

| check | result |
|---|---|
| R8 RLS by connection role | `mem0_app` LOGIN non-superuser; direct client ns-unset → 0 rows, right-ns → 1; mem0 tests 13 pass |
| R1 chain isolation | full suite ran; real `audit_chain` head **421 unchanged**; isolation test + 8 audit-chain tests pass |
| R6 OpenSSL-3.5 gate | `debian:trixie-slim` OpenSSL 3.5.6 → `tests/crypto/` **17 passed / 2 skipped** |
| Annex IV + PMM | pack regenerates 14 sections, PMM plan ingested (Art-72), ML-DSA-65 signed |
| R3 | exactly one blocking `sbom` job; no drift (already-clean) |
| Full suite | **335 passed / 10 skipped / 0 failed**; `audit.sh` holds **364** |

## Consequences
- New: `compliance/{pilot-deployment-runbook,post-market-monitoring-plan,pilot-onboarding-kit}.md`,
  `backend/alembic/versions/0009_mem0_app_login_role.py`, `backend/tests/memory/test_audit_chain_test_isolation.py`,
  CI job `crypto-openssl35`. Modified: `mem0_adapter.py` (direct mem0_app login + fallback), `audit_chain._dsn`
  (`AUDIT_CHAIN_DATABASE_URL`), `tests/conftest.py` (audit-isolation fixture), `tests/crypto/test_audit_chain_signing.py`
  (read-back DSN fix), `scripts/generate-annex-iv-doc.py` (PMM ingest), `risk-register.md` (R2), KB_10/KB_18. **No new deps.**

## Honest residual / ledger
- **RESOLVED:** R8/G-076 (connection-enforced RLS), R1/G-1 (test-isolation; G-079 audit-chain-pollution tail), R6
  (crypto PR gate), R2 (register), R3 (already-clean). **R11 buildable half** shipped (onboarding kit).
- **DEFERRED (honest, ledgered):** R11/G-035/G-043 real customer pilot + published A/B (need a buyer/real fleet);
  R4 A2A live-mTLS + R5 first-real-PLC `sil_bridge` hardening (wire AS the pilot goes live — runbook §4); R7 cascade UI
  (G-021); R9 continuous anomaly detection (G-064 tail); R12 carry-forward low/medium (G-066 scale, G-060 pgaudit,
  G-067, G-070, G-055/G-056). R10 → Stage 23 (conformity dry-run).
- Conformity is NOT certified — Stage 23 dry-run + a notified body. The system is pilot-DEPLOYABLE (shadow/assisted),
  not yet running a real pilot. Nothing faked.

## References
- `compliance/pilot-deployment-runbook.md` · `compliance/post-market-monitoring-plan.md` ·
  `compliance/pilot-onboarding-kit.md` · `backend/alembic/versions/0009_mem0_app_login_role.py` ·
  `.github/workflows/ci.yml` (`crypto-openssl35`) · research §32 · CTO #4 review §8. EU AI Act Art-26/72; SRE PRR.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-26T16:02:01+00:00 -->
<!-- signature: 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 -->
