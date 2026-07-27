#!/usr/bin/env bash
# Stage 21 — chaos drill (G-004; research §31.4). Kills the Postgres container and asserts the system degrades
# HONESTLY (raises / honest-unavailable — NEVER fabricates a result) while PG is down, then RECOVERS on restart.
# "All chaos tests include automated validation of expected resilience behaviour." Free/local (docker + a tiny probe).
#
#   bash scripts/chaos/kill-postgres-drill.sh
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../backup/lib.sh"
require_container "$PG_CONTAINER"

# A minimal probe: connect to PG and read the audit_chain head. Returns 0 + prints OK on success; non-zero otherwise.
probe() {
  docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
    psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT 'OK:'||count(*) FROM audit_chain;" 2>/dev/null
}

log "=== chaos drill: kill Postgres, assert honest degradation + recovery ==="

# 1) baseline: probe must succeed while healthy
BASE="$(probe || true)"
case "$BASE" in OK:*) log "baseline probe OK ($BASE)";; *) die "baseline probe failed — environment not healthy before the drill";; esac

# Baseline the SECONDARY (app-layer) signal too: only use verify-audit-chain as a degradation assertion if it PASSES
# with PG UP. If it already fails with PG up (e.g. pre-existing invalid-signature rows, G-073-adjacent), it can't prove
# honest-degradation under fault, so we skip that leg and rely on the primary probe (G-079).
VAC="$REPO_ROOT/scripts/verify-audit-chain.py"
VAC_BASELINE_OK=0
if [ -f "$VAC" ]; then
  if DATABASE_URL="postgresql://$PG_USER:$PG_PASSWORD@localhost:5544/$PG_DB" python "$VAC" >/dev/null 2>&1; then
    VAC_BASELINE_OK=1; log "verify-audit-chain passes with PG up — usable as a secondary degradation signal"
  else
    log "NOTE: verify-audit-chain already fails with PG up (chain has unverifiable rows) — skipping it as a chaos signal; the primary probe carries the drill (G-079)"
  fi
fi

# 2) FAULT: kill the container
log "killing $PG_CONTAINER"
docker kill "$PG_CONTAINER" >/dev/null || die "docker kill failed"

ensure_restart() { docker start "$PG_CONTAINER" >/dev/null 2>&1 || true; }
trap ensure_restart EXIT

# 3) assert HONEST degradation: the probe must FAIL (raise/error), NOT return a fabricated value
DOWN="$(probe || true)"
if [ -z "$DOWN" ]; then
  log "degradation HONEST: probe failed cleanly while PG down (no fabricated result)"
else
  die "FABRICATION RISK: probe returned '$DOWN' while PG was killed — a value was produced without the DB"
fi

# Secondary leg (only load-bearing if it passed at baseline, see G-079): the app layer must FAIL (not fabricate) with PG down.
if [ "$VAC_BASELINE_OK" = 1 ]; then
  if DATABASE_URL="postgresql://$PG_USER:$PG_PASSWORD@localhost:5544/$PG_DB" python "$VAC" >/dev/null 2>&1; then
    die "verify-audit-chain.py exited 0 with PG down — must fail-honest, not fabricate"
  else
    log "app layer HONEST: verify-audit-chain.py (which passed at baseline) now fails with PG down"
  fi
fi

# 4) RECOVERY: restart + wait for health, probe must succeed again
log "restarting $PG_CONTAINER"
docker start "$PG_CONTAINER" >/dev/null || die "restart failed"
trap - EXIT
for _ in $(seq 1 30); do docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1 && break; sleep 2; done
REC="$(probe || true)"
case "$REC" in OK:*) log "recovery OK ($REC) — system healthy after restart";; *) die "recovery FAILED — probe still failing after restart";; esac

log "CHAOS DRILL PASSED — honest degradation under fault, clean recovery on restart."
