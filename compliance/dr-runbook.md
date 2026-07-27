# Disaster Recovery Runbook (Stage 21)

> Free/OSS/local DR for the stateful tier. Scope: single-node dev/pilot-prep. Multi-node HA (streaming replication +
> automatic failover) and live off-site replication are **honestly deferred to the pilot/cloud** (Hard Rule 9 — no paid
> infra at build time). Research §31. ADR `2026-06-22_stage21_dr_ha_backups.md`. KB_10 (production hardening) / KB_15.

## 1. What is protected

| Store | Role | Backup method | Recovery source of truth |
|---|---|---|---|
| **PostgreSQL** (`pgvector/pgvector:pg15`) | **Source of truth** — incidents, decisions, `audit_chain`, mem0 vectors | `pg_dump -Fc` (logical) + base-backup/WAL archiving (PITR) | **Primary** |
| **Neo4j** (`5.15-community`) | ISA-95 equipment graph (also mirrored in PG, Stage 12) | offline `neo4j-admin database dump` (`neo4j` + `system`) | Backstop (PG mirror is primary) |
| **Redis** (`7-alpine`) | Cache / pubsub — **no source-of-truth state** | RDB snapshot (`BGSAVE` + copy `dump.rdb`) | Rebuildable from PG |

## 2. RPO / RTO targets

| Metric | Target | Basis |
|---|---|---|
| **RPO** (max data loss) | **≤ 60 s** with PITR (`archive_timeout=60` forces a WAL switch every 60 s); = backup interval for the logical-dump leg (e.g. hourly) | research §31.1 |
| **RTO** (time to restore) | **< 5 min** for the current DB size on this hardware | measured: `restore-verify.sh` restores + verifies the live DB (22 tables, ~2 MB) in **~4 s**; RTO scales with size (pgBackRest parallel restore keeps a 500 GB DB < 30 min) |
| **Backup integrity errors** | **0** (3-2-1-1-0) | every backup runs `pg_restore --list`; `restore-verify.sh` asserts row-count + `audit_chain` head parity |

## 3. Backup (routine)

```bash
bash scripts/backup/backup-all.sh        # pg + neo4j (brief offline) + redis; writes a SHA-256 manifest + prunes retention
```
Individual stores: `scripts/backup/backup-postgres.sh` · `backup-neo4j.sh` · `backup-redis.sh`.
Schedule out-of-band (cron / Task Scheduler) at the cadence matching the RPO target.

**3-2-1(-1-0) layout:** (3) ≥3 copies, (2) 2 media, (1) 1 off-site, (-1) 1 immutable, (-0) 0 errors.
- Copy 1: `backups/` (primary on-disk).
- Copy 2: set `BACKUP_ROOT_2=/mnt/external/...` → scripts copy each artefact to the second medium.
- Off-site: set `OFFSITE_RCLONE_REMOTE=s3:bucket/path` and run `rclone copy backups/ "$OFFSITE_RCLONE_REMOTE"` out-of-band.
  **Not exercised at build time (Rule 9 — no paid cloud); the hook is wired + documented for the pilot.**
- Immutable / 0-errors: the manifest carries SHA-256 sums; restore-verify is the 0-errors gate.

## 4. Restore + verify (the binding drill — never trust an untested backup)

```bash
bash scripts/restore/restore-verify.sh   # restores the latest pg_dump into a SCRATCH db, asserts row-count + audit_chain head parity, drops it
```
Exits non-zero on any mismatch or unreadable archive. Run it on a schedule (the SOTA "test your backups" practice).

## 5. Actual recovery (PostgreSQL is lost)

1. Stop the app/runtime so nothing writes during recovery.
2. Bring up a clean Postgres (`docker compose -f docker/docker-compose.yml up -d postgres`); wait for `pg_isready`.
3. Restore the latest dump:
   ```bash
   docker cp backups/postgres/<latest>.dump ai-agent-postgres:/tmp/r.dump
   docker exec ai-agent-postgres dropdb   -U aiagent --if-exists manufacturing
   docker exec ai-agent-postgres createdb -U aiagent manufacturing
   docker exec ai-agent-postgres pg_restore -U aiagent -d manufacturing --no-owner --exit-on-error /tmp/r.dump
   ```
   For **PITR to a precise moment**, restore the base backup and replay WAL with a `recovery_target_time` (see §31.1).
4. **Verify before reconnecting the app:** `python scripts/verify-audit-chain.py` must exit 0 (chain intact).
5. Reapply migrations if needed: `cd backend && alembic upgrade head` (no-op if the dump was current).
6. Restart the app; run `scripts/chaos/kill-postgres-drill.sh`-style probe to confirm health.

**Neo4j:** stop the container → `neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true`
(+ `system`) → start. If Neo4j is unrecoverable, repopulate ISA-95 from the Postgres mirror (`graph_isa95`).
**Redis:** copy a `dump_*.rdb` to the data volume and restart, or let it rebuild from PG (cache only).

## 6. Resilience drill (chaos)

```bash
bash scripts/chaos/kill-postgres-drill.sh   # kills PG, asserts HONEST degradation (no fabrication) + recovery on restart
```
Passing means: while PG is down the system raises / returns honest-unavailable (never a fabricated value — Rule 1a),
and recovers cleanly on restart. CI runs backup + restore-verify on every PR (`dr-backup-restore`).

## 7. Honest scope boundary

- **Single-node**: no automatic failover yet. A node loss = a restore (RTO above), not a hot standby. Multi-node HA
  (PG streaming replication / Patroni; Neo4j is Community = no clustering) is a **pilot/cloud** item (Stage 22+).
- **Off-site** is config-only at build time (no paid cloud). The runbook + scripts are ready; the operator wires a real
  bucket at pilot.
- These boundaries are deliberate (Rule 9) and tracked in the risk register, not hidden.
