"""Stage 13.5 — ML-DSA-65 sign/verify over the KeyProvider (KB_13). The API `audit_chain` + scripts call.

`audit_chain._sign()` (Stage 12) already does `from crypto.pqc_signing import sign as pqc_sign, active_key_version`
and `scripts/verify-audit-chain.py` does `from backend.crypto.pqc_signing import verify` — this module makes those
real (FIPS-204 ML-DSA-65 via the configured provider). No caller imports a concrete backend.
"""
from __future__ import annotations

import os
from typing import Optional

ALGORITHM = "ML-DSA-65"


def default_alias() -> str:
    return os.environ.get("AGENT_IDENTITY_ALIAS", "agent-identity")


def sign(data: bytes, alias: Optional[str] = None) -> bytes:
    """Sign `data` with the active key version of the agent-identity alias (ML-DSA-65)."""
    from crypto.key_provider import get_key_provider
    return get_key_provider().sign(alias or default_alias(), data)


def verify(data: bytes, sig: bytes, public_key: bytes) -> bool:
    """Verify an ML-DSA-65 signature over `data` under `public_key` (pure — works for historical/peer keys)."""
    from crypto.key_provider import get_key_provider
    return get_key_provider().verify(public_key, data, sig, algorithm=ALGORITHM)


def active_key_version(alias: Optional[str] = None) -> int:
    from crypto.key_provider import get_key_provider
    return get_key_provider().active_version(alias or default_alias())


def public_key(alias: Optional[str] = None, version: Optional[int] = None) -> bytes:
    from crypto.key_provider import get_key_provider
    return get_key_provider().public_key(alias or default_alias(), version)


def algorithm() -> str:
    return ALGORITHM


__all__ = ["sign", "verify", "active_key_version", "public_key", "algorithm", "default_alias", "ALGORITHM"]
