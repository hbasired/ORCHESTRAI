#!/usr/bin/env bash
# scripts/independent-audit.sh <stage-number>
#
# Independent, per-stage audit performed by a DIFFERENT agent than the one that
# implemented the stage (operator mandate, 2026-05-31). Two phases:
#   1. Mechanical audit  — scripts/audit-task.sh <stage> (count gate, artefacts).
#   2. Independent review — spawns a FRESH Claude Code subprocess with the
#      `task-auditor` skill, which re-runs the stage's tests, reads the new code
#      adversarially, and writes audits/STAGE_<NN>_independent_review.md.
#
# Why: the builder of a system has an incentive (conscious or not) to pass their
# own audit. A separate agent with fresh context and no authorship has none.
# This is distinct from cto-review.sh (whole-system, every 10 stages).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${#}" -lt 1 ]; then
  echo "Usage: $0 <stage-number>"
  exit 2
fi

STAGE="$1"
STAGE_PADDED="$STAGE"
case "$STAGE" in *.*) STAGE_PADDED="${STAGE/./_}" ;; esac
INTPART="${STAGE_PADDED%%_*}"; RESTPART=""
[[ "$STAGE_PADDED" == *_* ]] && RESTPART="_${STAGE_PADDED#*_}"
[[ "$INTPART" =~ ^[0-9]$ ]] && INTPART="0$INTPART"
STAGE_PADDED="${INTPART}${RESTPART}"

TASK_FILE=$(ls tasks/STAGE_${STAGE_PADDED}_*.md 2>/dev/null | head -1)
OUT="audits/STAGE_${STAGE_PADDED}_independent_review.md"
mkdir -p audits

echo "=== Phase 1: mechanical audit (scripts/audit-task.sh ${STAGE}) ==="
bash scripts/audit-task.sh "$STAGE" || true   # gaps are reported, not fatal here

echo ""
echo "=== Phase 2: INDEPENDENT review by a fresh agent (task-auditor) ==="
if ! command -v claude >/dev/null 2>&1; then
  echo "NOTE: 'claude' CLI not on PATH — cannot auto-spawn the independent auditor."
  echo "  Independence requirement (operator mandate): the audit MUST be run by a DIFFERENT"
  echo "  agent/session than the one that implemented stage ${STAGE_PADDED}."
  echo "  Manual fallback: open a FRESH Claude Code session (or use the Agent tool to spawn a"
  echo "  separate subagent) and have it adopt .claude/skills/task-auditor/SKILL.md, audit"
  echo "  ${TASK_FILE:-the stage task doc}, and write ${OUT}."
  exit 2
fi

# Gather IMPLEMENTATION CONTEXT so the auditor knows exactly what this stage changed.
CHANGED_FILES="(git unavailable)"
if command -v git >/dev/null 2>&1; then
  CHANGED_FILES=$(git status --porcelain 2>/dev/null | awk '{print $NF}' | grep -vE '^audits/' | head -60)
  [ -z "$CHANGED_FILES" ] && CHANGED_FILES="(no working-tree changes detected)"
fi

PROMPT_FILE=$(mktemp)
cat > "$PROMPT_FILE" <<EOF
You are invoked as the task-auditor skill — an INDEPENDENT auditor for stage ${STAGE_PADDED}.
You did NOT build this stage. Read .claude/skills/task-auditor/SKILL.md FIRST and follow it exactly.

Your sole output is ${OUT}.

== IMPLEMENTATION CONTEXT (what this stage changed — read these to ground your audit) ==
Task doc: ${TASK_FILE:-<none>}
Changed/untracked files in the working tree:
${CHANGED_FILES}
Also read the latest entry of knowledge-base/KB_TASK_LOG.md (the stage's Shipped/Learned notes) and the new
ADRs in compliance/decision-logs/ for this stage. Use \`git diff\`/\`git show\` where commits exist.

== YOUR JOB ==
Audit ${TASK_FILE:-the stage task doc}: verify EVERY acceptance criterion against real evidence (re-run the
named tests / scripts/audit.sh / the stage's verification commands yourself), read the changed code
adversarially for theatrical fallbacks / bypassed gates / faked tests, and confirm the audit baseline
discipline. Write the verdict (PASS / PASS-WITH-GAPS / FAIL) with a per-criterion evidence table and
file:line findings.

== DEFERRED GAPS ==
For any gap whose real fix belongs to a LATER stage, record it in audits/OPEN_GAPS_LEDGER.md with a
target_stage (append a row) IN ADDITION to listing it in ${OUT}. Do not invent fixes that belong elsewhere.

You are READ-ONLY except for ${OUT} and (append-only) audits/OPEN_GAPS_LEDGER.md. Do not run any
state-mutating script (close-task.sh, next-task.sh, seed-next-task.sh, audit.sh --baseline).
EOF

echo "Spawning a fresh Claude Code subprocess as the independent auditor..."
echo "Output target: ${OUT}"
claude -p "$(cat "$PROMPT_FILE")" > /tmp/independent_audit_subprocess.log 2>&1 || {
  echo "WARN: 'claude -p' invocation failed (CLI shape may differ). Manual fallback — paste into a fresh session:"
  echo ""
  cat "$PROMPT_FILE"
}
rm -f "$PROMPT_FILE"

if [ -f "$OUT" ]; then
  echo "Independent review written: ${OUT}"
  echo ""
  echo ">>> AUDIT -> FIX HANDOFF: the review is a report, not a fix. Now hand ${OUT} to an"
  echo "    IMPLEMENTER session (e.g. backend-engineer) to FIX every gap it lists, then re-run"
  echo "    this script until the verdict is PASS. Gaps whose fix belongs to a later stage must be"
  echo "    in audits/OPEN_GAPS_LEDGER.md (the auditor appends them; start-task.sh surfaces them later)."
else
  echo "WARN: ${OUT} not written by the subprocess. Inspect /tmp/independent_audit_subprocess.log."
fi
