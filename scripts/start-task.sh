#!/usr/bin/env bash
# scripts/start-task.sh <stage-number> <slug>
#
# Production-grade task bootstrap:
#   - Validates stage-number format (NN or N.5 / NN_5).
#   - Validates slug format (snake_case, lowercase, no spaces).
#   - Refuses if target file exists.
#   - Refuses if a previous numbered stage is not closed (no skipping).
#   - Pre-populates suggested role from path/keyword heuristics.
#   - Pre-populates KB files from the suggested role's SKILL.md "Mandatory reads".
#   - Pre-populates Pre-requisites from the previous stage's "Hand-off" block.
#   - Pre-populates Acceptance criteria from CTO remediation map entries targeting this stage.
#   - Emits the full context bundle.
#   - Prints explicit next steps.
#
# Example: bash scripts/start-task.sh 11 langgraph_runtime
# Example: bash scripts/start-task.sh 3.5 cto_checkpoint_1

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${#}" -lt 2 ]; then
  echo "Usage: $0 <stage-number> <slug>"
  echo "  <stage-number>  e.g. 11, 3.5, 11_5 (half-stages allowed)"
  echo "  <slug>          snake_case description, e.g. langgraph_runtime"
  exit 2
fi

STAGE_RAW="$1"
SLUG="$2"

# ----- normalize and validate stage number -----

# Accept formats: NN, N.M, NN_M (treat N.M and NN_M as the same)
STAGE_PADDED="${STAGE_RAW//./_}"
INT_PART="${STAGE_PADDED%%_*}"
REST_PART=""
if [[ "$STAGE_PADDED" == *_* ]]; then
  REST_PART="_${STAGE_PADDED#*_}"
fi
# Pad single-digit to width 2
if [[ "$INT_PART" =~ ^[0-9]$ ]]; then
  INT_PART="0$INT_PART"
elif [[ ! "$INT_PART" =~ ^[0-9]{2,3}$ ]]; then
  echo "[start-task] REFUSE: stage number '$STAGE_RAW' invalid. Must be N, NN, N.M, or NN_M."
  exit 2
fi
STAGE_PADDED="${INT_PART}${REST_PART}"
STAGE_DISPLAY="${STAGE_PADDED//_/.}"

# ----- validate slug -----

if [[ ! "$SLUG" =~ ^[a-z][a-z0-9_]*$ ]]; then
  echo "[start-task] REFUSE: slug '$SLUG' must be lowercase snake_case (start with letter; only a-z, 0-9, _)."
  exit 2
fi

TASK_FILE="tasks/STAGE_${STAGE_PADDED}_${SLUG}.md"

if [ -e "$TASK_FILE" ]; then
  echo "[start-task] REFUSE: $TASK_FILE already exists. Use a different slug or edit the existing file directly."
  exit 1
fi

# ----- sequencing check: predecessor INTEGER stage must be done (or absent) -----
# Half-stages (NN_M) are NOT required to be done — they're intermediate gates / future plans.
# The rule: for stage N (whole), predecessor is N-1. For stage N.M (half), predecessor is N.

PREV_INT_DECIMAL=$((10#$INT_PART))
if [ -z "$REST_PART" ]; then
  PRED_INT=$((PREV_INT_DECIMAL - 1))
else
  PRED_INT=$PREV_INT_DECIMAL
fi
if [ "$PRED_INT" -ge 1 ]; then
  PRED_PAD=$(printf "%02d" "$PRED_INT")
  # Match STAGE_<NN>_<anything-not-starting-with-digit-underscore>.md  (i.e., not the half-stage NN_M_*)
  PRED_FILE=$(ls tasks/STAGE_${PRED_PAD}_*.md 2>/dev/null | grep -vE "^tasks/STAGE_${PRED_PAD}_[0-9]_" | head -1)
  if [ -n "$PRED_FILE" ]; then
    PRED_STATUS=$(python -c "
import sys
sys.path.insert(0, '.claude/hooks/lib')
from context_loader import extract_status
print(extract_status(open(r'''$PRED_FILE''', encoding='utf-8', errors='ignore').read()))
")
    if [ "$PRED_STATUS" != "done" ]; then
      echo "[start-task] WARN: predecessor integer stage '$PRED_FILE' has status='$PRED_STATUS' (expected 'done')."
      if [ "${3:-}" != "--force-skip" ]; then
        echo "[start-task] REFUSE: close the predecessor stage first (preserves the cycle invariant). Pass '--force-skip' as the 3rd arg to override."
        exit 1
      fi
      echo "[start-task] --force-skip given; proceeding despite open predecessor."
    fi
  else
    echo "[start-task] INFO: no predecessor integer stage doc found at tasks/STAGE_${PRED_PAD}_*.md (this is OK if Stage $PRED_INT was skipped intentionally)."
  fi
fi

# ----- determine suggested role from the slug (since the task file does not exist yet) -----

# Suggested role from the slug, via the SINGLE shared word-boundary matcher (G-038 fix: no duplicated table,
# and `ci` no longer matches `pricing`). Canonical source: .claude/hooks/lib/context_loader.suggest_role_from_slug.
SUGGESTED_ROLE=$(python -c "
import sys
sys.path.insert(0, '.claude/hooks/lib')
from context_loader import suggest_role_from_slug
print(suggest_role_from_slug('$SLUG'))
")

# ----- gather mandatory reads from the suggested role's SKILL.md -----

SKILL_FILE=".claude/skills/${SUGGESTED_ROLE}/SKILL.md"
MANDATORY_READS_RAW=""
if [ -f "$SKILL_FILE" ]; then
  MANDATORY_READS_RAW=$(awk '/^# Mandatory reads/{flag=1;next} /^# /{flag=0} flag' "$SKILL_FILE")
fi

# Extract KB filenames from mandatory reads block
KB_LISTED_FROM_SKILL=$(echo "$MANDATORY_READS_RAW" | grep -oE 'KB_[0-9A-Za-z_]+\.md' | sort -u | head -10)

# Always include KB_TASK_LOG (mandatory for every task)
if ! echo "$KB_LISTED_FROM_SKILL" | grep -q '^KB_TASK_LOG\.md$'; then
  KB_LISTED_FROM_SKILL=$(printf "KB_TASK_LOG.md\n%s\n" "$KB_LISTED_FROM_SKILL")
fi

# ----- extract previous stage's hand-off block -----

PREV_STAGE_FILE=$(ls tasks/STAGE_*.md 2>/dev/null | sort | awk -F_ -v this="$STAGE_PADDED" '
  {
    file = $0
    sub(/^tasks\/STAGE_/, "", file)
    sub(/_.*$/, "", file)
    if (file < this) print $0
  }' | tail -1)
HANDOFF_BLOCK=""
if [ -n "$PREV_STAGE_FILE" ]; then
  HANDOFF_BLOCK=$(awk '/^## Hand-off/{flag=1; next} /^## /{flag=0} flag' "$PREV_STAGE_FILE")
fi

# ----- find CTO remediation entries targeting this stage -----

CTO_REMEDIATIONS=""
for MAP in audits/CTO_*_remediation_map.json; do
  [ -e "$MAP" ] || continue
  ITEMS=$(python -c "
import json
data = json.load(open(r'''$MAP''', encoding='utf-8'))
target_a = '$STAGE_PADDED'
target_b = '${STAGE_PADDED#0}'  # without leading zero
target_c = '$STAGE_DISPLAY'
for r in data.get('remediations', []):
    ts = str(r.get('target_stage', '')).strip().replace('.', '_')
    if ts in (target_a, target_b, target_c, target_c.replace('.', '_')):
        desc = r.get('description', '')
        print(f'- (from $(basename $MAP)) ' + desc)
")
  if [ -n "$ITEMS" ]; then
    CTO_REMEDIATIONS="${CTO_REMEDIATIONS}${ITEMS}\n"
  fi
done

# ----- find OPEN gaps-ledger rows targeting this stage (CTO #1 remediation #2; wired 2026-06-12) -----

LEDGER_ROWS=""
if [ -f audits/OPEN_GAPS_LEDGER.md ]; then
  LEDGER_ROWS=$(python -c "
import io, re
stage_int = '${STAGE_PADDED#0}'.split('_')[0].lstrip('0') or '0'
stage_disp = '$STAGE_DISPLAY'
pat = re.compile(r'Stage\s+(' + re.escape(stage_int) + r'|' + re.escape(stage_disp) + r')(?![.\d])')
for line in io.open('audits/OPEN_GAPS_LEDGER.md', encoding='utf-8'):
    if not line.startswith('| G-'):
        continue
    cells = [c.strip() for c in line.split('|')]
    if len(cells) < 7:
        continue
    target, status = cells[5], cells[6]
    if 'RESOLVED' in status:
        continue
    if pat.search(target) or 'every stage' in target.lower() or 'every CTO checkpoint' in target.lower():
        print('- ' + cells[1] + ': ' + (cells[2][:160] + ('…' if len(cells[2]) > 160 else '')) + f'  (target: {target}; status: {status})')
")
fi

# ----- build the task doc -----

TEMPLATE="tasks/TASK_TEMPLATE.md"
if [ ! -f "$TEMPLATE" ]; then
  echo "[start-task] ERROR: $TEMPLATE missing. Cannot seed task doc."
  exit 2
fi

# Apply template substitutions
sed -e "s|{{STAGE}}|${STAGE_DISPLAY}|g" \
    -e "s|{{STAGE_PADDED}}|${STAGE_PADDED}|g" \
    -e "s|{{SLUG}}|${SLUG}|g" \
    -e "s|{{DATE}}|$(date +%Y-%m-%d)|g" \
    "$TEMPLATE" > "$TASK_FILE"

# Append the pre-populated sections that are inferred from context
{
  echo ""
  echo "## Pre-populated by start-task.sh ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo ""

  echo "### Suggested role (from slug heuristic)"
  echo ""
  echo "**${SUGGESTED_ROLE}** — open \`.claude/skills/${SUGGESTED_ROLE}/SKILL.md\` before touching code."
  echo ""

  if [ -n "$KB_LISTED_FROM_SKILL" ]; then
    echo "### KB files to update (seeded from role's Mandatory reads)"
    echo ""
    echo "$KB_LISTED_FROM_SKILL" | while read -r kb; do
      [ -z "$kb" ] && continue
      echo "- \`knowledge-base/$kb\`"
    done
    echo ""
  fi

  if [ -n "$HANDOFF_BLOCK" ]; then
    echo "### Pre-requisites (from previous stage's hand-off — $(basename "$PREV_STAGE_FILE"))"
    echo ""
    echo "$HANDOFF_BLOCK"
    echo ""
  fi

  if [ -n "$CTO_REMEDIATIONS" ]; then
    echo "### CTO checkpoint remediations targeting this stage (auto-routed)"
    echo ""
    printf "%b\n" "$CTO_REMEDIATIONS"
    echo ""
    echo "These items MUST appear as acceptance criteria above."
    echo ""
  fi

  if [ -n "$LEDGER_ROWS" ]; then
    echo "### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)"
    echo ""
    echo "$LEDGER_ROWS"
    echo ""
    echo "Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage)."
  fi
} >> "$TASK_FILE"

# ----- echo result + context bundle -----

echo "[start-task] Created: $TASK_FILE"
echo "[start-task] Suggested role: $SUGGESTED_ROLE"
echo ""

# If load-context.py exists, emit a short bundle (quiet form via init.sh --quiet)
if [ -f scripts/load-context.py ]; then
  echo "=== Quick context (use 'bash scripts/init.sh' for the full bundle) ==="
  python scripts/load-context.py --mode=task-start --stage="$STAGE_DISPLAY" 2>/dev/null | head -40
  echo "==="
fi

echo ""
echo "[start-task] NEXT STEPS:"
echo "  1. Read the suggested role's SKILL.md: .claude/skills/${SUGGESTED_ROLE}/SKILL.md"
echo "  2. Open $TASK_FILE and fill in: Title, Acceptance criteria (specific + testable), Files to CREATE/MODIFY/DELETE."
echo "  3. Verify Pre-requisites listed are actually met (services running, prior stages done, env vars set)."
echo "  4. Implement under the role persona."
echo "  5. When ready: bash scripts/audit-task.sh $STAGE_DISPLAY"
echo "  6. Close: bash scripts/close-task.sh $STAGE_DISPLAY"
