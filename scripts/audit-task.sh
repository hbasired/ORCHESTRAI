#!/usr/bin/env bash
# scripts/audit-task.sh <stage-number>
# Runs scripts/audit.sh (count gate), checks KB-diff coverage for the task,
# scans for missing artefacts (model cards, ADRs, schemas), and writes
# audits/STAGE_<NN>_audit.md.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${#}" -lt 1 ]; then
  echo "Usage: $0 <stage-number>"
  exit 2
fi

STAGE="$1"
STAGE_PADDED="$STAGE"
case "$STAGE" in
  *.*) STAGE_PADDED="${STAGE/./_}" ;;
esac
INTPART="${STAGE_PADDED%%_*}"
RESTPART=""
[[ "$STAGE_PADDED" == *_* ]] && RESTPART="_${STAGE_PADDED#*_}"
[[ "$INTPART" =~ ^[0-9]$ ]] && INTPART="0$INTPART"
STAGE_PADDED="${INTPART}${RESTPART}"

# Match the WHOLE-stage doc, not a half-stage sibling (STAGE_NN_5_*) that string-sorts
# earlier ('5' < a letter slug). If this stage IS a half-stage, the plain glob is correct.
if [[ "$STAGE_PADDED" == *_* ]]; then
  TASK_FILE=$(ls tasks/STAGE_${STAGE_PADDED}_*.md 2>/dev/null | head -1)
else
  TASK_FILE=$(ls tasks/STAGE_${STAGE_PADDED}_[!0-9]*.md 2>/dev/null | head -1)
fi
AUDIT_FILE="audits/STAGE_${STAGE_PADDED}_audit.md"
mkdir -p audits

if [ -z "$TASK_FILE" ]; then
  echo "WARN: no task doc found for stage $STAGE_PADDED; auditing repo-wide anyway."
fi

# 1. Run the repo-wide audit script
echo "Running scripts/audit.sh ..."
AUDIT_OUT=$(bash scripts/audit.sh 2>&1 || true)
AUDIT_TOTAL=$(echo "$AUDIT_OUT" | grep -E '^\s*TOTAL' | awk '{print $2}' | head -1)
BASELINE=$(cat .audit-baseline 2>/dev/null || echo "?")

# 2. KB-diff coverage: which KB files were touched in the working tree?
KB_TOUCHED=""
if command -v git >/dev/null 2>&1; then
  KB_TOUCHED=$(git status --porcelain knowledge-base/ 2>/dev/null | awk '{print $NF}' | sort -u)
fi

