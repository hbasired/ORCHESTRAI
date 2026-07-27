# Stage 25 — Independent Review (post-GA operations)

**Reviewer**: independent `task-auditor` (DIFFERENT agent than the implementer)
**Date**: 2026-07-03
**Task doc**: `tasks/STAGE_25_post_ga.md`
**Status**: COMPLETE.

## Verdict (summary — full reasoning at the bottom)

**PASS-WITH-GAPS.** No theatre; every headline number reproduced live (full suite 365/10/0, audit 364, chain
428/349 exit 0, load test 8 exactly-once + 4 suppressed, pgaudit proven, Langfuse 3.203.3 OK, sweep honestly
`insufficient_history`). Must fix before close: F1 (skill.yaml wrong module path), F2 (nightly crypto gate
false-positive grep), F3 (nightly job install step broken on trixie Py3.13), F5 (KB_TASK_LOG entry + KB/risk
updates still owed; audit doc claims them prematurely).

## Work log (what has been done so far)

- [x] Read task-auditor SKILL.md, task doc, mechanical audit `audits/STAGE_25_audit.md`.
- [x] Read `backend/jobs/post_market_anomaly_sweep.py`, `backend/agents/runtime/shard_router.py`,
      `backend/api/ops_routes.py`, ops-router mount in `backend/main.py` (confirmed at main.py:400-401).
- [x] Read tests (jobs / scale / api), docker pgaudit + langfuse changes, nightly-evals crypto job, DVC skill,
      drill doc, Q3 report, ADR.
- [x] Re-run stage suites dynamically (jobs / scale / ops_routes) — 21 passed.
- [x] Live sweep dry-run; chain verify; seq 427/428 rows; pgaudit probe; Langfuse health; DVC; audit.sh; ledger rows.
- [x] Theatre hunt + deferral honesty check.
- [x] Full-suite re-run: 365 passed / 10 skipped / 0 failed (469s) — exact reproduction.
- [x] Final verdict: PASS-WITH-GAPS.

## Static review findings (code + docs read in full)

### Code quality / honesty (adversarial read)

- `backend/jobs/post_market_anomaly_sweep.py` — CLEAN. `analyse()` genuinely returns
  `status="insufficient_history"` with `anomalies: []` below 14 days (jobs/post_market_anomaly_sweep.py:141-147);
  no fabricated score anywhere; `sweep()` raises `RuntimeError` with no DSN (line 180) — honest-unavailable, not a
  fake return. Detectors are real math (median/MAD modified-Z; sklearn IsolationForest with `random_state=0` for
  determinism). Non-dry runs append a signed `post_market.sweep` audit row. One SOFT spot noted: the audit-append is
  wrapped `try/except → WARN` (lines 197-198), so a failed evidence write does not fail the sweep — defensible for a
  nightly job (stderr WARN + `audit_seq: null` in the report is visible), but the row is the Art-72 evidence; noted
  as an observation, not a violation (the failure is surfaced, not hidden).
- `backend/agents/runtime/shard_router.py` — CLEAN. Advisory lock is a real cross-connection
  `pg_try_advisory_lock`; the at-most-once ledger is a real `INSERT ... ON CONFLICT DO NOTHING` claim with
  failed-run unclaim; duplicates return NAMED statuses (`duplicate_suppressed` / `already_processed`), never a
  silent re-run. The no-DB fallback is explicitly labelled single-process-only in the docstring (honest degradation,
  not hidden). Warm-first fan-out rationale documented (import-lock deadlock class).
- `backend/api/ops_routes.py` — CLEAN. Reads ONLY `audit_chain`; raises HTTP 503 with an explicit
  honest-unavailable detail when no DSN / PG unreachable (lines 31-39); latencies computed from real row timestamps;
  no hardcoded cascade/sweep data in the HTML (it fetches the endpoints client-side). Mounted in `backend/main.py`
  lines 400-401 — confirmed.
- Tests are honest: `tests/jobs/` asserts the insufficient-history honest-empty invariant, spike detection,
  determinism, no-DB-raises; `tests/scale/` asserts 8 processed exactly once + 4 suppressed + full node trajectory
  per processed run and PRINTS throughput rather than asserting a made-up SLA; `tests/api/test_ops_routes.py`
  asserts honest-503 without DB + live chain reads (`chain_rows >= 428`). No no-op/always-pass tests found.
