#!/usr/bin/env bash
# .claude/hooks/post_tool_use_write.sh
# PostToolUse hook (matcher: Write|Edit|MultiEdit) — emits KB-update reminders
# based on the path → KB mapping in .claude/hooks/lib/kb_map.json. Also marks
# the session as needs-audit when backend/ code is touched.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

TARGET="${CLAUDE_TOOL_FILE_PATH:-}"
if [ -z "$TARGET" ] && [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  TARGET=$(echo "$CLAUDE_TOOL_INPUT" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("file_path","") or d.get("path",""))' 2>/dev/null || echo "")
fi

[ -z "$TARGET" ] && exit 0

# Normalize relative path
case "$TARGET" in
  /*|[A-Za-z]:*)
    REL=$(python -c "import os,sys;print(os.path.relpath('$TARGET', '$REPO_ROOT'))" 2>/dev/null || echo "$TARGET")
    ;;
  *) REL="$TARGET" ;;
esac

# Mark needs-audit for backend code changes (outside tests/training)
if [[ "$REL" == backend/* ]] && [[ "$REL" != backend/tests/* ]] && [[ "$REL" != backend/training/* ]]; then
  mkdir -p audits
  echo "needs-audit=true" > audits/.session_state
  echo "last-write=$REL" >> audits/.session_state
fi

# Look up KB reminders via the Python helper
python .claude/hooks/lib/context_loader.py --kb-reminder "$REL" 2>/dev/null || true

# Stronger reminder for safety / crypto / a2a paths
if [[ "$REL" == backend/safety/* ]] || [[ "$REL" == backend/crypto/* ]] || [[ "$REL" == backend/a2a/* ]]; then
  echo "[post_tool_use ATTENTION] $REL touches a high-risk surface."
  echo "  → Add a new ADR in compliance/decision-logs/$(date +%Y-%m-%d)_<slug>.md"
  echo "  → Update compliance/risk-register.md if scope changed"
  echo "  → Verify audit chain still validates: python scripts/verify-audit-chain.py --quick"
fi

exit 0
