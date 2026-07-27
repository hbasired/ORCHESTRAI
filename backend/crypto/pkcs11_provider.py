"""Stage 13.5 — Pkcs11KeyProvider: HSM / SoftHSM via PKCS#11 (KB_13). Honest stub.

The SAME driver targets SoftHSM (dev) and a real HSM (prod) — only the token/slot differs (KB_13 §"Why the swap is
fast"). The full implementation + the documented software→pkcs11 swap drill land at the Stage-22 pilot. Until then
this provider is an HONEST stub: it raises with guidance rather than silently faking HSM-grade signing (Rule 1a).
The KeyProvider ABC is the real deliverable — selecting `CRYPTO_PROVIDER=pkcs11` is a config change, no caller edits.
"""
from __future__ import annotations

from typing import Any, Optional

from crypto.key_provider import DEFAULT_ALGORITHM, KeyProvider

_MSG = ("Pkcs11KeyProvider is not yet wired (Stage 22 pilot: SoftHSM dev token + real HSM share this PKCS#11 path). "
        "Set CRYPTO_PROVIDER=software for the dev ML-DSA-65 signer, or wire PKCS11_MODULE/TOKEN/PIN + python-pkcs11.")


class Pkcs11KeyProvider(KeyProvider):
    def __init__(self) -> None:
        raise NotImplementedError(_MSG)

    def generate_keypair(self, alias: str, algorithm: str = DEFAULT_ALGORITHM) -> int: raise NotImplementedError(_MSG)
    def sign(self, alias: str, data: bytes) -> bytes: raise NotImplementedError(_MSG)
    def verify(self, public_key: bytes, data: bytes, sig: bytes, algorithm: str = DEFAULT_ALGORITHM) -> bool: raise NotImplementedError(_MSG)
    def public_key(self, alias: str, version: Optional[int] = None) -> bytes: raise NotImplementedError(_MSG)
    def active_version(self, alias: str) -> int: raise NotImplementedError(_MSG)
    def rotate(self, alias: str) -> int: raise NotImplementedError(_MSG)
    def capabilities(self) -> dict[str, Any]: raise NotImplementedError(_MSG)


__all__ = ["Pkcs11KeyProvider"]
