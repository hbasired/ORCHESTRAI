#!/usr/bin/env bash
# .claude/hooks/session_start.sh
# SessionStart hook — emits the project context bundle to Claude's stdin context.
# Wired via .claude/settings.json (see .claude/hooks/settings.json.patch.md).

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

python scripts/load-context.py --mode=session-start 2>/dev/null || {
  echo "[session_start hook] WARN: scripts/load-context.py failed or missing. Read CLAUDE.md manually."
  echo "[session_start hook] Suggested first reads: knowledge-base/KB_TASK_LOG.md (top entry), tasks/STAGE_02_simpy_simulator.md, .audit-baseline."
  exit 0
}
