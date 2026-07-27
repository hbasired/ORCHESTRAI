#!/usr/bin/env bash
# scripts/rectify-task.sh <stage-number>
# Lists open gaps from audits/STAGE_<NN>_audit.md as a numbered TODO list.
# The agent rectifies and re-runs audit-task.sh until the list is empty.

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

AUDIT_FILE="audits/STAGE_${STAGE_PADDED}_audit.md"
if [ ! -f "$AUDIT_FILE" ]; then
  echo "ERROR: $AUDIT_FILE not found. Run scripts/audit-task.sh $STAGE first."
  exit 2
fi

echo "Open gaps from $AUDIT_FILE:"
echo ""
N=0
while IFS= read -r line; do
  N=$((N+1))
  echo "  $N. ${line#- \[ \] }"
done < <(grep -E '^- \[ \] ' "$AUDIT_FILE" | grep -v '\(auto-generated')

if [ "$N" -eq 0 ]; then
  echo "  (none — ready to close: bash scripts/close-task.sh $STAGE)"
  exit 0
fi

echo ""
echo "After fixing, mark items done by changing '- [ ]' to '- [x]' in $AUDIT_FILE,"
echo "then re-run: bash scripts/audit-task.sh $STAGE"
echo "Loop until all gaps are resolved, then: bash scripts/close-task.sh $STAGE"