- `docker/postgres-pgaudit.Dockerfile` — real (FROM pgvector/pgvector:pg15 + postgresql-15-pgaudit); honest comment
  that the live container was enabled in-place and the Dockerfile is the durability path.
- `docker/docker-compose.observability.yml` — Langfuse v3 fixes are real config (CLICKHOUSE_MIGRATION_URL,
  CLUSTER_ENABLED=false, ENCRYPTION_KEY, MinIO S3 + worker). Dev-only default secrets (`changeme_dev_salt`, zero
  ENCRYPTION_KEY) are env-overridable — acceptable for a local dev overlay.
- `.github/workflows/nightly-evals.yml` — `crypto-deep-openssl35` job present (debian:trixie-slim, checks
  `openssl version | grep -E "3\.[5-9]"`, runs `tests/crypto/ -v -rs`, and FAILS on a skip of the deep tests via
  `! grep -iE "SKIPPED.*(slh|hybrid|openssl)"`). The gate is real. (Cannot execute a GitHub-hosted nightly job
  locally; verified by read. The skip-grep pattern depends on skip reasons containing slh/hybrid/openssl — the
  existing crypto skip markers do; pattern is adequate, slightly brittle.)

### Discrepancies found in static review

1. **`data/skills/bearing_overheat_response/skill.yaml` names a non-existent path** — the `verify` step says
   `executes: backend/ml/plan_verifier.py`; the real module is `backend/services/plan_verifier.py` (verified on
   disk). The file's own header claims "every step names the live module that executes it," so a wrong path is a
   (minor) honesty defect in the artifact. All 10 other referenced paths verified present.
2. Task-doc "Files to CREATE" table (template-era, May) says `compliance/post-market-monitoring/2026-Q4.md` and
   `frontend-nextjs/src/app/post-market/page.tsx`; what shipped is `2026-Q3.md` (correct quarter for 2026-07) and a
   backend `/ops/` HTML page instead of a Next.js page. The checked acceptance criteria describe what actually
   shipped, so this is a doc-drift note, not a faked criterion. `audits/STAGE_25_a2a_federation.md` was NOT created —
   consistent with the honestly-deferred federation AC (buyer-blocked).

### Deferral honesty check (docs)

- `audits/STAGE_25_pqc_drill.md` — explicitly says **LOCAL live env, no customer pilot exists (G-035)**; caveats
  single-node scope + grace-window verification pending. HONEST.
- `compliance/post-market-monitoring/2026-Q3.md` — explicitly labelled REHEARSAL, "must not be read as
  field-performance evidence", "no deployed customer", Art-73 row says "NONE — and none possible". HONEST.
- ADR `2026-07-02_stage25_post_ga_ops.md` — deferrals R1-R4 + federation partner + G-077 named as buyer-blocked;
  throughput labelled "a laptop measurement, not an SLA". HONEST.

## Dynamic verification (commands I ran myself, 2026-07-03, live Docker stack)

All runs used the SYSTEM python from `d:/ai-embodied-agent/backend` with
`DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing`, Neo4j bolt://localhost:7687,
Redis 6379, `MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5`, `MEM0_EMBED_DIM=384`, `PG_POOL_MAX=8`.

