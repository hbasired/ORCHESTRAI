#!/usr/bin/env bash
# scripts/next-task.sh [--from <stage>] [--quiet]
#
# Seeds the NEXT stage's task doc after a successful close-task.sh.
# Called automatically at the end of close-task.sh; can also be run manually.
#
# Stage-discovery logic (post v2 expansion):
#   - If --from <N> is supplied: compute next stage strictly AFTER N (looking
#     at integer + half stages in order N+0.5 then N+1 then N+1.5...).
#   - If --from is NOT supplied: fall back to the highest-numbered
#     CLOSED task doc (status: done) plus 1. This is more conservative than
#     "highest existing doc" because the v2 expansion pre-seeded future
#     template task docs that are NOT yet closed.
#
# Behaviour when the next slot already has a task doc:
#   - If a STAGE_<NEXT>_<anyslug>.md exists, this script is a no-op and
#     reports the existing file. Half-stages count: STAGE_03_5_* satisfies
#     "next is 3.5".
#   - Operator can then rename to a meaningful slug via start-task.sh.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FROM_STAGE=""
QUIET=""
while [ "${#}" -gt 0 ]; do
  case "$1" in
    --from)  FROM_STAGE="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    *)       echo "Unknown arg: $1"; exit 2 ;;
  esac
done

# ----- helpers ----------------------------------------------------------

# Normalise a stage number like "3", "3.5", "11_5", "03" into the canonical
# zero-padded form used by filenames: "03", "03_5", "11", "11_5".
canon_stage() {
  local s="$1"
  s="${s//./_}"               # 3.5 -> 3_5
  local int_part="${s%%_*}"   # "3_5" -> "3"
  local rest=""
  if [[ "$s" == *_* ]]; then
    rest="_${s#*_}"           # "_5"
  fi
  if [[ "$int_part" =~ ^[0-9]$ ]]; then
    int_part="0$int_part"     # 3 -> 03
  fi
  printf '%s%s' "$int_part" "$rest"
}

