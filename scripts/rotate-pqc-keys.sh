#!/usr/bin/env bash
# scripts/rotate-pqc-keys.sh [--mode={hybrid|pq-only|classical-only}] [--key-type={identity|tls|firmware|hmac}] [--dry-run]
# Quarterly PQC key rotation drill. Performs overlap rotation: new keypair
# generated; new key signs alongside old for grace window; audit chain emits
# a rotation marker row signed by both; old key revoked after grace window.
#
# Requires Stage 13.5+ (backend/crypto/key_manager.py present).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

MODE="hybrid"
KEY_TYPE="identity"
DRY_RUN=""
GRACE_HOURS="24"

while [ "${#}" -gt 0 ]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --key-type) KEY_TYPE="$2"; shift 2 ;;
    --grace-hours) GRACE_HOURS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

case "$MODE" in
  hybrid|pq-only|classical-only) ;;
  *) echo "ERROR: --mode must be hybrid|pq-only|classical-only"; exit 2 ;;
esac

case "$KEY_TYPE" in
  identity|tls|firmware|hmac) ;;
  *) echo "ERROR: --key-type must be identity|tls|firmware|hmac"; exit 2 ;;
esac

if [ ! -f backend/crypto/key_manager.py ]; then
  echo "REFUSE: backend/crypto/key_manager.py missing. PQC infrastructure not yet shipped (Stage 13.5+)."
  exit 1
fi

echo "PQC key rotation drill"
echo "  Key type:    $KEY_TYPE"
echo "  Mode:        $MODE"
echo "  Grace hours: $GRACE_HOURS"
echo "  Dry run:     ${DRY_RUN:-no}"
echo ""

PYTHON_CMD="python -m backend.crypto.key_manager rotate"
PYTHON_CMD="$PYTHON_CMD --key-type=$KEY_TYPE --mode=$MODE --grace-hours=$GRACE_HOURS"
[ -n "$DRY_RUN" ] && PYTHON_CMD="$PYTHON_CMD --dry-run"

echo ">>> $PYTHON_CMD"
$PYTHON_CMD || {
  echo "ERROR: key rotation failed. Audit chain unchanged."
  exit 1
}

if [ -z "$DRY_RUN" ]; then
  echo ""
  echo "Verifying audit chain after rotation..."
  python scripts/verify-audit-chain.py || {
    echo "FATAL: audit chain failed verification after rotation. INVESTIGATE IMMEDIATELY."
    echo "  The rotation marker may not have been written correctly. Do not deploy."
    exit 1
  }
  echo "Audit chain OK."

  # Log to KB_TASK_LOG (manual reminder)
  echo ""
  echo "REMINDER: append a KB_TASK_LOG entry for this rotation:"
  echo "  date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "  key-type: $KEY_TYPE  mode: $MODE  grace-hours: $GRACE_HOURS"
fi
