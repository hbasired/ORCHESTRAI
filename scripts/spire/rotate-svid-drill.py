"""Stage 27 — SVID rotation drill: prove SPIRE rotates the workload cert (new serial) while the SPIFFE IDENTITY
stays constant — the zero-downtime rotating-identity property (Kagenti pattern). Run with the SPIRE overlay up.

    python scripts/spire/rotate-svid-drill.py
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from security.spiffe_identity import fetch_svid_via_docker, SpiffeUnavailable  # noqa: E402
from cryptography import x509  # noqa: E402


def _serial():
    s = fetch_svid_via_docker()
    c = x509.load_pem_x509_certificate(s.cert_path.read_bytes())
    return s.spiffe_id, c.serial_number


def main() -> int:
    try:
        sid1, ser1 = _serial()
    except SpiffeUnavailable as e:
        print(f"SKIP: SPIRE not available ({e})"); return 0
    print(f"BEFORE: {sid1} serial={ser1}")
    subprocess.run(["docker", "restart", "spire-agent"], capture_output=True)
    for _ in range(30):
        if subprocess.run(["docker", "exec", "spire-agent", "/opt/spire/bin/spire-agent", "healthcheck",
                           "-socketPath", "/tmp/spire/agent/public/api.sock"], capture_output=True).returncode == 0:
            break
        time.sleep(2)
    time.sleep(3)
    sid2, ser2 = _serial()
    print(f"AFTER:  {sid2} serial={ser2}")
    ok = (ser1 != ser2) and (sid1 == sid2)
    print("ROTATION VERIFIED — cert rotated, identity constant" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
