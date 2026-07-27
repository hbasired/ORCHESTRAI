#!/usr/bin/env bash
# Stage 21 — Redis snapshot backup (research §31.3).
# Redis is a CACHE / pubsub here (NOT a source of truth — rebuildable from Postgres on total loss), so an RDB snapshot
# is sufficient. BGSAVE forks a point-in-time dump.rdb; we wait for it to finish, then copy it out with `docker cp`.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OUT_DIR="$BACKUP_ROOT/redis"
mkdir -p "$OUT_DIR"
require_container "$REDIS_CONTAINER"

LAST_BEFORE="$(docker exec "$REDIS_CONTAINER" redis-cli LASTSAVE 2>/dev/null | tr -d '\r')"
log "BGSAVE on $REDIS_CONTAINER (last save: $LAST_BEFORE)"
docker exec "$REDIS_CONTAINER" redis-cli BGSAVE >/dev/null || die "BGSAVE failed"

# Wait until LASTSAVE advances (BGSAVE complete), bounded.
for _ in $(seq 1 30); do
  NOW="$(docker exec "$REDIS_CONTAINER" redis-cli LASTSAVE 2>/dev/null | tr -d '\r')"
  [ "$NOW" != "$LAST_BEFORE" ] && break
  sleep 1
done

DST="$OUT_DIR/dump_${TS}.rdb"
docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$(docker_host_path "$DST")" 2>/dev/null || die "docker cp dump.rdb failed"
[ -s "$DST" ] || die "redis rdb is empty"
log "redis backup OK: $DST ($(wc -c < "$DST" | tr -d ' ') bytes)"
copy_second_medium "$DST"
prune_retention "$OUT_DIR" "dump_*.rdb"
echo "$DST"
