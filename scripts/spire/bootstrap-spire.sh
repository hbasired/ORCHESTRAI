#!/usr/bin/env bash
# Stage 27 — bring up SPIRE (server + agent) + register the A2A workload identities. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."

docker compose -f docker/docker-compose.spire.yml up -d spire-server
echo "waiting for spire-server healthcheck..."
until docker exec spire-server /opt/spire/bin/spire-server healthcheck >/dev/null 2>&1; do sleep 2; done

TOKEN=$(docker exec spire-server /opt/spire/bin/spire-server token generate \
        -spiffeID spiffe://ai-agent.local/agent-node | sed 's/Token: //')
echo "join token generated"
SPIRE_JOIN_TOKEN="$TOKEN" docker compose -f docker/docker-compose.spire.yml up -d spire-agent
until docker exec spire-agent /opt/spire/bin/spire-agent healthcheck \
      -socketPath /tmp/spire/agent/public/api.sock >/dev/null 2>&1; do sleep 2; done
echo "spire-agent healthy"

for wl in a2a-server a2a-client; do
  docker exec spire-server /opt/spire/bin/spire-server entry create \
    -parentID spiffe://ai-agent.local/agent-node \
    -spiffeID  "spiffe://ai-agent.local/${wl}" \
    -selector  unix:uid:0 -x509SVIDTTL 3600 2>/dev/null || true
done
echo "workload entries ensured; fetching a probe SVID:"
docker exec spire-agent /opt/spire/bin/spire-agent api fetch x509 \
  -socketPath /tmp/spire/agent/public/api.sock | head -6
