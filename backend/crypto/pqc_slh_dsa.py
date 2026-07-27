"""Stage 18 — SLH-DSA-SHA2-128s long-trust signatures (FIPS 205; KB_13; research §28.2).

For firmware / policy / model-card bundles with a **10-year** trust horizon, SLH-DSA (hash-based, the most
conservative PQC signature — no lattice assumption) is the right primitive (KB_13 algorithm matrix). Implemented over
the host/container **OpenSSL 3.5** CLI (which ships native FIPS-205 SLH-DSA) — a real signer with no fragile build.
Honest-unavailable (`SlhDsaUnavailable`) if OpenSSL < 3.5 is not on PATH (production/CI run on the OpenSSL-3.5 image).
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

ALGORITHM = "SLH-DSA-SHA2-128s"


class SlhDsaUnavailable(RuntimeError):
    """Raised when an OpenSSL 3.5+ providing SLH-DSA is not available — never faked (Rule 1a)."""


def _openssl() -> str:
    return os.environ.get("OPENSSL_BIN", "openssl")


def openssl_supports_slh_dsa() -> bool:
    """True only if `openssl` is ≥ 3.5 AND lists SLH-DSA-SHA2-128s."""
    try:
        ver = subprocess.run([_openssl(), "version"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"OpenSSL\s+(\d+)\.(\d+)", ver)
        if not m or (int(m.group(1)), int(m.group(2))) < (3, 5):
            return False
        algs = subprocess.run([_openssl(), "list", "-signature-algorithms"],
                              capture_output=True, text=True, timeout=10).stdout
        return "SLH-DSA-SHA2-128s" in algs
    except Exception:  # noqa: BLE001
        return False


def _require() -> None:
    if not openssl_supports_slh_dsa():
        raise SlhDsaUnavailable("OpenSSL >= 3.5 with SLH-DSA-SHA2-128s is required (FIPS 205) — not on PATH")


def _key_dir() -> Path:
    root = Path(os.environ.get("KEY_STORE_DIR", str(Path(__file__).resolve().parent / ".keystore"))) / "slh_dsa"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe(alias: str) -> str:
    s = alias
    for ch in ':\\/*?"<>|':
        s = s.replace(ch, "_")
    return s


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=60)


def generate_keypair(alias: str = "firmware-policy") -> bytes:
    """Generate a persisted SLH-DSA-SHA2-128s keypair under `alias`; return the public key (PEM bytes)."""
    _require()
    kd = _key_dir()
    keyp = kd / f"{_safe(alias)}.key"
    pubp = kd / f"{_safe(alias)}.pub"
    r = _run([_openssl(), "genpkey", "-algorithm", "SLH-DSA-SHA2-128s", "-out", str(keyp)])
    if r.returncode != 0 or not keyp.exists():
        raise SlhDsaUnavailable(f"SLH-DSA keygen failed: {r.stderr.decode(errors='replace')[:200]}")
    try:
        os.chmod(keyp, 0o600)
    except OSError:
        pass
    _run([_openssl(), "pkey", "-in", str(keyp), "-pubout", "-out", str(pubp)])
    return pubp.read_bytes()


def public_key(alias: str = "firmware-policy") -> bytes:
    return (_key_dir() / f"{_safe(alias)}.pub").read_bytes()


def sign(data: bytes, alias: str = "firmware-policy") -> bytes:
    """Sign `data` with the SLH-DSA key `alias` (auto-generates the key on first use). Returns the raw signature."""
    _require()
    keyp = _key_dir() / f"{_safe(alias)}.key"
    if not keyp.exists():
        generate_keypair(alias)
    with tempfile.TemporaryDirectory() as td:
        din, sout = Path(td) / "in.bin", Path(td) / "sig.bin"
        din.write_bytes(data)
        r = _run([_openssl(), "pkeyutl", "-sign", "-rawin", "-inkey", str(keyp), "-in", str(din), "-out", str(sout)])
        if r.returncode != 0 or not sout.exists():
            raise SlhDsaUnavailable(f"SLH-DSA sign failed: {r.stderr.decode(errors='replace')[:200]}")
        return sout.read_bytes()


def verify(data: bytes, signature: bytes, public_key_pem: Optional[bytes] = None,
           alias: str = "firmware-policy") -> bool:
    """Verify a signature. Provide the signer's public-key PEM, or rely on the stored `alias` public key. False on
    any failure (no partial trust)."""
    try:
        _require()
        with tempfile.TemporaryDirectory() as td:
            din, sin, pin = Path(td) / "in.bin", Path(td) / "sig.bin", Path(td) / "pub.pem"
            din.write_bytes(data)
            sin.write_bytes(signature)
            if public_key_pem is not None:
                pin.write_bytes(public_key_pem)
            else:
                pin.write_bytes(public_key(alias))
            r = _run([_openssl(), "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(pin),
                      "-in", str(din), "-sigfile", str(sin)])
            return r.returncode == 0 and b"Verified Successfully" in r.stdout
    except Exception:  # noqa: BLE001
        return False


def algorithm() -> str:
    return ALGORITHM


__all__ = ["ALGORITHM", "SlhDsaUnavailable", "openssl_supports_slh_dsa", "generate_keypair",
           "public_key", "sign", "verify", "algorithm"]
