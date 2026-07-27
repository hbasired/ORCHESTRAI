# Stage 22 — Independent Review

**Auditor:** independent `task-auditor` (did NOT implement Stage 22)
**Date:** 2026-06-26
**Stage:** 22 — pilot deployment runbook + post-market monitoring + CTO #4 remediations (R1/R2/R3/R6/R8 + buildable half of R11; defers R4/R5/R7/R9/R12, R10→23)
**ADR:** `compliance/decision-logs/2026-06-22_stage22_pilot_deployment_runbook.md`
**Mode:** DYNAMIC (live Docker stack up; tests + DB + crypto-version all reproduced)

## VERDICT: PASS

All three load-bearing claims reproduced live against the running stack, both honesty checks confirmed, audit holds at 364, and every deferral is explicitly and accurately marked. No theatre, no bypass, no overclaim. This stage is governance/remediation (no new fabrication surface), so the flat audit count is legitimate.

## Load-bearing checks
| # | Claim | DYNAMIC/static | Reproduced? | Note |
|---|---|---|---|---|
| R8 | RLS by connection role (`mem0_app` non-superuser LOGIN; ns-unset → 0 rows) | DYNAMIC | **YES** | `pg_roles` → `mem0_app\|t\|f\|f` (login, NOT super, NOT bypassrls). `psql -U mem0_app` with namespace UNSET → **0 rows**. Adapter `_connect_ns` connects AS `mem0_app` via `_mem0_app_dsn` (direct login), honest fallback to superuser+`SET ROLE` if login role absent. Migration `0009` sets `ALTER ROLE mem0_app LOGIN NOSUPERUSER NOBYPASSRLS …` — matches. |
| R1 | audit-chain test isolation (real head unchanged after tests; verify exit 0) | DYNAMIC | **YES** | Real head **421 before** tests; isolation+signing tests **3 passed**; real head **421 after** (no pollution). `verify-audit-chain.py` → exit **0**, "Audit chain OK (421 rows; hash chain intact; all 342 post-cutover signatures verify)". `audit_chain._dsn` prefers `AUDIT_CHAIN_DATABASE_URL`; conftest `_isolate_audit_chain` creates/migrates/drops a throwaway DB with honest fallback. |
| R6 | OpenSSL-3.5 crypto CI gate (debian:trixie OpenSSL 3.5.x) | DYNAMIC | **YES** | `debian:trixie-slim` → **OpenSSL 3.5.6**. CI job `crypto-openssl35` present (ci.yml:533) in a `debian:trixie-slim` container, runs `tests/crypto/` on every PR, and adds a defensive assert that aborts if OpenSSL `< 3.5` (ci.yml:545-548) — the gate is real, not skip-by-default. (Did not re-run the 17-test crypto suite in-container; static read + version proof suffice, per scope.) |
| R3 | exactly one `sbom:` job (ADR D6 honesty) | static | **YES** | `grep -c '^  sbom:' ci.yml` → **1**. ADR claim "exactly ONE blocking sbom job, duplicate removed in Stage 18" is TRUE — not fabricated. |
| Deferrals | pilot/A2A mTLS/sil_bridge honestly deferred; conformity NOT certified | static | **YES** | Runbook: shadow→assisted posture; R4 (A2A mTLS) + R5 (sil_bridge first-PLC) "honest placeholders … wired as part of go-live"; real pilot + A/B (G-035/G-043) "Not yet done (need a buyer/real fleet)"; "Conformity is NOT certified — Stage-23 dry-run + notified body come next." PMM plan + onboarding kit both carry explicit "Honest status" deferral sections. |
| audit.sh | count == 364 | DYNAMIC | **YES** | TOTAL **364** == `.audit-baseline` 364. Governance/remediation stage (additive, no fabrication introduced) — flat count is correct and consistent with the ADR's `--no-baseline-drop`-class rationale. |

## Findings (severity-ranked)
- **None blocking.** Every acceptance-criterion claim in the ADR's "Verified live" table was independently reproduced or confirmed by source read. The numbers in the ADR (head 421, mem0_app `t\|f\|f`, OpenSSL 3.5.6, single sbom job, audit 364) all match what I observed.
- **INFO (no action):** R8's honest-fallback branch (superuser + best-effort `SET ROLE`, mem0_adapter.py:125-132) is a graceful-degradation path, not the load-bearing one; the load-bearing path (direct `mem0_app` login) is what is active here and was proven (ns-unset → 0 rows as a non-superuser). Acceptable per Rule 1a (honest degradation, not theatre).
- **INFO (no action):** The R6 crypto suite itself was not re-executed in-container by this audit (scope-limited); the implementer's "17 passed / 2 skipped" stands un-reproduced but the *gate mechanism* (container OpenSSL 3.5.6 + assert + on-every-PR) is verified real.

## Deferrals — honesty assessment
Honest. The three new compliance docs and the ADR "Honest residual" all clearly mark as DEFERRED: the real customer pilot + published A/B (R11/G-035/G-043, "need a buyer/real fleet"), A2A live mTLS (R4), sil_bridge first-real-PLC hardening (R5), cascade UI (R7/G-021), continuous anomaly detection (R9), and R10→Stage 23. Conformity is explicitly NOT claimed certified. No deferred item is dressed up as done.

## New gaps
None. No new gap rows appended to `audits/OPEN_GAPS_LEDGER.md` — all residuals are pre-existing, correctly ledgered (G-035, G-043, G-064, G-066, G-067, G-070, G-075, etc.) with target stages.

## Commands run (read-only)
- `docker exec … pg_roles WHERE rolname='mem0_app'` → `mem0_app|t|f|f`
- `docker exec -U mem0_app … SELECT count(*) FROM mem0_memories` (ns unset) → `0`
- `docker exec … SELECT max(seq) FROM audit_chain` → `421` (before AND after tests)
- `pytest tests/memory/test_audit_chain_test_isolation.py tests/crypto/test_audit_chain_signing.py` → `3 passed`
- `python scripts/verify-audit-chain.py` → exit `0`, "Audit chain OK (421 rows … all 342 post-cutover signatures verify)"
- `docker run --rm debian:trixie-slim … openssl version` → `OpenSSL 3.5.6`
- `grep -c '^  sbom:' .github/workflows/ci.yml` → `1`
- `bash scripts/audit.sh` → TOTAL `364` (== baseline)
