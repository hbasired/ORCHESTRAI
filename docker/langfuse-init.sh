#!/usr/bin/env bash
# Stage 12.5 — Langfuse first-boot helper (KB_15). Langfuse v3 self-hosted creates its org/project + API keys via
# the UI on first run; this script documents + automates the non-UI bits and prints the LANGFUSE_TOKEN the
# otel-collector needs (base64 of "public_key:secret_key").
#
#   bash docker/langfuse-init.sh   # after `docker compose ... -f docker-compose.observability.yml up -d langfuse-web`
set -euo pipefail

LANGFUSE_URL="${LANGFUSE_URL:-http://localhost:3001}"

echo "Langfuse first-boot setup"
echo "  1. Open ${LANGFUSE_URL} and create the initial user + organisation + project (one-time, UI)."
echo "  2. In the project settings, create an API key pair (public pk-... + secret sk-...)."
echo "  3. Export them, then this script prints the LANGFUSE_TOKEN for docker/otel-collector-config.yaml:"

if [[ -n "${LANGFUSE_PUBLIC_KEY:-}" && -n "${LANGFUSE_SECRET_KEY:-}" ]]; then
  TOKEN="$(printf '%s:%s' "${LANGFUSE_PUBLIC_KEY}" "${LANGFUSE_SECRET_KEY}" | base64 | tr -d '\n')"
  echo ""
  echo "LANGFUSE_TOKEN=${TOKEN}"
  echo "  → put this in your env / .env so the otel-collector can authenticate to Langfuse ingestion."
else
  echo ""
  echo "  (set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY and re-run to emit LANGFUSE_TOKEN)"
fi

echo ""
echo "Then point the backend at the collector:  OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318"
echo "Traces will flow: backend → otel-collector → Langfuse (${LANGFUSE_URL}) + Phoenix (http://localhost:6006)."