| # | Command | Claimed | Independently measured | Match |
|---|---|---|---|---|
| 1 | `python -m pytest tests/jobs/ tests/scale/ tests/api/test_ops_routes.py -q -s` | 10 + 7 + 4 tests pass | **21 passed** in 68.8s (0 failed, 0 skipped — DB-gated legs RAN live) | YES |
| 2 | G-066 load test (inside #1) | 8 distinct exactly-once + 4 dupes suppressed, 6 workers, 50s, 0.16/s | `processed=8 suppressed=4 workers=6 elapsed=55.87s throughput=0.143/s backend=postgres` | YES (throughput within laptop variance; the invariant — 8 exactly-once + 4 suppressed — reproduced exactly) |
| 3 | `python -m jobs.post_market_anomaly_sweep --dry-run` | honest `insufficient_history`, no anomaly claim | `{"status": "insufficient_history", "days_observed": 7, "days_required": 14, "anomalies": [], "dry_run": true}`, exit 0 (7 days now vs 6 at drill time — a day passed; consistent) | YES |
| 4 | `python scripts/verify-audit-chain.py` | exit 0; 428 rows; all 349 post-cutover sigs verify | `Audit chain OK (428 rows; hash chain intact; all 349 post-cutover signatures verify)`, exit 0 | YES |
| 5 | `SELECT seq, action, actor FROM audit_chain WHERE seq IN (427,428)` | seq 427 `post_market.sweep`, seq 428 `key_rotation` | `427\|post_market.sweep\|job:post_market_anomaly_sweep` and `428\|key_rotation\|crypto.key_manager`; count(*)=428, max(seq)=428 | YES |
| 6 | pgaudit: `SHOW shared_preload_libraries` + my own probe CREATE/INSERT/DROP + `docker logs \| grep AUDIT:` | pgaudit live, AUDIT: lines proven | `shared_preload_libraries = pgaudit`; my probe produced **3 fresh `AUDIT:` lines** (DDL CREATE TABLE, WRITE INSERT, DDL DROP) — reproduced with MY OWN statements, not the implementer's | YES |
| 7 | `curl http://localhost:3001/api/public/health` | `{"status":"OK","version":"3.203.3"}` | exactly that | YES |
| 8 | `dvc status` | clean | "Data and pipelines are up to date."; `data/skills.dvc` staged in git | YES |
| 9 | `bash scripts/audit.sh` (no --baseline) | TOTAL 364 flat | **TOTAL 364** (same per-category counts as `audits/STAGE_25_audit.md`) | YES |
| 10 | Full suite `python -m pytest -q` (live stack) | 365 passed / 10 skipped / 0 failed | **365 passed, 10 skipped, 0 failed in 469.03s (7:49)** — exact reproduction | YES |
| 10a | `verify-audit-chain.py` AFTER my full-suite re-run | chain head unchanged by tests | still **428 rows, all 349 sigs verify, exit 0** — R1 test isolation held under an independent adversarial re-run | YES |
| 10b | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/` (Langfuse UI root) | HTTP 200 (G-067 render claim) | HTTP 200 | YES |
| 11 | `research/stage-explainers/STAGE_25/index.html` + `compliance/post-market-monitoring/reports/2026-07-02.json` exist | shipped | both exist; the report JSON matches the seq-427 sweep (`insufficient_history`, 6 days, `audit_seq: 427`, `dry_run: false`) | YES |
| 12 | `audits/OPEN_GAPS_LEDGER.md` rows | G-021/060/061/067 RESOLVED; G-055/070 re-checked OPEN; G-066 FOOTHOLD | all seven rows updated exactly as claimed, with evidence text | YES |

**Test-isolation cross-check (unprompted):** the real chain head was 428 BEFORE my re-run of the load test
(which drives 8 incidents through the full runtime, including the audit-writing `log` node) and STILL 428 after —
the Stage-22 `AUDIT_CHAIN_DATABASE_URL` conftest isolation is demonstrably load-bearing. No pollution of the
attestable chain by my adversarial re-run.

**Theatre-hunt grep** over the stage's new code (`backend/jobs/**`, `agents/runtime/shard_router.py`,
`api/ops_routes.py`) for `random.uniform|random.choice|Math.random|generateMockState|_get_demo_|RESPONSES = {|MODELS = [`:
**zero matches**. Dict-literal/constant-fabrication sweep (Rule 1a, grep-invisible class): every return path in the
three new modules traced — no fabricated fallback returns found; failure paths raise or return 503/named statuses.

## Per-criterion evidence table

| Acceptance criterion (task doc) | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| G-060 pgaudit RESOLVED | live + AUDIT: lines + durable Dockerfile | **YES** | `shared_preload_libraries=pgaudit`; my OWN probe produced 3 AUDIT: lines; Dockerfile real |
| G-061 DVC skill RESOLVED | skill.yaml + dvc clean | **YES (with 1 defect)** | `dvc status` clean; skill.yaml real playbook — but one `executes:` path is wrong (F1 below) |
| G-067 Langfuse RESOLVED | health OK + UI render, overlay fixed | **YES** | health `{"status":"OK","version":"3.203.3"}`; UI root HTTP 200; compose fixes are real config |
| G-070 / G-055/56 re-checked, still OPEN | drill done, pin-blocked | **YES** | ledger rows updated with evidence; honest OPEN status |
| G-066 foothold (shard_router + load test) | 8 exactly-once + 4 suppressed, 6 workers | **YES** | reproduced live: processed=8 suppressed=4 workers=6 elapsed=55.87s (0.143/s); code is real advisory-lock + ledger |
| Nightly `crypto-deep-openssl35` job | added; skip-of-deep-tests = failure | **PARTIAL — job present but has 2 defects (F2, F3)** | gate will false-positive on a legitimate reverse-skip; install step likely breaks on trixie Py3.13 |
| G-021 ops routes RESOLVED | real audit_chain only, honest-503, 4/4 tests | **YES** | 4 tests pass live; 503 path verified in test; no fabricated data anywhere |
| Art-72 sweep operational | 10/10 tests, seq 427, honest insufficient_history | **YES** | 10 tests pass; dry-run reproduced `insufficient_history` (7 days); seq 427 row + report JSON confirmed |
| PQC rotation drill | seq 428, chain 427→428, all sigs verify | **YES** | seq 428 `key_rotation` (identity) confirmed in DB; chain verifies exit 0 (428 rows / 349 sigs) |
| Q3 post-market report | labelled REHEARSAL | **YES** | explicit "must not be read as field-performance evidence"; Art-73 row honest |
| Deferred: R1 real pilot, R2 go-live wiring, federation partner | buyer-blocked | **YES — honest** | task doc, ADR, drill doc, Q3 report all consistent; `STAGE_25_a2a_federation.md` correctly NOT written |
| Full suite | 365 / 10 / 0 | **YES** | exact reproduction |
| Audit baseline | 364 flat, waived (ops stage) | **YES (with process note F5)** | audit.sh reproduced 364; waiver justified in ADR; KB_TASK_LOG justification NOT YET WRITTEN (owed before close) |

## Findings (gaps — must fix before close unless noted)

**F1 (minor, fix before close) — `data/skills/bearing_overheat_response/skill.yaml` names a non-existent module.**
The `verify` step says `executes: backend/ml/plan_verifier.py`; the real module is
`backend/services/plan_verifier.py` (verified on disk; `backend/ml/plan_verifier.py` does not exist). The file's
own header claims "every step names the live module that executes it" — so this is a (small) unverified-claim
defect in a G-061 deliverable. One-line fix + `dvc` re-hash.

**F2 (moderate, fix before close) — the new nightly `crypto-deep-openssl35` gate will FALSE-POSITIVE-FAIL on
every run.** `backend/tests/crypto/test_pqc_slh_dsa.py:37-42` (`test_honest_unavailable_is_not_faked`)
legitimately SKIPS on an OpenSSL-3.5 runner with reason "OpenSSL 3.5 present — unavailability path not
exercisable here". With `-rs` that summary line contains both "slh" (filename) and "OpenSSL" (reason), so the
gate `! grep -iE "SKIPPED.*(slh|hybrid|openssl)"` (.github/workflows/nightly-evals.yml:88) matches it and fails
the job even when every deep test RAN and passed. **Empirically proven during this review** on the OpenSSL-3.5
host: `python -m pytest tests/crypto/ -v -rs` → **17 passed, 2 skipped** (every SLH-DSA/hybrid-TLS deep test RAN
and passed), then applying the exact gate grep to that output matched
`SKIPPED [1] tests\crypto\test_pqc_slh_dsa.py:40: OpenSSL 3.5 present ... not exercisable here` → "GATE WOULD
FAIL". The Stage-22 per-PR job's own local verification ("17 passed / 2 skipped" per ci.yml:545) shows the same
skip occurs on trixie. Fail-loud, not theatre — but the shipped gate cannot go green as written. Fix: anchor the
grep to the availability-skip reason (e.g. `"not on PATH"`) or deselect the reverse-skip test.

**F3 (moderate, fix before close) — the same nightly job's install step is likely broken on debian:trixie-slim.**
The job pip-installs the FULL `backend/requirements.txt` into a venv on trixie, whose python3 is **3.13.5**
(verified live in the container). `numpy==1.26.4` ships wheels only for cp39–cp312, and the job installs no build
toolchain — so `pip install -r requirements.txt` should fail before pytest ever runs (live confirmation attempt
recorded below). The Stage-22 per-PR `crypto-openssl35` job avoided precisely this by installing ONLY the crypto
deps (ci.yml:555-557). Fix: mirror the per-PR job's dependency set (the crypto suite needs dilithium-py/kyber-py/
jcs/pytest/httpx/cryptography, not torch/numpy/TF), or pin a python3.11 toolchain.
*(Note: the full-requirements install also cannot have been verified by the implementer — the ADR claims the job
was "appended", not run; GitHub-hosted nightlies can't run locally, but a container dry-run like Stage 22's was
feasible and was not done.)*

**F4 (trivial) — drill-doc rotation ledger incomplete.** `audits/STAGE_25_pqc_drill.md` says the `key_rotation`
rows are "seq 428 (identity, this drill) + seq 223 (tls, Stage-18 era)"; the live chain also holds seq **221
(firmware)** and **222 (identity)** key_rotation rows (verified by SQL). Cosmetic doc inaccuracy.

**F5 (process, fix before close) — premature past-tense claim in the mechanical audit + KB updates still owed.**
`audits/STAGE_25_audit.md` §6 says the flat-baseline waiver is "Justified in `knowledge-base/KB_TASK_LOG.md`
(Stage 25 entry)" — but KB_TASK_LOG.md (1963 lines) contains NO Stage 25 entry yet (last entry: 2026-07-02
out-of-band strategic audit). Likewise the task doc's "Files to MODIFY" updates are not yet applied: KB_18's
Art-72 row still reads "live-ops dashboard render at Stage 25" (not `shipped`), KB_10 has no Stage-25 live-ops
invariants, and the risk-register quarterly refresh (Q3 report §4 says "next due at Stage-25 close") is pending.
Per the §5 lifecycle these steps legitimately come AFTER this review and BEFORE `close-task.sh` (which enforces
the KB_TASK_LOG entry) — so this is not a faked criterion, but the audit doc's claim is written as already-done
(verify-don't-assert, Rule 1a-adjacent). Close MUST NOT proceed until the KB_TASK_LOG entry (with the
`--no-baseline-drop` justification), the KB_18/KB_10/KB_13/KB_16 updates, and the risk-register refresh land.

**F6 (doc-drift note, no action beyond the task doc's own honesty) —** the template-era "Files to CREATE" table
names `compliance/post-market-monitoring/2026-Q4.md` and `frontend-nextjs/src/app/post-market/page.tsx`; what
shipped is `2026-Q3.md` (the correct quarter for 2026-07) and a backend `/ops/` self-contained HTML page. The
checked ACs describe what actually shipped, so no criterion was faked; noting for the record.

**Observations (not gaps):** (a) the sweep's audit-append is `try/except → stderr WARN + audit_seq:null`
(jobs/post_market_anomaly_sweep.py:197-199) — a failed Art-72 evidence write does not fail the sweep; surfaced,
defensible, but consider exit-nonzero on append failure in a later increment. (b) The nightly gate's comment
says "no skips allowed" while the grep only forbids slh/hybrid/openssl skips — the DB-gated
`test_audit_chain_signing.py` will silently skip in that job (no PG service); wording nit, subsumed by F2/F3.
(c) Baseline flat-at-364 deviates from the task doc's own "Audit target: strict decrease", but the waiver is
explicitly justified (additive ops stage; the de-mock of the 364 is Stage 28's job per the signed
2026-07-02 strategic ADR) and follows the long-standing precedent of protocol/infra stages 13.5-24.

## Verdict

**PASS-WITH-GAPS.**

No theatre found: every fabrication-surface in the three new modules was read line-by-line; failure paths raise,
503, or return named suppression statuses — never a fabricated value. Every headline number reproduced live and
independently: full suite **365/10/0**, audit **364**, chain **428 rows / 349 sigs / exit 0**, seq **427 + 428**
rows present, load test **8 exactly-once + 4 suppressed**, pgaudit AUDIT: lines from my own probe, Langfuse
**3.203.3 OK**, sweep honestly reports `insufficient_history` with an empty anomalies list. Deferrals are honest
and consistently labelled across all documents.

The gaps are real but bounded: two defects in the new nightly workflow (F2 false-positive gate, F3 broken install)
mean the "nightly deep-crypto gate" AC is shipped-but-not-yet-runnable and must be fixed before close; one wrong
path in the DVC skill (F1); and the lifecycle tail (KB_TASK_LOG entry + KB/risk-register updates, F5) is still
owed before `close-task.sh`. None of these undermines the honesty of what was measured.

**Must fix before close:** F1, F2, F3, F5 (F4 optional cosmetic).

---
*Reviewer independence statement: I did not implement any part of Stage 25. All dynamic numbers above come from
commands I executed myself on 2026-07-03 against the live Docker stack (PG@5544 / Neo4j@7687 / Redis@6379).*
