#!/usr/bin/env bash
# Stage 21 — PostgreSQL backup (free/built-in; research §31.1/§31.5).
# Produces a portable `pg_dump -Fc` custom-format artefact (compressed; supports `pg_restore --list` integrity check +
# parallel restore) and verifies the archive is readable before declaring success. PITR (base backup + WAL archiving)
# is configured in docker-compose (archive_command/archive_timeout) — this script is the logical-dump leg.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OUT_DIR="$BACKUP_ROOT/postgres"
mkdir -p "$OUT_DIR"
require_container "$PG_CONTAINER"

DUMP="$OUT_DIR/${PG_DB}_${TS}.dump"
log "pg_dump -Fc $PG_DB -> $DUMP"
# -Fc custom format to stdout (binary) -> host file. PGPASSWORD passed into the container env for this exec only.
docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
  pg_dump -Fc -U "$PG_USER" "$PG_DB" > "$DUMP" || die "pg_dump failed"

[ -s "$DUMP" ] || die "dump is empty"

# Integrity: pg_restore --list must read the archive structure (exit 0). A custom-format (-Fc) archive is NOT readable
# from a pipe (pg_restore needs to seek) — copy it into the container and list the real file.
docker cp "$(docker_host_path "$DUMP")" "$PG_CONTAINER:/tmp/_chk.dump" >/dev/null || die "docker cp for integrity check failed"
if docker exec "$PG_CONTAINER" pg_restore --list /tmp/_chk.dump >/dev/null 2>&1; then
  log "archive integrity OK (pg_restore --list)"
  docker exec "$PG_CONTAINER" rm -f /tmp/_chk.dump
else
  docker exec "$PG_CONTAINER" rm -f /tmp/_chk.dump
  die "archive integrity check failed (pg_restore --list non-zero) — corrupt dump"
fi

SIZE="$(wc -c < "$DUMP" | tr -d ' ')"
log "postgres backup OK: $DUMP (${SIZE} bytes)"
copy_second_medium "$DUMP"
prune_retention "$OUT_DIR" "${PG_DB}_*.dump"
echo "$DUMP"