# Return the integer + fractional parts of a canonical stage (eg "03_5" -> "3 0.5").
stage_parts() {
  local canon="$1"
  local int_part="${canon%%_*}"
  local int_dec=$((10#$int_part))
  local frac="0"
  if [[ "$canon" == *_* ]]; then
    local sub="${canon#*_}"
    # Only "_5" supported (half-stage). Anything else treated as 0.5 too.
    frac="5"
  fi
  printf '%d %s' "$int_dec" "$frac"
}

# Given a stage, return a list of candidate "next" stage canonical strings,
# in priority order.
#
# Rule: half-stages (N.5) only appear in the candidate list if a task doc
# for them ALREADY exists in tasks/ — the v2 expansion pre-seeded the
# specific half-stages that ARE in the roadmap (3.5 CTO#1, 10.5 CTO#2,
# 11.5 MCP, 12.5 observability, 13.5 PQC, 14.5 CTO#3, 21.5 CTO#4,
# 24.5 CTO#5, 25.5 Digital Triplet). We don't speculatively seed
# arbitrary N.5 stages — they're not in the roadmap.
#
# Examples (assuming the v2 expansion docs are present):
#   from=02 -> 03 (no 2.5 in roadmap) 03_5 04 ...
#   from=03 -> 03_5 (pre-seeded) 04 ...
#   from=03_5 -> 04 ...
#   from=10 -> 10_5 (pre-seeded) 11 ...
next_stage_candidates() {
  local canon="$1"
  read int_dec frac <<<"$(stage_parts "$canon")"
  local upper=$((int_dec + 8))   # search window
  local results=()
  if [ "$frac" = "0" ]; then
    # current is N (whole).
    # First try N.5 but ONLY if pre-seeded.
    if ls "tasks/STAGE_$(canon_stage "${int_dec}_5")"_*.md >/dev/null 2>&1; then
      results+=("$(canon_stage "${int_dec}_5")")
    fi
    # Then N+1, N+1.5 (if pre-seeded), N+2, N+2.5 (if pre-seeded), ...
    for ((i = int_dec + 1; i <= upper; i++)); do
      results+=("$(canon_stage "$i")")
      if ls "tasks/STAGE_$(canon_stage "${i}_5")"_*.md >/dev/null 2>&1; then
        results+=("$(canon_stage "${i}_5")")
      fi
    done
  else
    # current is N.5. Next is N+1, then N+1.5 (if pre-seeded), ...
    for ((i = int_dec + 1; i <= upper; i++)); do
      results+=("$(canon_stage "$i")")
      if ls "tasks/STAGE_$(canon_stage "${i}_5")"_*.md >/dev/null 2>&1; then
        results+=("$(canon_stage "${i}_5")")
      fi
    done
  fi
  printf '%s\n' "${results[@]}"
}

# Highest-numbered closed (status=done) task doc.
highest_closed_stage() {
  local last=""
  for f in $(ls tasks/STAGE_*.md 2>/dev/null | sort); do
    local status
    status=$(python -c "
import sys
sys.path.insert(0, '.claude/hooks/lib')
from context_loader import extract_status
print(extract_status(open(r'''$f''', encoding='utf-8', errors='ignore').read()))
" 2>/dev/null)
    if [ "$status" = "done" ]; then
      last="$f"
    fi
  done
  if [ -n "$last" ]; then
    basename "$last" .md | sed -E 's/^STAGE_([0-9_]+)_.*/\1/'
  fi
}

# ----- determine FROM stage --------------------------------------------

if [ -z "$FROM_STAGE" ]; then
  FROM_STAGE=$(highest_closed_stage)
  if [ -z "$FROM_STAGE" ]; then
    echo "next-task: no closed task docs found. Use scripts/start-task.sh <stage> <slug> to seed the first."
    exit 0
  fi
  [ -n "$QUIET" ] || echo "next-task: --from not given; falling back to highest closed stage: $FROM_STAGE"
fi

FROM_CANON=$(canon_stage "$FROM_STAGE")

# ----- find the next slot ----------------------------------------------

NEXT_CANON=""
EXISTING_PATH=""
while IFS= read -r candidate; do
  if [ -z "$candidate" ]; then continue; fi
  # Glob carefully: STAGE_03_*.md naively matches STAGE_03_5_*.md too. We
  # want whole-stage docs only when candidate is a whole stage, and
  # half-stage docs only when candidate explicitly ends in _5.
  if [[ "$candidate" == *_5 ]]; then
    existing=$(ls "tasks/STAGE_${candidate}"_*.md 2>/dev/null | head -1)
  else
    # Whole-stage candidate. Exclude STAGE_NN_<digit>_* (the half-stage form).
    existing=$(ls "tasks/STAGE_${candidate}"_[!0-9]*.md 2>/dev/null | head -1)
  fi
  if [ -n "$existing" ]; then
    # If it exists AND is not "done", that's the next slot the operator
    # should pick up.
    status=$(python -c "
import sys
sys.path.insert(0, '.claude/hooks/lib')
from context_loader import extract_status
print(extract_status(open(r'''$existing''', encoding='utf-8', errors='ignore').read()))
" 2>/dev/null)
    if [ "$status" != "done" ]; then
      NEXT_CANON="$candidate"
      EXISTING_PATH="$existing"
      break
    fi
    # Already done; keep looking forward.
    continue
  fi
  # Slot is empty -> seed here.
  NEXT_CANON="$candidate"
  break
done < <(next_stage_candidates "$FROM_CANON")

if [ -z "$NEXT_CANON" ]; then
  echo "next-task: could not determine a next slot after stage $FROM_CANON within the search window."
  exit 0
fi

NEXT_DISPLAY="${NEXT_CANON//_/.}"

# ----- if the next slot already has a doc, no-op + report --------------

if [ -n "$EXISTING_PATH" ]; then
  echo "next-task: next slot is stage $NEXT_DISPLAY -- task doc already exists at $EXISTING_PATH (status: not-started or in-progress)."
  echo "next-task: operator should run \`/begin\` (or 'bash scripts/init.sh') to enter it."
  exit 0
fi

# ----- otherwise, seed a TBD task doc -----------------------------------

TEMPLATE="tasks/TASK_TEMPLATE.md"
if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: $TEMPLATE missing."
  exit 2
fi

NEXT_FILE="tasks/STAGE_${NEXT_CANON}_TBD.md"

# Extract hand-off block from the FROM stage's task doc, if any.
FROM_FILE=$(ls tasks/STAGE_${FROM_CANON}_*.md 2>/dev/null | head -1)
HANDOFF=""
if [ -n "$FROM_FILE" ]; then
  HANDOFF=$(awk '/^## Hand-off/{flag=1; next} /^## /{flag=0} flag' "$FROM_FILE")
fi

sed -e "s|{{STAGE}}|${NEXT_DISPLAY}|g" \
    -e "s|{{STAGE_PADDED}}|${NEXT_CANON}|g" \
    -e "s|{{SLUG}}|TBD|g" \
    -e "s|{{DATE}}|$(date +%Y-%m-%d)|g" \
    "$TEMPLATE" > "$NEXT_FILE"

if [ -n "$HANDOFF" ]; then
  {
    echo ""
    echo "## Pre-requisites (pre-filled from $(basename "$FROM_FILE") hand-off)"
    echo ""
    echo "$HANDOFF"
  } >> "$NEXT_FILE"
fi

echo "next-task: seeded $NEXT_FILE (TBD slug)"
echo "next-task: rename to a meaningful slug via 'bash scripts/start-task.sh ${NEXT_DISPLAY} <slug>' (or edit + rename the file manually)"
