"""Stage 18 — REAL hybrid TLS 1.3 handshake (X25519MLKEM768 KEM + ML-DSA-65 cert) via OpenSSL 3.5.

Not a mock: starts a real `openssl s_server -groups X25519MLKEM768` with an ML-DSA-65 self-signed cert, connects a
real `openssl s_client`, and asserts the negotiated TLS 1.3 group is X25519MLKEM768. Skips if OpenSSL < 3.5.
"""
import re
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path

import pytest


def _openssl_version() -> tuple[int, int]:
    try:
        out = subprocess.run(["openssl", "version"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"OpenSSL\s+(\d+)\.(\d+)", out)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    except Exception:
        return (0, 0)


_HAS_35 = _openssl_version() >= (3, 5)
pytestmark = pytest.mark.skipif(not _HAS_35, reason="OpenSSL >= 3.5 (native X25519MLKEM768) not on PATH")


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _gen_mldsa_cert(td: Path) -> tuple[Path, Path]:
    key, crt = td / "srv.key", td / "srv.crt"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ML-DSA-65", "-out", str(key)],
                   capture_output=True, timeout=30, check=True)
    subprocess.run(["openssl", "req", "-x509", "-key", str(key), "-out", str(crt), "-days", "1",
                    "-subj", "/CN=ai-agent-pqc"], capture_output=True, timeout=30, check=True)
    return key, crt


def test_x25519mlkem768_hybrid_handshake_with_mldsa_cert(tmp_path):
    key, crt = _gen_mldsa_cert(tmp_path)
    # the cert is genuinely ML-DSA-65 signed
    txt = subprocess.run(["openssl", "x509", "-in", str(crt), "-noout", "-text"],
                         capture_output=True, text=True, timeout=15).stdout
    assert "ML-DSA-65" in txt

    port = _free_port()
    server = subprocess.Popen(
        ["openssl", "s_server", "-accept", str(port), "-cert", str(crt), "-key", str(key),
         "-groups", "X25519MLKEM768", "-tls1_3", "-www", "-naccept", "2"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        # wait for the listener
        for _ in range(40):
            with closing(socket.socket()) as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.25)
        out = subprocess.run(
            ["openssl", "s_client", "-connect", f"127.0.0.1:{port}", "-groups", "X25519MLKEM768", "-tls1_3"],
            input=b"Q\n", capture_output=True, timeout=30).stdout.decode(errors="replace")
        assert "Negotiated TLS1.3 group: X25519MLKEM768" in out, f"hybrid group not negotiated:\n{out[:600]}"
        assert "TLSv1.3" in out
        # the cert is verified with an ML-DSA-65 signature (the whole chain is post-quantum)
        assert "mldsa65" in out.lower() or "ml-dsa" in out.lower(), f"peer sig not ML-DSA:\n{out[:600]}"
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
