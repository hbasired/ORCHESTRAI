#!/usr/bin/env bash
# .claude/hooks/pre_web_search.sh
# PreToolUse hook (matcher: WebSearch|WebFetch) — marks the session as having
# used web search so the Stop hook can warn if research/initial-research.md
# is not appended before close. Per the research protocol in CLAUDE.md §5.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

mkdir -p audits
state_file="audits/.session_state"
touch "$state_file"

# Idempotent set: only update if not already true
if ! grep -q '^web-search-used=true' "$state_file" 2>/dev/null; then
  echo "web-search-used=true" >> "$state_file"
  echo "web-search-first-at=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$state_file"
fi

# Reminder visible to the agent during the tool call
echo "[research protocol] Web search detected. Before session close, append a new dated section to research/initial-research.md (per CLAUDE.md §5)."
exit 0
