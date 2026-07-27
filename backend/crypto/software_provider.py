"""Stage 13.5 — SoftwareKeyProvider: real FIPS-204 ML-DSA-65 via `dilithium-py` + a filesystem keystore.

The dev/no-budget tier of KB_13's KeyProvider abstraction. Produces REAL, verifiable ML-DSA-65 signatures (FIPS-204
parameter sizes pk=1952/sk=4032/sig=3309), Windows-native, no liboqs build. Honest caveat (the library's own): the
pure-Python impl is NOT constant-time / side-channel-hardened — that is acceptable here BECAUSE this is the dev/
no-budget tier; production swaps to the `pkcs11` (HSM) or `vault` provider via `CRYPTO_PROVIDER` (config only), where
signing runs in hardened hardware. Keys are versioned per alias (overlap rotation + historical verification); the
private keys live in a gitignored keystore dir (software-tier only — HSM keys never touch the filesystem).
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Optional

from crypto.key_provider import DEFAULT_ALGORITHM, KeyProvider

_SUPPORTED = {"ML-DSA-65"}


def _keystore_dir() -> Path:
    d = os.environ.get("KEY_STORE_DIR")
    base = Path(d) if d else Path(__file__).resolve().parent / ".keystore"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _mldsa():
    from dilithium_py.ml_dsa import ML_DSA_65
    return ML_DSA_65


class SoftwareKeyProvider(KeyProvider):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._root = _keystore_dir()

    # ---- keystore layout: <root>/<alias>/v<N>.sk + v<N>.pk -----------------

    @staticmethod
    def _safe_alias(alias: str) -> str:
        """Map an arbitrary logical alias to a filesystem-safe directory name (Windows forbids : \\ / * ? \" < > |).
        Existing aliases (e.g. `agent-identity`) are unchanged; `agent:embodied` -> `agent_embodied`."""
        safe = alias
        for ch in ':\\/*?"<>|':
            safe = safe.replace(ch, "_")
        return safe

    def _alias_dir(self, alias: str) -> Path:
        d = self._root / self._safe_alias(alias)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _versions(self, alias: str) -> list[int]:
        d = self._alias_dir(alias)
        return sorted(int(p.stem[1:]) for p in d.glob("v*.pk") if p.stem[1:].isdigit())

    def _write_key(self, alias: str, version: int, pk: bytes, sk: bytes) -> None:
        d = self._alias_dir(alias)
        (d / f"v{version}.pk").write_bytes(pk)
        sk_path = d / f"v{version}.sk"
        sk_path.write_bytes(sk)
        try:
            os.chmod(sk_path, 0o600)  # best-effort (limited on Windows); software-tier secret
        except Exception:  # noqa: BLE001
            pass

    # ---- KeyProvider surface ------------------------------------------------

    def generate_keypair(self, alias: str, algorithm: str = DEFAULT_ALGORITHM) -> int:
        if algorithm not in _SUPPORTED:
            raise ValueError(f"SoftwareKeyProvider supports {_SUPPORTED}, not {algorithm!r}")
        with self._lock:
            versions = self._versions(alias)
            if versions:
                return versions[-1]
            pk, sk = _mldsa().keygen()
            self._write_key(alias, 1, pk, sk)
            return 1

    def active_version(self, alias: str) -> int:
        with self._lock:
            versions = self._versions(alias)
        if versions:
            return versions[-1]
        return self.generate_keypair(alias)  # first use → v1

    def sign(self, alias: str, data: bytes) -> bytes:
        version = self.active_version(alias)
        with self._lock:
            sk = (self._alias_dir(alias) / f"v{version}.sk").read_bytes()
        return _mldsa().sign(sk, data)

    def verify(self, public_key: bytes, data: bytes, sig: bytes, algorithm: str = DEFAULT_ALGORITHM) -> bool:
        if algorithm not in _SUPPORTED:
            raise ValueError(f"unsupported algorithm {algorithm!r}")
        try:
            return bool(_mldsa().verify(public_key, data, sig))
        except Exception:  # noqa: BLE001 - a malformed key/sig is a verification failure, not a crash
            return False

    def public_key(self, alias: str, version: Optional[int] = None) -> bytes:
        v = version if version is not None else self.active_version(alias)
        path = self._alias_dir(alias) / f"v{v}.pk"
        if not path.exists():
            raise KeyError(f"no public key for {alias!r} v{v}")
        return path.read_bytes()

    def rotate(self, alias: str) -> int:
        with self._lock:
            versions = self._versions(alias)
            new_v = (versions[-1] if versions else 0) + 1
            pk, sk = _mldsa().keygen()
            self._write_key(alias, new_v, pk, sk)
            return new_v

    def capabilities(self) -> dict[str, Any]:
        return {"backend": "software:dilithium-py", "supported_algorithms": sorted(_SUPPORTED),
                "fips_level": "FIPS-204 algorithm; software (not side-channel-hardened) — dev/no-budget tier",
                "attestation": False}


__all__ = ["SoftwareKeyProvider"]
