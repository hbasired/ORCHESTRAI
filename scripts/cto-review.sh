#!/usr/bin/env bash
# scripts/cto-review.sh
# Fires the CTO checkpoint: refuses unless the last-closed stage is a multiple
# of 10 (or --force). Spawns a fresh Claude Code subprocess with the
# cto-reviewer skill. Writes audits/CTO_<N>_review.md.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FORCE=""
if [ "${1:-}" = "--force" ]; then
  FORCE=1
  shift
fi

# Determine the last-closed stage number
LAST_DONE=$(grep -lE '^status:\s*done' tasks/STAGE_*.md 2>/dev/null | sort | tail -1)
LAST_NUM=""
if [ -n "$LAST_DONE" ]; then
  LAST_NUM=$(basename "$LAST_DONE" .md | sed -E 's/^STAGE_([0-9]+).*/\1/')
fi

if [ -z "$FORCE" ]; then
  if [ -z "$LAST_NUM" ]; then
    echo "REFUSE: no closed stages found. Use --force to override."
    exit 1
  fi
  INT=$(( 10#$LAST_NUM ))
  if [ $((INT % 10)) -ne 0 ]; then
    echo "REFUSE: last-closed stage is $INT, not a multiple of 10. CTO checkpoints fire after stages 10/20/30/..."
    echo "  Use --force to override."
    exit 1
  fi
fi

# Determine checkpoint number
EXISTING_CTO=$(ls audits/CTO_*_review.md 2>/dev/null | wc -l | tr -d ' ')
N=$((EXISTING_CTO + 1))
OUT="audits/CTO_${N}_review.md"

mkdir -p audits
if [ -e "$OUT" ]; then
  echo "WARN: $OUT already exists. Append checkpoint number or remove the file."
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "REFUSE: 'claude' CLI not on PATH. Install Claude Code, then re-run."
  echo "  This script spawns a fresh Claude Code subprocess with the cto-reviewer skill."
  echo "  Manual fallback: open a fresh Claude Code session in this repo, invoke the"
  echo "    'cto-reviewer' skill, and follow .claude/skills/cto-reviewer/SKILL.md."
  echo "  Then ensure the session writes $OUT (and audits/CTO_${N}_remediation_map.json)."
  exit 2
fi

PROMPT_FILE=$(mktemp)
cat > "$PROMPT_FILE" <<EOF
You are invoked as the cto-reviewer skill for CTO Checkpoint #${N}.

Read .claude/skills/cto-reviewer/SKILL.md FIRST. Your sole output is $OUT.

Mandatory reads (per SKILL.md):
- CLAUDE.md
- PRD-ai-embodied-agent-v2.md
- The entire knowledge-base/ directory
- The last 10 task docs (any status)
- The last 10 audits/STAGE_*_audit.md files
- All compliance/decision-logs/*.md since the previous CTO checkpoint
- .audit-baseline
- Full compliance/risk-register.md
- audits/CTO_$((N-1))_review.md if it exists
- audits/CTO_$((N-1))_remediation_map.json if it exists

Follow audits/CTO_TEMPLATE_review.md for the output shape.

Also produce audits/CTO_${N}_remediation_map.json — a JSON object mapping each future-task remediation to a target stage number, e.g.:
  {"remediations":[{"description":"...","target_stage":"15"}, ...]}

You are READ-ONLY. Do not edit any other file. Do not run any state-mutating script.
EOF

echo "Spawning Claude Code subprocess for CTO Checkpoint #${N}..."
echo "Output target: $OUT"
echo ""

claude -p "$(cat "$PROMPT_FILE")" > /tmp/cto_subprocess.log 2>&1 || {
  echo "WARN: 'claude -p' invocation failed (CLI shape may differ in your version). Fallback:"
  echo "  Open a fresh Claude Code interactive session in this repo and paste:"
  echo ""
  cat "$PROMPT_FILE"
}
rm -f "$PROMPT_FILE"

if [ -f "$OUT" ]; then
  echo "CTO review written: $OUT"

  MAP_FILE="audits/CTO_${N}_remediation_map.json"
  if [ -f "$MAP_FILE" ] && [ -f scripts/generate-remediation-tasks.sh ]; then
    bash scripts/generate-remediation-tasks.sh "$MAP_FILE"
  fi
else
  echo "WARN: $OUT not written by subprocess. Inspect /tmp/cto_subprocess.log."
fi
