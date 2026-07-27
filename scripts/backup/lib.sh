#!/usr/bin/env bash
# Stage 21 — shared backup/restore helpers (free/OSS/local; research §31). Sourced by the backup/restore/chaos scripts.
# All config via env with the project's docker-compose defaults (CLAUDE.md / reference_docker_infra_ports).
set -uo pipefail

# On Windows Git-Bash (MSYS), absolute args like `/tmp/x` or `/backups` passed to docker get rewritten to Windows
# paths (e.g. C:/.../tmp/x). Disable that so CONTAINER-internal paths reach docker verbatim. No-op on Linux/CI.
export MSYS_NO_PATHCONV=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Convert a host path to a form `docker -v` accepts on the current OS (Windows needs C:\... via cygpath; Linux verbatim).
docker_host_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}

# --- containers (docker-compose container_name) ---
PG_CONTAINER="${PG_CONTAINER:-ai-agent-postgres}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-ai-agent-neo4j}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ai-agent-redis}"
NEO4J_IMAGE="${NEO4J_IMAGE:-neo4j:5.15-community}"

# --- credentials (match docker/.env / reference_docker_infra_ports) ---
PG_USER="${POSTGRES_USER:-aiagent}"
PG_PASSWORD="${POSTGRES_PASSWORD:-devpass2026}"
PG_DB="${POSTGRES_DB:-manufacturing}"

# --- 3-2-1 backup locations (primary on-disk + a second on-disk medium; off-site is config-only, Rule 9) ---
BACKUP_ROOT="${BACKUP_ROOT:-$REPO_ROOT/backups}"
BACKUP_ROOT_2="${BACKUP_ROOT_2:-}"                 # second medium (e.g. an external mount); copied to if set
OFFSITE_RCLONE_REMOTE="${OFFSITE_RCLONE_REMOTE:-}" # documented off-site target (NOT exercised at build time)
RETENTION="${BACKUP_RETENTION:-7}"                 # keep the most recent N artefacts per store

TS="$(date -u +%Y%m%dT%H%M%SZ)"

log()  { printf '[backup %s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die()  { printf '[backup ERROR] %s\n' "$*" >&2; exit 1; }

require_container() {
  docker inspect -f '{{.State.Running}}' "$1" >/dev/null 2>&1 \
    || die "container '$1' not found/running (start it: docker start $1)"
}

# Keep only the most recent $RETENTION files matching a glob in a dir.
prune_retention() {
  local dir="$1" pattern="$2"
  ls -1t "$dir"/$pattern 2>/dev/null | tail -n +"$((RETENTION + 1))" | while read -r old; do
    log "retention: removing $old"; rm -f "$old"
  done
}

# 3-2-1 second medium: copy an artefact to BACKUP_ROOT_2 if configured.
copy_second_medium() {
  local f="$1"
  [ -n "$BACKUP_ROOT_2" ] || return 0
  mkdir -p "$BACKUP_ROOT_2"
  cp -f "$f" "$BACKUP_ROOT_2/" && log "copied to second medium: $BACKUP_ROOT_2/$(basename "$f")"
}
