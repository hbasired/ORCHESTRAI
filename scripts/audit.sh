#!/usr/bin/env bash
# scripts/audit.sh — recurring re-audit script run at the close of every stage.
#
# Purpose: enforce honesty discipline. Greps for the known theatrical fallbacks
# in the codebase and reports the count. The iterative cycle protocol
# (knowledge-base/KB_README.md) requires that this count strictly decrease
# from one stage to the next.
#
# Exit codes:
#   0  — count is at or below the recorded baseline for the current stage
#   1  — count regressed (something fake leaked back in)
#   2  — usage / environment error
#
# Usage:
#   scripts/audit.sh                # report; compare to baseline if present
#   scripts/audit.sh --baseline     # write current count to .audit-baseline (run at end of a stage)
#   scripts/audit.sh --json         # machine-readable output
#
# Run from repo root.

set -euo pipefail

# ----- config -----
BASELINE_FILE=".audit-baseline"
SEARCH_PATHS=("backend" "frontend-nextjs/src")

# Patterns we treat as theatrical fallbacks. Each row: <label>|<pattern>|<ext-csv>
# Patterns are extended regex (egrep -E). ext-csv is comma-separated extensions
# without dots (e.g. "py" or "ts,tsx,js,jsx").
PATTERNS=(
  "random_uniform_py|random\.uniform|py"
  "random_choice_py|random\.choice|py"
  "random_choices_py|random\.choices|py"
  "math_random_ts|Math\.random|ts,tsx,js,jsx"
  "hardcoded_responses_ts|^[[:space:]]*const[[:space:]]+RESPONSES[[:space:]]*=|ts,tsx"
  "hardcoded_models_ts|^[[:space:]]*const[[:space:]]+MODELS[[:space:]]*=|ts,tsx"
  "generate_mock_state|generateMockState|ts,tsx,js,jsx"
  "generate_robots|generateRobots|ts,tsx,js,jsx"
  "mock_detections|_generate_mock_detections|py"
  "mock_predictions|_generate_mock_predictions|py"
  "heuristic_actions|_generate_heuristic_actions|py"
  "get_demo_metrics|_get_demo_metrics|py"
)

# Whitelist: files / lines that are *expected* to contain these patterns
# (tests intentionally use random, fixtures, training notebooks, etc.).
# Grep -v against these to avoid false positives.
WHITELIST=(
  "backend/tests/"
  "frontend-nextjs/__tests__/"
  "backend/training/"
  "scripts/audit.sh"           # this file
  "\.md:"                      # markdown documents (KB / research)
  # Stage 28 (G-085) audit-hygiene fix: exclude GITIGNORED THIRD-PARTY code. `backend/venv/` (numpy/scipy/sklearn/
  # etc.) is an untracked local virtualenv — NOT project source — yet it contributed ~212 of the pre-Stage-28 "364"
  # (numpy/scipy random.* in their own tests). The audit's purpose is PROJECT theatre, not third-party libraries; a
  # clean CI checkout never even has these dirs. `node_modules` is the frontend equivalent. This makes the count
  # honestly measure project code (see ADR 2026-07-04_stage28_graphrag_adoption_ux + KB_TASK_LOG for the finding).
  "backend/venv/"
  "backend/\.venv/"
  "/node_modules/"
  "/site-packages/"
)

# ----- helpers -----
print_usage() {
  cat <<EOF
Usage: scripts/audit.sh [--baseline | --json]

Run from the repo root. Reports counts of theatrical fallback patterns
across backend/ and frontend-nextjs/src/. Use --baseline at the close of
a stage to lock in the current count for future comparison.
EOF
}

