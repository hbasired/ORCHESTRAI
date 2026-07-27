#!/usr/bin/env bash
# Stage 21 — orchestrate the full stateful-tier backup (research §31). Runs pg + neo4j + redis backups, writes a
# signed-free manifest with SHA-256 checksums (integrity / 3-2-1-1-0 "zero errors"), and reports a single status.
# Postgres is the source of truth (its failure fails the run); neo4j/redis are best-effort backstops (warn, don't fail).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
HERE="$(dirname "${BASH_SOURCE[0]}")"

MANIFEST_DIR="$BACKUP_ROOT/manifests"
mkdir -p "$MANIFEST_DIR"
MANIFEST="$MANIFEST_DIR/backup_${TS}.manifest"
: > "$MANIFEST"

rc=0
record() {  # name  artefact-path  required(0/1)
  local name="$1" path="$2" required="$3"
  if [ -n "$path" ] && [ -e "$path" ]; then
    local sum; sum="$(sha256sum "$path" 2>/dev/null | awk '{print $1}')"
    printf '%s\t%s\t%s\n' "$name" "$path" "$sum" >> "$MANIFEST"
    log "$name -> OK"
  else
    printf '%s\t%s\tFAILED\n' "$name" "${path:-<none>}" >> "$MANIFEST"
    log "$name -> FAILED"
    [ "$required" = 1 ] && rc=1
  fi
}

log "=== backup-all $TS ==="
PG_OUT="$(bash "$HERE/backup-postgres.sh" 2>>"$MANIFEST_DIR/backup_${TS}.log" | tail -1)" || PG_OUT=""
record postgres "$PG_OUT" 1
NEO_OUT="$(bash "$HERE/backup-neo4j.sh" 2>>"$MANIFEST_DIR/backup_${TS}.log" | tail -1)" || NEO_OUT=""
record neo4j "$NEO_OUT" 0
REDIS_OUT="$(bash "$HERE/backup-redis.sh" 2>>"$MANIFEST_DIR/backup_${TS}.log" | tail -1)" || REDIS_OUT=""
record redis "$REDIS_OUT" 0

copy_second_medium "$MANIFEST"
log "manifest: $MANIFEST"
[ -n "$OFFSITE_RCLONE_REMOTE" ] && log "off-site target configured: $OFFSITE_RCLONE_REMOTE (run rclone copy out-of-band; not exercised at build time — Rule 9)"
prune_retention "$MANIFEST_DIR" "backup_*.manifest"

if [ "$rc" = 0 ]; then log "=== backup-all OK ==="; else log "=== backup-all FAILED (required store missing) ==="; fi
exit "$rc"
