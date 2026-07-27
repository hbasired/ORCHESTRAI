#!/usr/bin/env bash
# Stage 21 — tested restore + verification (the BINDING DR deliverable; research §31.1/§31.5).
# "Never trust an untested backup." Restores the latest (or given) pg_dump into a SCRATCH database and ASSERTS that
# every public-table row count AND the audit_chain head (seq + hash) match the live source. Exits nonzero on any
# mismatch or restore error. Drops the scratch DB on the way out. Free/built-in (pg_restore/psql via docker exec).
#
#   bash scripts/restore/restore-verify.sh [path/to/backup.dump]
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../backup/lib.sh"

DUMP="${1:-$(ls -1t "$BACKUP_ROOT/postgres/${PG_DB}_"*.dump 2>/dev/null | head -1)}"
[ -n "$DUMP" ] && [ -s "$DUMP" ] || die "no backup dump found (run scripts/backup/backup-postgres.sh first, or pass a path)"
require_container "$PG_CONTAINER"
log "verifying restore of: $DUMP"

SCRATCH="${PG_DB}_verify_${TS}"
PSQL() { docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" psql -U "$PG_USER" -tA "$@"; }

cleanup() { PSQL -d "$PG_DB" -c "DROP DATABASE IF EXISTS \"$SCRATCH\";" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# 1) copy the dump into the container (custom-format -Fc must be a seekable file, not a pipe) + integrity check
docker cp "$(docker_host_path "$DUMP")" "$PG_CONTAINER:/tmp/_verify.dump" || die "docker cp dump into container failed"
docker exec "$PG_CONTAINER" pg_restore --list /tmp/_verify.dump >/dev/null 2>&1 \
  || { docker exec "$PG_CONTAINER" rm -f /tmp/_verify.dump; die "pg_restore --list failed — corrupt archive"; }

# 2) restore into a fresh scratch DB
PSQL -d "$PG_DB" -c "DROP DATABASE IF EXISTS \"$SCRATCH\";" >/dev/null
PSQL -d "$PG_DB" -c "CREATE DATABASE \"$SCRATCH\";" >/dev/null || die "createdb scratch failed"
log "restoring into scratch DB '$SCRATCH'"
# pg_restore returns non-zero on hard errors; --exit-on-error to be strict. (No --clean: target is empty.)
docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
  pg_restore -U "$PG_USER" -d "$SCRATCH" --no-owner --exit-on-error /tmp/_verify.dump \
  || { docker exec "$PG_CONTAINER" rm -f /tmp/_verify.dump; die "pg_restore into scratch failed"; }
docker exec "$PG_CONTAINER" rm -f /tmp/_verify.dump

# 3) per-table row-count parity (source vs scratch) over the public schema
COUNT_SQL="SELECT string_agg(t||'='||(xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I',s,t),false,true,'')))[1]::text, ',' ORDER BY t) FROM (SELECT schemaname s, tablename t FROM pg_tables WHERE schemaname='public') q;"
SRC_COUNTS="$(PSQL -d "$PG_DB" -c "$COUNT_SQL")"
DST_COUNTS="$(PSQL -d "$SCRATCH" -c "$COUNT_SQL")"
if [ "$SRC_COUNTS" = "$DST_COUNTS" ]; then
  log "row-count parity OK ($(echo "$SRC_COUNTS" | tr ',' '\n' | wc -l | tr -d ' ') public tables)"
else
  log "SOURCE : $SRC_COUNTS"
  log "RESTORED: $DST_COUNTS"
  die "row-count MISMATCH between source and restored scratch DB"
fi

# 4) audit_chain head parity (the tamper-evident integrity anchor), if the table exists
HEAD_SQL="SELECT coalesce((SELECT seq||':'||substr(hash,1,16) FROM audit_chain ORDER BY seq DESC LIMIT 1),'<none>');"
SRC_HEAD="$(PSQL -d "$PG_DB" -c "$HEAD_SQL" 2>/dev/null || echo '<no-table>')"
DST_HEAD="$(PSQL -d "$SCRATCH" -c "$HEAD_SQL" 2>/dev/null || echo '<no-table>')"
if [ "$SRC_HEAD" = "$DST_HEAD" ]; then
  log "audit_chain head parity OK (head=$SRC_HEAD)"
else
  die "audit_chain head MISMATCH: source=$SRC_HEAD restored=$DST_HEAD"
fi

log "RESTORE-VERIFY PASSED — backup is restorable and faithful."
