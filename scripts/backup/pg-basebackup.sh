#!/usr/bin/env bash
# Stage 21 — PostgreSQL physical BASE BACKUP for PITR (research §31.1).
# `pg_basebackup -Ft -z` produces a compressed tar base backup — the anchor a point-in-time recovery replays archived
# WAL on top of. Complements the logical `pg_dump` leg (backup-postgres.sh). Free/built-in. Requires the server to
# allow replication connections (default for the local superuser). The continuous WAL-archive leg is enabled per the
# docker-compose PITR comment + dr-runbook §5 (off by default to avoid a full-WAL-disk outage).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OUT_DIR="$BACKUP_ROOT/postgres-base/${TS}"
mkdir -p "$OUT_DIR"
require_container "$PG_CONTAINER"

log "pg_basebackup -Ft -z (compressed tar base backup) -> $OUT_DIR"
# Run inside the container (writes to /tmp), then copy the artefacts out.
docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" sh -c \
  'rm -rf /tmp/_basebackup && mkdir -p /tmp/_basebackup && pg_basebackup -U '"$PG_USER"' -D /tmp/_basebackup -Ft -z -Xs -P' \
  || die "pg_basebackup failed (ensure the role may start a replication connection)"

docker cp "$PG_CONTAINER:/tmp/_basebackup/." "$(docker_host_path "$OUT_DIR")" || die "docker cp base backup out failed"
docker exec "$PG_CONTAINER" rm -rf /tmp/_basebackup

COUNT="$(ls -1 "$OUT_DIR"/*.tar.gz 2>/dev/null | wc -l | tr -d ' ')"
[ "$COUNT" -ge 1 ] || die "no base-backup tar produced"
log "base backup OK: $OUT_DIR ($COUNT tar.gz)"
ls -1dt "$BACKUP_ROOT"/postgres-base/*/ 2>/dev/null | tail -n +"$((RETENTION + 1))" | while read -r old; do
  log "retention: removing $old"; rm -rf "$old"
done
echo "$OUT_DIR"
