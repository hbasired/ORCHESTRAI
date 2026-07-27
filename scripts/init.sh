#!/usr/bin/env bash
# scripts/init.sh
# Single entrypoint for session initialisation. Called by:
#   - .claude/commands/begin.md (the /begin slash command)
#   - The operator manually (`bash scripts/init.sh`)
#   - The SessionStart hook (already calls load-context.py; this script is the more verbose orchestrator)
#
# Responsibilities:
#   1. Emit the full context bundle via scripts/load-context.py.
#   2. Pre-flight environment checks (python on PATH, git repo healthy, .audit-baseline present, CLAUDE.md present).
#   3. Determine state via the loader and print explicit recommended action.
#   4. Optionally execute a follow-up script when --auto-route is given (e.g., automatically run rectify-task.sh if state is has-open-gaps).
#
# Exit codes:
#   0  — context loaded; state determined; recommendation printed.
#   2  — pre-flight check failed (missing python / not a git repo / CLAUDE.md missing / .audit-baseline missing).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

AUTO_ROUTE=""
QUIET=""
while [ "${#}" -gt 0 ]; do
  case "$1" in
    --auto-route) AUTO_ROUTE=1; shift ;;
    --quiet)      QUIET=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: bash scripts/init.sh [--auto-route] [--quiet]

  --auto-route   After printing the bundle, automatically invoke the
                 recommended follow-up script if the state is unambiguous
                 (e.g., 'has-open-gaps' triggers rectify-task.sh; 'done-needs-next-task'
                 triggers next-task.sh). NEVER triggers anything destructive.

  --quiet        Suppress the context bundle; only print the state + recommendation.
EOF
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

# ----- pre-flight -----

fail=0
if ! command -v python >/dev/null 2>&1; then
  echo "[init] PRE-FLIGHT FAIL: python not on PATH." >&2
  fail=1
fi
if [ ! -d .git ]; then
  echo "[init] PRE-FLIGHT FAIL: not a git repository (no .git directory at $REPO_ROOT)." >&2
  fail=1
fi
if [ ! -f CLAUDE.md ]; then
  echo "[init] PRE-FLIGHT FAIL: CLAUDE.md missing. The project requires this file at repo root." >&2
  fail=1
fi
if [ ! -f .audit-baseline ]; then
  echo "[init] PRE-FLIGHT FAIL: .audit-baseline missing. Run 'bash scripts/audit.sh --baseline' to seed." >&2
  fail=1
fi
if [ ! -f scripts/load-context.py ]; then
  echo "[init] PRE-FLIGHT FAIL: scripts/load-context.py missing." >&2
  fail=1
fi
if [ "$fail" -ne 0 ]; then
  echo "[init] Pre-flight failed. Fix the above and re-run."
  exit 2
fi

# ----- emit bundle -----

if [ -z "$QUIET" ]; then
  python scripts/load-context.py --mode=session-start
fi

# ----- determine state for the orchestrator's own routing -----

STATE=$(python -c "
import sys
sys.path.insert(0, '.claude/hooks/lib')
from context_loader import find_current_task, determine_state
task = find_current_task()
state, _ = determine_state(task)
print(state)
")

STAGE_RAW=$(python -c "
import sys
sys.path.insert(0, '.claude/hooks/lib')
from context_loader import find_current_task, extract_stage_number
task = find_current_task()
print(extract_stage_number(task) if task else '')
")
STAGE_DISPLAY="${STAGE_RAW//_/.}"

echo ""
echo "============================================================"
echo "[init] State: $STATE | Stage: ${STAGE_DISPLAY:-(none)}"
echo "============================================================"

# ----- auto-route (opt-in via flag) -----

if [ -n "$AUTO_ROUTE" ]; then
  case "$STATE" in
    no-task)
      echo "[init] Auto-routing: seeding next stage task doc."
      bash scripts/next-task.sh
      ;;
    has-open-gaps)
      echo "[init] Auto-routing: listing gaps via rectify-task.sh."
      bash scripts/rectify-task.sh "$STAGE_DISPLAY"
      ;;
    done-needs-next-task)
      echo "[init] Auto-routing: seeding next stage task doc."
      bash scripts/next-task.sh
      ;;
    not-started|in-progress|audit-clean-ready-to-close|unknown)
      echo "[init] State '$STATE' requires human-driven decisions; not auto-routing."
      ;;
  esac
fi

exit 0
