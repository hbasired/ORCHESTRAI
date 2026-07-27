# ADR — Stage 21: Disaster Recovery, HA posture & backups (free-cost, OSS/local)

**Date**: 2026-06-22
**Status**: Accepted (Stage 21 — follows Stage 20 red-team eval harness)
**Author persona**: `devops-sre`
**Relates**: KB_10 (production hardening), KB_15 (observability/evidence). Research §31/§31.5. Hard Rule 9 (free/local),
Rule 1a (no fabricated results), Rule 11 (research-first). Pays **G-066** (DR/HA) + folds **G-004** (chaos) + the CTO #3
runtime-determinism remediation; touches **G-060** (DB audit/DR).

---

## Context

Before the Stage-22 pilot the stateful tier (Postgres source-of-truth + `audit_chain`, Neo4j ISA-95 graph, Redis cache)
needs a **tested** backup→restore→verify DR path, a runbook with RPO/RTO, and a resilience (chaos) drill. Constraint:
**free/OSS/local only** (Rule 9) — no paid cloud, no Neo4j Enterprise (so no online/differential graph backup).

## Decisions

**D1 — Postgres: logical dump + base backup + PITR-ready.** `scripts/backup/backup-postgres.sh` = `pg_dump -Fc`
(custom format; compressed; `pg_restore --list` integrity check) — the portable, restore-anywhere leg.
`scripts/backup/pg-basebackup.sh` = `pg_basebackup -Ft -z -Xs` physical base backup — the PITR anchor. Continuous WAL
archiving (`archive_mode=on` + `archive_command` + `archive_timeout=60` ⇒ RPO ≤ 60 s) is **config-provided but OFF by
default** (docker-compose comment + runbook): enabling it with an unreachable `archive_command` fills the WAL disk →
outage, so it's a deliberate pilot-enable, not a build-time default. `wal_level=logical` (Stage 13) already satisfies PITR.

**D2 — Neo4j (Community = offline) + Redis (cache).** `backup-neo4j.sh` briefly stops the container and runs a one-off
`neo4j-admin database dump` (data `neo4j` + `system`) via `--volumes-from` (online/differential is Enterprise-only).
The ISA-95 graph is also mirrored in Postgres (Stage 12) → PG is primary recovery, the Neo4j dump is the backstop.
`backup-redis.sh` snapshots `dump.rdb` (BGSAVE) — Redis holds no source-of-truth state (rebuildable from PG).
`backup-all.sh` orchestrates all three + a SHA-256 manifest + retention; PG failure fails the run, neo4j/redis are
best-effort.

**D3 — Tested restore is the BINDING deliverable.** `scripts/restore/restore-verify.sh` restores the latest dump into a
**scratch DB** and ASSERTS per-public-table row-count parity + the `audit_chain` head (seq + hash) parity against the
live source, exits non-zero on any mismatch, drops the scratch DB. "Never trust an untested backup."

**D4 — Chaos drill (G-004).** `scripts/chaos/kill-postgres-drill.sh` kills the PG container and asserts the system
**degrades honestly** (the probe + `verify-audit-chain.py` FAIL rather than fabricate — Rule 1a) then recovers on
restart. Measured, not claimed.

**D5 — HA posture (honest free scope).** True multi-node HA (streaming replication / automatic failover; Neo4j Community
has no clustering) is a **pilot/cloud** item. Build-time HA = `restart: unless-stopped` + healthchecks (already on all
stateful services) + the fast tested-restore DR path + the chaos drill. 3-2-1(-1-0): primary on-disk + `BACKUP_ROOT_2`
second medium + an `rclone` off-site target that is **config-only** (not exercised at build time — Rule 9).

**D6 — Runtime determinism regression test (CTO #3).** `backend/tests/agents/runtime/test_runtime_determinism.py`
asserts two runs of the same incident (distinct `thread_id`s ⇒ full re-execution, not checkpoint resume) produce
identical node trajectories + decisions.

**D7 — CI gate `dr-backup-restore`.** Starts a NAMED Postgres container (exercises the scripts' real `docker exec`
path), seeds a realistic schema, runs backup + restore-verify; FAILS on mismatch. Fast (no full-stack install).

## Verified live (Docker up, 2026-06-22)

| check | result |
|---|---|
| `backup-postgres.sh` + `pg-basebackup.sh` | dump 2.1 MB, integrity OK; base.tar.gz + pg_wal.tar.gz + manifest |
| `backup-neo4j.sh` | offline dump OK — `neo4j.dump` + `system.dump`; container auto-restart |
| `backup-redis.sh` / `backup-all.sh` | RDB snapshot OK; manifest with SHA-256 sums (pg+redis OK; neo4j OK after `--no-deps` fix) |
| **`restore-verify.sh`** | **PASS** — row-count parity (22 public tables) + `audit_chain` head parity; **RTO ~4 s** for the live DB |
| **`kill-postgres-drill.sh`** | **PASS** — honest degradation under fault (no fabrication) + clean recovery on restart |
| determinism test | **1 passed** (identical trajectory + decisions across two runs) |
| CI gate simulation | restore-verify PASS on a generic seeded schema (row + audit_chain parity) |

`bash scripts/audit.sh` holds **364** (additive bash/scripts + one test — outside the theatre-scanned tree).

## Consequences
- New: `scripts/backup/{lib.sh,backup-all.sh,backup-postgres.sh,pg-basebackup.sh,backup-neo4j.sh,backup-redis.sh}`,
  `scripts/restore/restore-verify.sh`, `scripts/chaos/kill-postgres-drill.sh`, `compliance/dr-runbook.md`,
  `backend/tests/agents/runtime/test_runtime_determinism.py`, CI job `dr-backup-restore`. Modified: `docker-compose.yml`
  (PITR doc block), `.gitignore` (backups), KB_10/KB_15, risk-register. **No new runtime deps** (uses docker + the
  bundled `pg_dump`/`pg_restore`/`neo4j-admin`/`redis-cli`).

## Honest residual / ledger
- **G-066 RESOLVED** (tested backup/restore/DR + runbook + RPO/RTO). **G-004 RESOLVED** (automated chaos drill).
- **Deferred to pilot/cloud (Rule 9):** multi-node HA / automatic failover; live off-site replication (config-only now);
  continuous WAL archiving is config-provided/OFF (enable per the compose comment). Recorded in the runbook §7 + risk
  register. **G-060** (pgaudit DB-level logging) remains a separate ledger item (the app-level `audit_chain` is the Art-12
  evidence).
- Process note (honesty): the first `backup-all` run FAILED neo4j (`--no-deps` is a compose flag, not `docker run`); the
  MSYS path-conversion bit the container-path args (`/tmp`, `/backups`) — both caught by running the scripts live and
  fixed (lib.sh `MSYS_NO_PATHCONV` + `docker_host_path`).

## References
- `scripts/backup/*` · `scripts/restore/restore-verify.sh` · `scripts/chaos/kill-postgres-drill.sh` ·
  `compliance/dr-runbook.md` · `docker/docker-compose.yml` · `.github/workflows/ci.yml` (`dr-backup-restore`) ·
  KB_10/KB_15 · research §31. PostgreSQL PITR docs; Neo4j Operations Manual (dump/load); 3-2-1 backup rule.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-26T09:46:25+00:00 -->
<!-- signature: 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 -->
