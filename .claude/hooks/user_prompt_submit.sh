#!/usr/bin/env bash
# .claude/hooks/user_prompt_submit.sh
# UserPromptSubmit hook — re-injects current task doc filename + status, and
# detects task-lifecycle keywords to remind the agent which script to run.
# The user prompt is passed via the CLAUDE_USER_PROMPT env var (Claude Code convention).

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

PROMPT="${CLAUDE_USER_PROMPT:-}"

# Find lowest-numbered not-started task doc
CURRENT_TASK=$(ls tasks/STAGE_*.md 2>/dev/null | sort | while read f; do
  status=$(grep -m1 -i '^status:' "$f" 2>/dev/null | awk '{print tolower($2)}')
  if [ "$status" = "not-started" ] || [ "$status" = "in-progress" ]; then
    echo "$f"
    break
  fi
done)

echo "[context] Current task doc: ${CURRENT_TASK:-<none found — run scripts/next-task.sh>}"

# Keyword triggers
case "${PROMPT,,}" in
  *"start task"*|*"new task"*|*"begin stage"*)
    echo "[hint] If starting a new stage: bash scripts/start-task.sh <stage-number> <slug>"
    ;;
  *"audit"*)
    echo "[hint] Per-task audit: bash scripts/audit-task.sh <stage-number>"
    echo "[hint] Repo-wide audit: bash scripts/audit.sh"
    ;;
  *"close task"*|*"finish stage"*|*"complete stage"*)
    echo "[hint] Close ritual: bash scripts/close-task.sh <stage-number> (refuses if gaps open or KB_TASK_LOG missing entry)"
    ;;
  *"cto checkpoint"*|*"cto review"*)
    echo "[hint] CTO checkpoint: bash scripts/cto-review.sh (refuses unless task # is multiple of 10)"
    ;;
  *"rotate"*|*"key rotation"*|*"pqc"*)
    echo "[hint] PQC key rotation drill: bash scripts/rotate-pqc-keys.sh (Stage 13.5+)"
    ;;
esac

exit 0
