#!/usr/bin/env bash
# scripts/close-task.sh <stage-number> [--no-baseline-drop "justification"]
# Refuses if gaps open or KB_TASK_LOG entry missing.
# Signs new ADRs with ML-DSA-65 (Stage 13.5+).
# Rewrites .audit-baseline.
# Calls next-task.sh to seed the next stage.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${#}" -lt 1 ]; then
  echo "Usage: $0 <stage-number> [--no-baseline-drop \"reason\"]"
  exit 2
fi

STAGE="$1"; shift
NO_BASELINE_DROP=""
NO_DROP_REASON=""
while [ "${#}" -gt 0 ]; do
  case "$1" in
    --no-baseline-drop)
      NO_BASELINE_DROP=1
      # Defensive: `shift 2` with only 1 remaining arg FAILS silently under `set -uo pipefail` (no -e),
      # leaving $1 unchanged -> the while-loop spins forever. Shift by how many args actually remain.
      if [ "${#}" -ge 2 ]; then
        NO_DROP_REASON="$2"; shift 2
      else
        NO_DROP_REASON=""; shift 1
      fi
      ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

STAGE_PADDED="$STAGE"
case "$STAGE" in *.*) STAGE_PADDED="${STAGE/./_}" ;; esac
INTPART="${STAGE_PADDED%%_*}"; RESTPART=""
[[ "$STAGE_PADDED" == *_* ]] && RESTPART="_${STAGE_PADDED#*_}"
[[ "$INTPART" =~ ^[0-9]$ ]] && INTPART="0$INTPART"
STAGE_PADDED="${INTPART}${RESTPART}"

AUDIT_FILE="audits/STAGE_${STAGE_PADDED}_audit.md"
# Match the WHOLE-stage doc, not a half-stage sibling (STAGE_NN_5_*) that string-sorts
# earlier ('5' < a letter slug). If this stage IS a half-stage, the plain glob is correct.
if [[ "$STAGE_PADDED" == *_* ]]; then
  TASK_FILE=$(ls tasks/STAGE_${STAGE_PADDED}_*.md 2>/dev/null | head -1)
else
  TASK_FILE=$(ls tasks/STAGE_${STAGE_PADDED}_[!0-9]*.md 2>/dev/null | head -1)
fi

# 1. Refuse if audit not run
if [ ! -f "$AUDIT_FILE" ]; then
  echo "REFUSE: $AUDIT_FILE missing. Run scripts/audit-task.sh $STAGE first."
  exit 1
fi

