#!/usr/bin/env bash
# scripts/seed-next-task.sh <stage-number> [--quiet]
#
# Seeds the NEXT stage's task doc at the END of the CURRENT stage's work,
# BEFORE the operator updates KB files / KB_TASK_LOG / other .md files.
#
# WHY THIS EXISTS (lifecycle ordering fix, 2026-05-31):
#   The next task document should be born at the final step of the previous
#   task, *before* the KB/.md updates — so the operator is never confused
#   about whether the next task doc exists while writing the KB entries.
#   Previously the only generation point was the very last line of
#   close-task.sh (after KB_TASK_LOG validation, baseline rewrite, status
#   flip). This script moves generation earlier and makes the moment explicit.
#
# NEW lifecycle order (see CLAUDE.md §5):
#   implement -> audit-task -> rectify-task (zero gaps)
#     -> seed-next-task.sh <stage>      <-- THIS STEP (next doc created here)
#     -> update KB files + KB_TASK_LOG + other .md
#     -> close-task.sh <stage>          (next-task call inside is now a no-op)
#
# This is a thin, guarded wrapper around scripts/next-task.sh --from <stage>.
# next-task.sh is already idempotent: if the next-slot doc exists it no-ops
# and reports it (never clobbers). This wrapper adds a hand-off pre-check so
# the seeded doc inherits a useful Pre-requisites block.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${#}" -lt 1 ]; then
  echo "Usage: $0 <stage-number> [--quiet]"
  echo "  Run this AFTER rectify (zero gaps) and AFTER authoring the current"
  echo "  stage's '## Hand-off' section, but BEFORE updating KB files."
  exit 2
fi

STAGE="$1"; shift
QUIET=""
while [ "${#}" -gt 0 ]; do
  case "$1" in
    --quiet) QUIET=1; shift ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

# Canonicalise stage number to the zero-padded filename form (3 -> 03, 3.5 -> 03_5).
STAGE_PADDED="$STAGE"
case "$STAGE" in *.*) STAGE_PADDED="${STAGE/./_}" ;; esac
INTPART="${STAGE_PADDED%%_*}"; RESTPART=""
[[ "$STAGE_PADDED" == *_* ]] && RESTPART="_${STAGE_PADDED#*_}"
[[ "$INTPART" =~ ^[0-9]$ ]] && INTPART="0$INTPART"
STAGE_PADDED="${INTPART}${RESTPART}"

TASK_FILE=$(ls tasks/STAGE_${STAGE_PADDED}_*.md 2>/dev/null | head -1)
if [ -z "$TASK_FILE" ]; then
  echo "REFUSE: no task doc found for stage ${STAGE_PADDED} (tasks/STAGE_${STAGE_PADDED}_*.md)."
  echo "  Seed-next-task is run from the CURRENT stage; pass the stage you are closing."
  exit 1
fi

# Hand-off pre-check: next-task.sh pulls the current stage's '## Hand-off'
# section into the seeded doc's Pre-requisites. Warn (don't block) if absent.
if ! grep -qE '^## *Hand-?off' "$TASK_FILE"; then
  echo "WARN: $TASK_FILE has no '## Hand-off' section."
  echo "  The next task doc will be seeded WITHOUT a pre-filled Pre-requisites block."
  echo "  Recommended: author the '## Hand-off' section first, then re-run."
fi

[ -n "$QUIET" ] || echo "seed-next-task: seeding the successor of stage ${STAGE_PADDED} (before KB/.md updates)..."

# Delegate to the idempotent generator (no-op if the next slot already exists).
if [ -f scripts/next-task.sh ]; then
  bash scripts/next-task.sh --from "${STAGE_PADDED}" ${QUIET:+--quiet}
else
  echo "ERROR: scripts/next-task.sh missing."
  exit 2
fi

[ -n "$QUIET" ] || {
  echo ""
  echo "seed-next-task: done. NOW update KB files + KB_TASK_LOG + other .md, THEN run:"
  echo "  bash scripts/close-task.sh ${STAGE}"
}
