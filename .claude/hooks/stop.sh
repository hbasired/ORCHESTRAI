#!/usr/bin/env bash
# .claude/hooks/stop.sh
# Stop hook — runs when Claude finishes responding. Warns if the session
# touched code but didn't run audit, or if KB_TASK_LOG wasn't updated.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

WARN=0

if [ -f audits/.session_state ]; then
  if grep -q '^needs-audit=true' audits/.session_state; then
    if ! grep -q '^audit-ran=true' audits/.session_state; then
      echo "[stop hook WARN] This session wrote backend code but scripts/audit-task.sh was not run."
      echo "  → Run: bash scripts/audit-task.sh <stage-number>"
      WARN=1
    fi
  fi

  # Research-protocol guard: if web search was used in this session,
  # research/initial-research.md MUST have been modified in the working tree.
  if grep -q '^web-search-used=true' audits/.session_state; then
    if command -v git >/dev/null 2>&1; then
      if ! git status --porcelain research/initial-research.md 2>/dev/null | grep -q .; then
        echo "[stop hook WARN] WebSearch/WebFetch was used this session but research/initial-research.md has NO working-tree diff."
        echo "  → Per CLAUDE.md §5 research protocol: append a new dated section before closing the session."
        echo "  → See research/initial-research.md §6, §7, §8 for the canonical shape."
        WARN=1
      fi
    fi
  fi
fi

# If we have a current task and it's not the expansion session, check KB_TASK_LOG was updated
if [ -f .git/HEAD ]; then
  # Check if KB_TASK_LOG was touched in working tree
  if git status --porcelain knowledge-base/KB_TASK_LOG.md 2>/dev/null | grep -q .; then
    : # Was touched — fine
  else
    # Was the backend touched but KB_TASK_LOG not? Only relevant if non-trivial changes pending.
    if git status --porcelain backend/ 2>/dev/null | grep -qE '^\s?[MA]'; then
      echo "[stop hook WARN] Backend changes present but knowledge-base/KB_TASK_LOG.md has no diff."
      echo "  → Every code-touching stage must append a KB_TASK_LOG entry at close."
      WARN=1
    fi
  fi
fi

# Audit chain quick verify (Stage 13.5+; skipped if script missing)
if [ -f scripts/verify-audit-chain.py ]; then
  python scripts/verify-audit-chain.py --quick 2>/dev/null || {
    echo "[stop hook WARN] Audit chain quick-verify failed. Run: python scripts/verify-audit-chain.py"
    WARN=1
  }
fi

[ "$WARN" -eq 0 ] && echo "[stop hook] Session clean."
exit 0
