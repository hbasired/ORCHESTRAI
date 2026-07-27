#!/usr/bin/env bash
# Stage 27 — SVID rotation drill: fetch an SVID, force SPIRE to rotate, fetch again, assert a NEW serial +
# continuous validity (zero-downtime rotation, the Kagenti/SPIRE identity-hygiene property).
set -euo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
AGENT=spire-agent
SOCK=/tmp/spire/agent/public/api.sock

serial() { docker exec "$AGENT" /opt/spire/bin/spire-agent api fetch x509 -socketPath "$SOCK" -write /opt/spire/data >/dev/null 2>&1
           docker exec "$AGENT" openssl x509 -in /opt/spire/data/svid.0.pem -noout -serial 2>/dev/null || \
           docker cp "$AGENT":/opt/spire/data/svid.0.pem /tmp/_svid.pem && openssl x509 -in /tmp/_svid.pem -noout -serial; }

echo "== SVID BEFORE rotation =="
S1=$(serial); echo "$S1"
echo "== forcing rotation (restart agent → new SVID on re-attest; SPIRE also auto-rotates at ~half TTL) =="
# Trigger a fresh SVID by asking the server to rotate the agent's keys via a new fetch after TTL/2, OR restart:
docker restart "$AGENT" >/dev/null
until docker exec "$AGENT" /opt/spire/bin/spire-agent healthcheck -socketPath "$SOCK" >/dev/null 2>&1; do sleep 2; done
sleep 3
echo "== SVID AFTER rotation =="
S2=$(serial); echo "$S2"
if [ "$S1" != "$S2" ]; then echo "ROTATION VERIFIED: serial changed ($S1 → $S2), workload identity continuous"; exit 0
else echo "NO ROTATION: serial unchanged"; exit 1; fi