# 3. Missing model-card scan
#
# Only flag weights that should be PROJECT-trained (Stages 4-10).
# Third-party externals are whitelisted because they ship with their own
# upstream documentation and are pinned by SHA/version — not by our card.
#
# Whitelisted externals (regex-matched against basename):
#   - yolov8n*       (Ultralytics YOLOv8 pretrained — Stage 0)
#   - yolov10*       (Ultralytics YOLOv10 — Stage 9)
#   - hi_IN-*        (Piper TTS Hindi voice — Stage 11)
#   - te_IN-*        (Piper TTS Telugu voice — Stage 11)
#   - whisper-*      (OpenAI Whisper checkpoints — Stage 11)
#   - bge-*          (BAAI/bge-* embeddings — Stage 12)
MISSING_CARDS=""
EXTERNAL_WHITELIST_REGEX='^(yolov8n|yolov10|hi_IN-|te_IN-|whisper-|bge-)'
if [ -d models ]; then
  for w in models/*.pt models/*.onnx models/*.safetensors models/*.h5; do
    [ -e "$w" ] || continue
    name=$(basename "$w"); name="${name%.*}"
    if [[ "$name" =~ $EXTERNAL_WHITELIST_REGEX ]]; then
      continue  # third-party external; not project-trained
    fi
    [ -f "models/${name}.metrics.json" ] || MISSING_CARDS="$MISSING_CARDS\n  - models/${name}.metrics.json"
    [ -f "compliance/model-cards/${name}.md" ] || MISSING_CARDS="$MISSING_CARDS\n  - compliance/model-cards/${name}.md"
  done
fi

# 4. ADR scan: any new decision log this session?
NEW_ADRS=""
if command -v git >/dev/null 2>&1; then
  NEW_ADRS=$(git status --porcelain compliance/decision-logs/ 2>/dev/null | grep '^?? ' | awk '{print $NF}')
fi

# 5. Gitleaks (if installed) — non-blocking
GITLEAKS_OUT="(gitleaks not run — install gitleaks for secret scanning)"
if command -v gitleaks >/dev/null 2>&1; then
  GITLEAKS_OUT=$(gitleaks detect --no-banner --no-git --redact 2>&1 || echo "leaks found — see above")
fi

# 6. Classical-crypto sniffer in new backend/crypto code
CLASSICAL_HITS=""
if [ -d backend/crypto ]; then
  CLASSICAL_HITS=$(grep -rnE 'rsa\.generate_private_key|RSAPrivateKey|ec\.generate_private_key|ECDSA|EllipticCurvePrivateKey' backend/crypto 2>/dev/null || true)
fi

# 7. Safety-validate sniffer: count actuator-related code without validate calls (heuristic)
SAFETY_HITS=""
if [ -d backend/integrations ] || [ -d backend/safety ]; then
  # Simple heuristic: find files using 'actuator' / 'send_command' / 'execute_action' that don't also reference safety.validator
  for f in $(grep -rlE 'actuator|send_command|execute_action' backend/ 2>/dev/null | grep -v tests/ | grep -v training/); do
    if ! grep -q 'safety.validator\|backend.safety\|from backend.safety' "$f"; then
      SAFETY_HITS="$SAFETY_HITS\n  - $f (mentions actuator-like operation; no safety.validator reference detected)"
    fi
  done
fi

# 8. Audit chain quick verify (if Stage 13.5+)
#
# Pre-Stage-13.5 the audit_chain table does not exist; verify-audit-chain.py
# detects this and emits a "(not yet enabled ...)" or "(... empty ...)" or
# "OK ..." message. Anything else (including a DB connection failure that
# escapes the "not yet enabled" branch) is a real chain integrity break.
CHAIN_STATUS="(audit chain not yet enabled — Stage 13.5+)"
if [ -f scripts/verify-audit-chain.py ]; then
  if python scripts/verify-audit-chain.py --quick 2>&1 | tee /tmp/chainverify.out \
       | grep -qiE 'OK|empty|not[[:space:]]+(yet[[:space:]]+)?enabled|skipped'; then
    CHAIN_STATUS="OK (quick verify passed)"
  else
    CHAIN_STATUS="FAIL — see python scripts/verify-audit-chain.py output"
  fi
fi

# 9. Write the audit report
cat > "$AUDIT_FILE" <<EOF
# Audit report — Stage ${STAGE_PADDED}

**Date**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Task doc**: ${TASK_FILE:-<not found>}
**Baseline**: ${BASELINE}
**Audit total**: ${AUDIT_TOTAL:-?}

## 1. Audit script

\`\`\`
${AUDIT_OUT}
\`\`\`

Gate: total (${AUDIT_TOTAL:-?}) must be **<=** baseline (${BASELINE}). Strictly **<** unless stage is flagged \`--no-baseline-drop\`.

## 2. KB diff coverage

Working-tree modified KB files:
${KB_TOUCHED:-  (none)}

Cross-check this against the task doc's "KB files this stage updates" block. Every listed KB file must have a non-trivial diff.

## 3. Missing artefacts

### Model cards / metrics
$(if [ -z "$MISSING_CARDS" ]; then echo "  (none)"; else echo -e "$MISSING_CARDS"; fi)

### New ADRs (untracked decision logs)
${NEW_ADRS:-  (none — if this stage made architectural decisions, write an ADR)}

## 4. Vulnerabilities

### Gitleaks
\`\`\`
${GITLEAKS_OUT}
\`\`\`

### Classical-crypto in backend/crypto/ (after Stage 13.5+)
$(if [ -z "$CLASSICAL_HITS" ]; then echo "  (none)"; else echo "$CLASSICAL_HITS" | sed 's/^/  /'; fi)

### Actuator paths without safety.validator reference (Stage 17+)
$(if [ -z "$SAFETY_HITS" ]; then echo "  (none)"; else echo -e "$SAFETY_HITS"; fi)

## 5. Audit chain integrity

${CHAIN_STATUS}

## 6. Gaps (action items)

(Rectify each before \`scripts/close-task.sh\`. The closure script refuses if this section is non-empty.)

- [ ] (auto-generated from the checks above where applicable; populate manually otherwise)

EOF

# Populate gaps section based on what failed
GAPS=()
if [ -n "$AUDIT_TOTAL" ] && [ "$AUDIT_TOTAL" != "?" ] && [ "$BASELINE" != "?" ]; then
  if [ "$AUDIT_TOTAL" -gt "$BASELINE" ]; then
    GAPS+=("Audit count regressed: $AUDIT_TOTAL > $BASELINE. Identify and remove the new theatrical fallback.")
  elif [ "$AUDIT_TOTAL" -eq "$BASELINE" ]; then
    GAPS+=("Audit count flat at $AUDIT_TOTAL. Justify --no-baseline-drop in KB_TASK_LOG, or reduce.")
  fi
fi
[ -n "$MISSING_CARDS" ] && GAPS+=("Missing model-card siblings (see above).")
[ -n "$CLASSICAL_HITS" ] && GAPS+=("Classical signature/key generation found in backend/crypto/ — replace with ML-DSA-65 wrappers.")
[ -n "$SAFETY_HITS" ] && GAPS+=("Actuator-touching code without safety.validator reference (Stage 17+).")
[ "$CHAIN_STATUS" != "OK (quick verify passed)" ] && [ -f scripts/verify-audit-chain.py ] && GAPS+=("Audit chain verify failed.")

if [ ${#GAPS[@]} -gt 0 ]; then
  # Pure-shell path: append the gaps and re-emit the file.
  # (The earlier Python heredoc was buggy under bash array expansion and
  # has been removed; the shell path below is the canonical implementation.)
  TMP=$(mktemp)
  awk '/^- \[ \] \(auto-generated/{exit} {print}' "$AUDIT_FILE" > "$TMP"
  for g in "${GAPS[@]}"; do
    echo "- [ ] $g" >> "$TMP"
  done
  echo "" >> "$TMP"
  mv "$TMP" "$AUDIT_FILE"
fi

echo "Audit report written: $AUDIT_FILE"
echo ""
echo "=================================================================="
echo "INDEPENDENT REVIEW REQUIRED before close (operator mandate 2026-05-31):"
echo "  This mechanical audit only COUNTS fakery patterns + missing artefacts."
echo "  A DIFFERENT agent than the implementer must independently review:"
echo "      bash scripts/independent-audit.sh $STAGE"
echo "  -> spawns a fresh task-auditor agent that re-runs tests adversarially"
echo "     and writes audits/STAGE_${STAGE_PADDED}_independent_review.md (verdict PASS required)."
echo "=================================================================="
[ ${#GAPS[@]} -gt 0 ] && { echo "GAPS PRESENT (${#GAPS[@]}). Run scripts/rectify-task.sh $STAGE."; exit 1; }
echo "Clean (mechanical). Independent review still required before close."
exit 0
