"""Stage 13.5 — the abstract KeyProvider boundary + factory (KB_13 §"Pluggable KeyProvider / PKCS#11 HSM boundary").

ONE abstract surface for key generation/signing/verification/rotation. Selection is by config only —
`CRYPTO_PROVIDER ∈ {software, pkcs11, vault}` — so buying an HSM is a config change, not a code change. No caller in
`backend/` imports a concrete provider; they call `get_key_provider()`.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Optional

DEFAULT_ALGORITHM = "ML-DSA-65"


class KeyProvider(ABC):
    """Abstract key/signing provider. Concrete backends: software (dilithium-py), pkcs11 (HSM), vault."""

    @abstractmethod
    def generate_keypair(self, alias: str, algorithm: str = DEFAULT_ALGORITHM) -> int:
        """Create the first keypair version for `alias` if absent. Returns the version (>=1)."""

    @abstractmethod
    def sign(self, alias: str, data: bytes) -> bytes:
        """Sign `data` with the ACTIVE key version of `alias`. Raises if the algorithm is unsupported."""

    @abstractmethod
    def verify(self, public_key: bytes, data: bytes, sig: bytes, algorithm: str = DEFAULT_ALGORITHM) -> bool:
        """Verify `sig` over `data` under `public_key`. Pure (no alias) so historical/peer keys verify."""

    @abstractmethod
    def public_key(self, alias: str, version: Optional[int] = None) -> bytes:
        """Public key bytes for `alias` (active version if `version` is None)."""

    @abstractmethod
    def active_version(self, alias: str) -> int:
        """Active (highest) key version for `alias`, generating v1 on first use."""

    @abstractmethod
    def rotate(self, alias: str) -> int:
        """Generate the next key version for `alias` (overlap rotation — old versions kept for verification).
        Returns the new active version."""

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """{supported_algorithms, fips_level, attestation, backend} — for the A2A agent card + audits."""


_provider_singleton: Optional[KeyProvider] = None


def get_key_provider() -> KeyProvider:
    """Return the configured KeyProvider singleton. `CRYPTO_PROVIDER` selects the backend (default: software)."""
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton
    backend = os.environ.get("CRYPTO_PROVIDER", "software").lower()
    if backend == "software":
        from crypto.software_provider import SoftwareKeyProvider
        _provider_singleton = SoftwareKeyProvider()
    elif backend == "pkcs11":
        from crypto.pkcs11_provider import Pkcs11KeyProvider  # honest stub until SoftHSM/HSM is wired
        _provider_singleton = Pkcs11KeyProvider()
    elif backend == "vault":
        from crypto.vault_provider import VaultTransitProvider  # honest stub until Vault is wired
        _provider_singleton = VaultTransitProvider()
    else:
        raise ValueError(f"unknown CRYPTO_PROVIDER {backend!r} (expected software|pkcs11|vault)")
    return _provider_singleton


def _reset_provider_for_tests() -> None:
    """Test hook to re-select the provider after changing CRYPTO_PROVIDER."""
    global _provider_singleton
    _provider_singleton = None


__all__ = ["KeyProvider", "get_key_provider", "DEFAULT_ALGORITHM"]