count_matches() {
  local label="$1"
  local pattern="$2"
  local ext_csv="$3"

  # Build --include args from the ext-csv (e.g. "ts,tsx,js,jsx" → 4 --include flags)
  local -a include_args=()
  IFS=',' read -ra exts <<<"$ext_csv"
  for ext in "${exts[@]}"; do
    include_args+=("--include=*.$ext")
  done

  # Build a temp grep result, then filter whitelist
  local raw_matches
  raw_matches=$(
    grep -RnE "${include_args[@]}" "$pattern" "${SEARCH_PATHS[@]}" 2>/dev/null || true
  )

  local filtered="$raw_matches"
  for white in "${WHITELIST[@]}"; do
    filtered=$(echo "$filtered" | grep -v -E "$white" || true)
  done

  # Empty filtered → 0; otherwise wc -l
  if [[ -z "$filtered" ]]; then
    echo 0
  else
    echo "$filtered" | wc -l | tr -d ' '
  fi
}

# ----- arg parse -----
MODE="report"
if [[ "${1:-}" == "--baseline" ]]; then
  MODE="baseline"
elif [[ "${1:-}" == "--json" ]]; then
  MODE="json"
elif [[ -n "${1:-}" ]]; then
  print_usage
  exit 2
fi

# ----- repo root sanity check -----
if [[ ! -d "backend" || ! -d "frontend-nextjs" ]]; then
  echo "ERROR: must run from repo root (expected backend/ and frontend-nextjs/ here)" >&2
  exit 2
fi

# ----- run -----
declare -A counts
total=0
for row in "${PATTERNS[@]}"; do
  IFS='|' read -r label pattern glob <<<"$row"
  count=$(count_matches "$label" "$pattern" "$glob")
  counts["$label"]=$count
  total=$((total + count))
done

# ----- output -----
if [[ "$MODE" == "json" ]]; then
  # naive JSON emission (avoid jq dependency)
  printf '{\n  "total": %d,\n  "counts": {\n' "$total"
  first=1
  for label in "${!counts[@]}"; do
    if [[ $first -eq 1 ]]; then first=0; else printf ',\n'; fi
    printf '    "%s": %d' "$label" "${counts[$label]}"
  done
  printf '\n  }\n}\n'
elif [[ "$MODE" == "baseline" ]]; then
  echo "$total" >"$BASELINE_FILE"
  echo "Baseline written to $BASELINE_FILE: $total theatrical-fallback occurrences"
else
  echo "Audit report ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo "============================================="
  for label in "${!counts[@]}"; do
    printf "  %-30s %4d\n" "$label" "${counts[$label]}"
  done
  echo "---------------------------------------------"
  printf "  %-30s %4d\n" "TOTAL" "$total"

  # Stage 18 (KB_13): classical-only crypto is FORBIDDEN in new backend/crypto + backend/a2a code. Match real API
  # calls (not comment/docstring mentions of "ECDSA"/"RSA" — those legitimately appear in the forbidden-list docs).
  classical=$(grep -RnE 'rsa\.generate_private_key|ec\.generate_private_key|EllipticCurvePrivateKey|ec\.ECDSA\(|dsa\.generate_private_key' \
    backend/crypto backend/a2a 2>/dev/null | grep -v -E '__pycache__|/tests/' || true)
  if [[ -n "$classical" ]]; then
    echo "---------------------------------------------"
    echo "CLASSICAL-CRYPTO VIOLATION (forbidden after Stage 13.5; KB_13):"
    echo "$classical"
    exit 1
  fi

  if [[ -f "$BASELINE_FILE" ]]; then
    baseline=$(cat "$BASELINE_FILE")
    echo "---------------------------------------------"
    echo "Baseline (from $BASELINE_FILE): $baseline"
    if [[ "$total" -gt "$baseline" ]]; then
      echo "REGRESSION: count is HIGHER than baseline ($total > $baseline)."
      echo "The iterative cycle requires this count to strictly decrease."
      exit 1
    elif [[ "$total" -eq "$baseline" ]]; then
      echo "NO PROGRESS: count is equal to baseline ($total)."
      echo "Did this stage actually replace any fakery? If not, the stage isn't done."
      # Don't fail; some stages legitimately don't touch ML fakery (e.g. Stage 14 hardening).
    else
      echo "OK: count decreased from $baseline to $total."
    fi
  else
    echo ""
    echo "No baseline file found at $BASELINE_FILE."
    echo "Run with --baseline at the close of this stage to lock in the current count."
  fi
fi
