#!/usr/bin/env bash
# Stage 21 — Neo4j Community OFFLINE backup (research §31.2/§31.5).
# Community Edition supports offline `neo4j-admin database dump` only (online/differential is Enterprise). We briefly
# stop the running container, run a one-off `neo4j-admin` container that reuses the data volume (`--volumes-from`) to
# dump the `neo4j` (data) and `system` (users/roles) databases, then restart. The ISA-95 graph is also mirrored in
# Postgres (Stage 12), so PG PITR is the primary recovery and this dump is the graph-store backstop.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OUT_DIR="$BACKUP_ROOT/neo4j/${TS}"
mkdir -p "$OUT_DIR"
require_container "$NEO4J_CONTAINER"

WAS_RUNNING=1
log "stopping $NEO4J_CONTAINER for offline dump (Community requires the DB offline)"
docker stop "$NEO4J_CONTAINER" >/dev/null || die "could not stop $NEO4J_CONTAINER"

# G-078: the restart MUST be verified — `docker start` can exit non-zero / the container can crash-loop on some hosts
# (Docker-Desktop NEO4J_AUTH re-init), and silently leaving Neo4j DOWN while reporting OK is dishonest. Retry + poll
# State.Running; only return once it is actually up. Returns 0 if up, 1 if it could not be recovered.
restart_neo4j() {
  [ "$WAS_RUNNING" = 1 ] || return 0
  log "restarting $NEO4J_CONTAINER"
  for _ in $(seq 1 20); do
    docker start "$NEO4J_CONTAINER" >/dev/null 2>&1 || true
    [ "$(docker inspect -f '{{.State.Running}}' "$NEO4J_CONTAINER" 2>/dev/null)" = "true" ] && { log "$NEO4J_CONTAINER is running again"; return 0; }
    sleep 1
  done
  log "ERROR: $NEO4J_CONTAINER did NOT come back up — manual recovery needed: docker start $NEO4J_CONTAINER"
  return 1
}
# Safety-net trap (best-effort) in case the script dies mid-dump.
trap 'restart_neo4j || true' EXIT

# Host mount path must be docker-friendly (Windows: D:\...; Linux: verbatim). MSYS_NO_PATHCONV (set in lib.sh) keeps
# the container-side /backups literal.
HOST_OUT="$(docker_host_path "$(cd "$OUT_DIR" && pwd)")"
for db in neo4j system; do
  log "dumping database '$db'"
  docker run --rm \
    --volumes-from "$NEO4J_CONTAINER" \
    -v "${HOST_OUT}:/backups" \
    "$NEO4J_IMAGE" \
    neo4j-admin database dump "$db" --to-path=/backups --overwrite-destination=true \
    || die "neo4j-admin dump failed for '$db'"
done

RESTART_OK=0; restart_neo4j && RESTART_OK=1; trap - EXIT
COUNT="$(ls -1 "$OUT_DIR"/*.dump 2>/dev/null | wc -l | tr -d ' ')"
[ "$COUNT" -ge 1 ] || die "no .dump artefacts produced"
# Honest reporting: artefacts produced, but if the container did not recover, FAIL the script so backup-all marks
# neo4j FAILED (the operator must restart it) rather than silently reporting OK with Neo4j down (G-078).
[ "$RESTART_OK" = 1 ] || die "dumps produced ($OUT_DIR) BUT $NEO4J_CONTAINER did not restart — recover it manually"
log "neo4j backup OK: $OUT_DIR ($COUNT dumps)"
copy_second_medium "$OUT_DIR"/neo4j.dump 2>/dev/null || true
# retention over timestamped dirs
ls -1dt "$BACKUP_ROOT"/neo4j/*/ 2>/dev/null | tail -n +"$((RETENTION + 1))" | while read -r old; do
  log "retention: removing $old"; rm -rf "$old"
done
# Echo the primary artefact FILE (not the dir) so backup-all can record a real SHA-256 in the manifest (G-078).
echo "$OUT_DIR/neo4j.dump"
