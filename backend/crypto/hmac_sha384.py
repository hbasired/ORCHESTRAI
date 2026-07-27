"""Stage 13.5 — HMAC-SHA-384 helper for OT message integrity (KB_13 algorithm matrix; used at Stage 15).

HMAC-SHA-384 is quantum-resistant at this length (NIST guidance) — the right MAC for Sparkplug B payloads / OPC UA
UserTokenPolicy. Constant-time verification. (Not a PQC signature — a symmetric MAC; lives here per KB_13.)
"""
from __future__ import annotations

import hashlib
import hmac


def mac(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA-384 tag over `data` with `key`."""
    if not key:
        raise ValueError("hmac_sha384.mac requires a non-empty key")
    return hmac.new(key, data, hashlib.sha384).digest()


def verify_mac(key: bytes, data: bytes, tag: bytes) -> bool:
    """Constant-time HMAC-SHA-384 verification."""
    return hmac.compare_digest(mac(key, data), tag)


__all__ = ["mac", "verify_mac"]
