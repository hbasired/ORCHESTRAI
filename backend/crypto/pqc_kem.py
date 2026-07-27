"""Stage 18 — ML-KEM-768 application-level KEM (FIPS 203; KB_13 algorithm matrix; research §28.2).

Hybrid-TLS key exchange is terminated by the OpenSSL-3.5 sidecar (`X25519MLKEM768`); this module is the
**application-level** KEM for when the sidecar is off-path — e.g. wrapping a signing key, an A2A application-layer
shared secret. Backed by **kyber-py** (pure-Python FIPS-203 ML-KEM, the ML-KEM sibling of the Stage-13.5 dilithium-py
signer): Windows-native, no build. Honest caveat: pure-Python is NOT side-channel-hardened — production wraps/decaps in
an HSM via the same config swap as the signer (CRYPTO_PROVIDER). Decapsulation keys persist under the keystore dir.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

ALGORITHM = "ML-KEM-768"


def _kem():
    from kyber_py.ml_kem import ML_KEM_768
    return ML_KEM_768


def _kem_dir() -> Path:
    root = Path(os.environ.get("KEY_STORE_DIR", str(Path(__file__).resolve().parent / ".keystore"))) / "kem"
    root.mkdir(parents=True, exist_ok=True)
    return root


def keygen() -> tuple[bytes, bytes]:
    """Generate an ML-KEM-768 keypair. Returns (encapsulation_key [public], decapsulation_key [private])."""
    ek, dk = _kem().keygen()
    return bytes(ek), bytes(dk)


def encapsulate(peer_encapsulation_key: bytes) -> tuple[bytes, bytes]:
    """Encapsulate to a peer's public (encapsulation) key. Returns (ciphertext, shared_secret)."""
    shared_secret, ciphertext = _kem().encaps(bytes(peer_encapsulation_key))
    return bytes(ciphertext), bytes(shared_secret)


def decapsulate(ciphertext: bytes, key: Union[bytes, str], key_id: Optional[str] = None) -> bytes:
    """Decapsulate a ciphertext → shared_secret. `key` is either the raw decapsulation key (bytes) or an alias (str)
    whose key is loaded from the keystore. (`key_id` is an accepted alias-style alternative to a str `key`.)"""
    alias = key_id if key_id is not None else (key if isinstance(key, str) else None)
    if alias is not None:
        dk = (_kem_dir() / f"{_safe(alias)}.dk").read_bytes()
    else:
        dk = bytes(key)  # type: ignore[arg-type]
    return bytes(_kem().decaps(dk, bytes(ciphertext)))


def generate_kem_keypair(alias: str) -> bytes:
    """Generate + persist an ML-KEM-768 keypair under `alias`; return the public encapsulation key. The private
    decapsulation key is written to the keystore (gitignored) — chmod-600 best-effort."""
    ek, dk = keygen()
    p = _kem_dir() / f"{_safe(alias)}.dk"
    p.write_bytes(dk)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    (_kem_dir() / f"{_safe(alias)}.ek").write_bytes(ek)
    return ek


def public_kem_key(alias: str) -> bytes:
    return (_kem_dir() / f"{_safe(alias)}.ek").read_bytes()


def _safe(alias: str) -> str:
    s = alias
    for ch in ':\\/*?"<>|':
        s = s.replace(ch, "_")
    return s


__all__ = ["ALGORITHM", "keygen", "encapsulate", "decapsulate", "generate_kem_keypair", "public_kem_key"]