# 2. Refuse if open gaps. Count "- [ ] ..." lines except the auto-generated
# placeholder from tasks/AUDIT_TEMPLATE.md (which contains "(auto-generated").
# G-048: `grep -c` already prints a count (0 on no-match), so `|| echo 0` appended a SECOND "0" line on
# exit-1 → "0\n0" → "syntax error in expression". Take the first line, strip to digits, default 0, base-10.
OPEN_GAPS=$(grep -cE '^- \[ \] ' "$AUDIT_FILE" 2>/dev/null | head -1 | tr -dc '0-9')
AUTO_PLACEHOLDER=$(grep -cE '^- \[ \] \(auto-generated' "$AUDIT_FILE" 2>/dev/null | head -1 | tr -dc '0-9')
OPEN_GAPS=$(( 10#${OPEN_GAPS:-0} - 10#${AUTO_PLACEHOLDER:-0} ))
if [ "$OPEN_GAPS" -gt 0 ]; then
  echo "REFUSE: $OPEN_GAPS open gaps in $AUDIT_FILE. Run scripts/rectify-task.sh $STAGE."
  exit 1
fi

# 3. Refuse if KB_TASK_LOG has no working-tree diff (or no new entry)
if command -v git >/dev/null 2>&1; then
  if ! git status --porcelain knowledge-base/KB_TASK_LOG.md 2>/dev/null | grep -q .; then
    if [ -z "$NO_BASELINE_DROP" ]; then
      echo "REFUSE: knowledge-base/KB_TASK_LOG.md has no working-tree change."
      echo "  Append a new entry for stage ${STAGE_PADDED} before closing."
      echo "  (For protocol/governance-only stages with no code, pass --no-baseline-drop \"reason\".)"
      exit 1
    fi
  fi
fi

# 4. Sign any new ADRs with ML-DSA-65 (Stage 13.5+, if backend/crypto exists)
if [ -f scripts/sign-decision-log.py ]; then
  NEW_ADRS=$(git status --porcelain compliance/decision-logs/ 2>/dev/null | grep '^?? ' | awk '{print $NF}' || true)
  for adr in $NEW_ADRS; do
    if [[ "$adr" == *.md ]]; then
      echo "Signing $adr ..."
      python scripts/sign-decision-log.py "$adr" || {
        echo "WARN: signing $adr failed. Continuing (sig will be backfilled when crypto is wired)."
      }
    fi
  done
fi

# 5. Rewrite .audit-baseline
NEW_TOTAL=$(bash scripts/audit.sh 2>&1 | grep -E '^\s*TOTAL' | awk '{print $2}' | head -1)
OLD_BASELINE=$(cat .audit-baseline 2>/dev/null || echo 0)
if [ -n "$NEW_TOTAL" ] && [ "$NEW_TOTAL" -gt "$OLD_BASELINE" ] && [ -z "$NO_BASELINE_DROP" ]; then
  echo "REFUSE: audit total ($NEW_TOTAL) is greater than baseline ($OLD_BASELINE). Fix the regression."
  exit 1
fi
if [ -n "$NEW_TOTAL" ] && [ "$NEW_TOTAL" -eq "$OLD_BASELINE" ] && [ -z "$NO_BASELINE_DROP" ]; then
  echo "WARN: audit total flat at $NEW_TOTAL. If this is intentional, re-run with --no-baseline-drop \"reason\"."
  exit 1
fi

export CLAUDE_HOOK_AUDIT_BASELINE_ALLOWED=1
bash scripts/audit.sh --baseline
unset CLAUDE_HOOK_AUDIT_BASELINE_ALLOWED

# 6. Update task doc status -> done.
# Handles BOTH common status formats:
#   - YAML frontmatter:  `status: not-started`
#   - Body bold:         `**Status**: not-started`
if [ -n "$TASK_FILE" ]; then
  # Plain YAML frontmatter form.
  sed -i.bak -E 's/^(status[[:space:]]*:[[:space:]]*)(not-started|in-progress|blocked)\b/\1done/I' "$TASK_FILE"
  # Bold-markdown body form (e.g. "**Status**: not-started").
  sed -i.bak -E 's/^(\*\*[Ss]tatus\*\*[[:space:]]*:[[:space:]]*)(not-started|in-progress|blocked)\b/\1done/' "$TASK_FILE"
  rm -f "$TASK_FILE.bak"
fi

# 7. Mark session state clean
mkdir -p audits
echo "needs-audit=false" > audits/.session_state
echo "last-close-stage=${STAGE_PADDED}" >> audits/.session_state
echo "last-close-at=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> audits/.session_state

echo ""
echo "Stage ${STAGE_PADDED} closed."
echo ""

# 8. Ensure the next task doc exists (SAFETY NET).
# As of the 2026-05-31 lifecycle fix, the next task doc is normally seeded
# EARLIER — at the end of the previous task, BEFORE KB/.md updates — via
# scripts/seed-next-task.sh (see CLAUDE.md §5). next-task.sh is idempotent:
# if that doc already exists it no-ops and reports it (never clobbers). This
# call is the fallback for when the operator skipped the explicit seed step.
# Pass --from so next-task.sh computes the successor of the JUST-CLOSED stage,
# not "highest existing task doc" (which breaks under the v2 expansion that
# pre-seeded future stage templates).
if [ -f scripts/next-task.sh ]; then
  echo "Ensuring next task doc exists (idempotent; normally pre-seeded by seed-next-task.sh):"
  bash scripts/next-task.sh --from "${STAGE_PADDED}"
fi

# 9. CTO checkpoint reminder if at boundary.
# G-048: force base-10 — a zero-padded INTPART ("08"/"09") octal-parses to "value too great for base" and
# leaves NEXT_NUM unset (→ "unbound variable" under set -u). `10#` makes it decimal regardless of padding.
NEXT_NUM=$(( 10#${INTPART:-0} + 1 ))
if [ $((NEXT_NUM % 10)) -eq 0 ] || [ "${INTPART}" = "10" ] || [ "${INTPART}" = "20" ] || [ "${INTPART}" = "30" ]; then
  echo ""
  echo "=== CTO CHECKPOINT DUE ==="
  echo "Stage ${INTPART} was a 10-task boundary. Before starting the next stage:"
  echo "  bash scripts/cto-review.sh"
fi
