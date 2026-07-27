"""Stage 13.5 — VaultTransitProvider: HashiCorp Vault Transit signing (KB_13). Honest stub.

The pilot key-storage tier. Full implementation (hvac against Vault Transit, ML-DSA-65 mechanism) lands with the
Stage-22 pilot. Until then this is an HONEST stub that raises with guidance rather than faking Vault-backed signing
(Rule 1a); the KeyProvider ABC is the real seam — `CRYPTO_PROVIDER=vault` is a config change, no caller edits.
"""
from __future__ import annotations

from typing import Any, Optional

from crypto.key_provider import DEFAULT_ALGORITHM, KeyProvider

_MSG = ("VaultTransitProvider is not yet wired (Stage 22 pilot). Set CRYPTO_PROVIDER=software for the dev ML-DSA-65 "
        "signer, or wire VAULT_ADDR/VAULT_TOKEN + hvac against a Vault Transit engine.")


class VaultTransitProvider(KeyProvider):
    def __init__(self) -> None:
        raise NotImplementedError(_MSG)

    def generate_keypair(self, alias: str, algorithm: str = DEFAULT_ALGORITHM) -> int: raise NotImplementedError(_MSG)
    def sign(self, alias: str, data: bytes) -> bytes: raise NotImplementedError(_MSG)
    def verify(self, public_key: bytes, data: bytes, sig: bytes, algorithm: str = DEFAULT_ALGORITHM) -> bool: raise NotImplementedError(_MSG)
    def public_key(self, alias: str, version: Optional[int] = None) -> bytes: raise NotImplementedError(_MSG)
    def active_version(self, alias: str) -> int: raise NotImplementedError(_MSG)
    def rotate(self, alias: str) -> int: raise NotImplementedError(_MSG)
    def capabilities(self) -> dict[str, Any]: raise NotImplementedError(_MSG)


__all__ = ["VaultTransitProvider"]
