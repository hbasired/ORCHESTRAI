#!/usr/bin/env bash
# Stage 18 — generate the PQC TLS server cert chain (ML-DSA-65 self-signed) for the hybrid-TLS sidecar.
# Requires OpenSSL 3.5+ (native ML-DSA). Output → docker/secrets/pqc/ (gitignored). For dev/pilot; production uses a
# CA-issued ML-DSA cert chain via the KeyProvider/HSM. The KEX (X25519MLKEM768) is negotiated at handshake time and is
# independent of the cert sig-alg; an ML-DSA-65 leaf makes the WHOLE chain post-quantum.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="docker/secrets/pqc"
mkdir -p "$OUT"

ver=$(openssl version | grep -oE '3\.[0-9]+' | head -1)
maj=${ver%%.*}; min=${ver##*.}
if [ "$maj" -lt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -lt 5 ]; }; then
  echo "REFUSE: OpenSSL >= 3.5 required for ML-DSA / X25519MLKEM768 (found $(openssl version))."
  exit 2
fi

openssl genpkey -algorithm ML-DSA-65 -out "$OUT/server.key"
# MSYS_NO_PATHCONV avoids Git-Bash mangling the -subj; on Linux it is a harmless no-op.
MSYS_NO_PATHCONV=1 openssl req -x509 -key "$OUT/server.key" -out "$OUT/server.crt" -days 365 -subj "/CN=ai-agent-pqc"
chmod 600 "$OUT/server.key" 2>/dev/null || true

echo "Wrote $OUT/server.{key,crt} (sig-alg: $(openssl x509 -in "$OUT/server.crt" -noout -text | grep -m1 -i 'Signature Algorithm' | sed 's/.*: //'))"
echo "Verify the live hybrid handshake:"
echo "  openssl s_server -accept 8443 -cert $OUT/server.crt -key $OUT/server.key -groups X25519MLKEM768 -tls1_3 -www &"
echo "  openssl s_client -connect localhost:8443 -groups X25519MLKEM768 -tls1_3   # -> Negotiated group: X25519MLKEM768"
