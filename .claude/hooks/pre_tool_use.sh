#!/usr/bin/env bash
# .claude/hooks/pre_tool_use.sh
# PreToolUse hook (matcher: Write|Edit|MultiEdit) — blocks edits to forbidden paths.
# Exit 2 to block; exit 0 to allow.
# The tool input is passed via CLAUDE_TOOL_INPUT (JSON) or CLAUDE_TOOL_FILE_PATH (string)
# depending on Claude Code version. We try both.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 0

# Extract target file path
TARGET="${CLAUDE_TOOL_FILE_PATH:-}"
if [ -z "$TARGET" ] && [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  TARGET=$(echo "$CLAUDE_TOOL_INPUT" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("file_path","") or d.get("path",""))' 2>/dev/null || echo "")
fi

[ -z "$TARGET" ] && exit 0  # Can't determine target → allow

# Normalize path (relative to repo root)
case "$TARGET" in
  /*|[A-Za-z]:*) REL="$TARGET" ;;
  *) REL="$REPO_ROOT/$TARGET" ;;
esac

block() {
  echo "[pre_tool_use BLOCK] $1" >&2
  exit 2
}

# 1. Finalized decision logs are append-only
if [[ "$REL" == *"compliance/decision-logs/"*.md ]]; then
  base=$(basename "$REL")
  if [[ "$base" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_ ]] && [ -f "$REL" ]; then
    # Already exists with a date prefix → finalized. Write a new ADR instead.
    block "Decision logs are append-only. To correct, write a new ADR: compliance/decision-logs/$(date +%Y-%m-%d)_<slug>.md"
  fi
fi

# 2. .audit-baseline outside closure ritual
if [[ "$REL" == *".audit-baseline" ]]; then
  if [ -z "${CLAUDE_HOOK_AUDIT_BASELINE_ALLOWED:-}" ]; then
    block ".audit-baseline can only be rewritten by scripts/close-task.sh. Use the closure ritual."
  fi
fi

# 3. Model card without metrics file alongside
if [[ "$REL" == *"compliance/model-cards/"*.md ]]; then
  model_name=$(basename "$REL" .md)
  if ! ls "models/$model_name.metrics.json" >/dev/null 2>&1; then
    echo "[pre_tool_use WARN] No models/$model_name.metrics.json found — model cards must ship with metrics." >&2
    # Warn but don't block (might be writing card first, metrics second).
  fi
fi

# 4. ALL existing PRD version files are frozen (hard rule 6, generalized 2026-06-11).
# Creating the NEXT version file is allowed (it won't exist yet); editing any existing one is not.
case "$(basename "$REL")" in
  PRD-ai-embodied-agent*.md)
    if [ -f "$REL" ]; then
      block "Existing PRD versions are frozen (hard rule 6; ADR 2026-06-11_strategic_product_reset). Write the next version file instead (e.g. PRD-ai-embodied-agent-v4.md)."
    fi
    ;;
esac

# 5. New random.* imports in backend (outside tests/training)
if [[ "$REL" == *"backend/"*.py ]] && [[ "$REL" != *"backend/tests/"* ]] && [[ "$REL" != *"backend/training/"* ]]; then
  if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
    NEW_CONTENT=$(echo "$CLAUDE_TOOL_INPUT" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("content","") or d.get("new_string",""))' 2>/dev/null || echo "")
    if echo "$NEW_CONTENT" | grep -qE '^[[:space:]]*import[[:space:]]+random|^[[:space:]]*from[[:space:]]+random[[:space:]]+import|random\.(uniform|choice|choices|randint|random)\('; then
      echo "[pre_tool_use WARN] random.* usage detected in non-test backend file. The audit baseline must strictly decrease — make sure this is replaced before stage close, or use secrets.SystemRandom() / os.urandom() for security-relevant randomness." >&2
      # Warn, don't block — might be removing not adding.
    fi
  fi
fi

# 6. New classical-only signatures in backend/ (after Stage 13.5)
# Conservative: warn rather than block (stage tracking is informal).
if [[ "$REL" == *"backend/crypto/"*.py ]] || [[ "$REL" == *"backend/a2a/"*.py ]]; then
  if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
    NEW_CONTENT=$(echo "$CLAUDE_TOOL_INPUT" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("content","") or d.get("new_string",""))' 2>/dev/null || echo "")
    if echo "$NEW_CONTENT" | grep -qE 'rsa\.generate_private_key|RSAPrivateKey|ec\.generate_private_key|ECDSA|EllipticCurvePrivateKey'; then
      echo "[pre_tool_use WARN] Classical signature/key gen detected in PQC-scoped file. Stage 13.5+ requires ML-DSA-65 via backend/crypto/pqc_signing.py. Hybrid wrappers OK; pure classical NOT OK in new code." >&2
    fi
  fi
fi

# 7. Block .pkl files under backend/ml/ or models/ (Stage 13.5+ trust requirement: .safetensors only)
if [[ "$REL" == *backend/ml/*.pkl ]] || [[ "$REL" == *models/*.pkl ]]; then
  block ".pkl files are not allowed in backend/ml/ or models/ (arbitrary-code-execution risk on torch.load). Use .safetensors instead. See knowledge-base/KB_19 + decision-logs/2026-05-24_governance_hardening_and_training_scaffold.md."
fi

# 8. Block edits to existing signed policy files (append-only — write a NEW policy YAML)
if [[ "$REL" == *compliance/policies/*.yaml ]] && [ -f "$REL" ]; then
  if grep -q '^# ML-DSA-65 SIGNATURE FOOTER' "$REL" 2>/dev/null; then
    block "Signed policy YAML files are append-only. Write a NEW policy file (compliance/policies/<date>_<slug>.yaml) instead of editing the signed one."
  fi
fi

# 9. Append-only enforcement for the task log + research log (G-039): block a destructive SHRINK.
#    Strikethrough corrections GROW the file (allowed); a net deletion is blocked. Override:
#    ALLOW_APPEND_ONLY_SHRINK=1 for a sanctioned rewrite.
if { [[ "$REL" == *knowledge-base/KB_TASK_LOG.md ]] || [[ "$REL" == *research/initial-research.md ]]; } \
   && [ -f "$REL" ] && [ "${ALLOW_APPEND_ONLY_SHRINK:-0}" != "1" ]; then
  DELTA=$(echo "$CLAUDE_TOOL_INPUT" | python -c '
import json, sys, os
d = json.load(sys.stdin)
fp = d.get("file_path", "") or d.get("path", "")
try:
    cur = os.path.getsize(fp)
except OSError:
    cur = 0
def n(s): return len((s or "").encode("utf-8"))
if isinstance(d.get("edits"), list):                 # MultiEdit
    delta = sum(n(e.get("new_string")) - n(e.get("old_string")) for e in d["edits"])
elif d.get("old_string") is not None:                # Edit
    delta = n(d.get("new_string")) - n(d.get("old_string"))
else:                                                # Write (replaces whole file)
    delta = n(d.get("content")) - cur
print(delta)
' 2>/dev/null || echo 0)
  if [ -n "$DELTA" ] && [ "$DELTA" -lt 0 ] 2>/dev/null; then
    block "Append-only file $REL would SHRINK by ${DELTA#-} bytes (G-039). These logs are append-only — add a new entry / strikethrough-correct (never delete). For a sanctioned rewrite set ALLOW_APPEND_ONLY_SHRINK=1."
  fi
fi

exit 0
