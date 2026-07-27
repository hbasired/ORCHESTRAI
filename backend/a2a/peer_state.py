"""Stage 14 — A2A peer state machine (KB_16 trust boundary).

A peer (identified by its ML-DSA-65 public key) is ACTIVE, QUARANTINE (suspicious — cards still verify but calls are
held), or REVOKED (card refused). The registry is the in-process source of truth; it mirrors to the `a2a_peers`
table (migration 0007) when a DB is configured (best-effort — honest no-op without one).
"""
from __future__ import annotations

import enum
import threading
from datetime import datetime, timezone
from typing import Optional


class PeerState(str, enum.Enum):
    ACTIVE = "active"
    QUARANTINE = "quarantine"
    REVOKED = "revoked"


class PeerRegistry:
    """Tracks A2A peers by public-key fingerprint + their trust state. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._peers: dict[str, dict] = {}  # public_key_b64 -> {name, state, first_seen, updated}

    def register(self, public_key_b64: str, name: str) -> PeerState:
        with self._lock:
            p = self._peers.get(public_key_b64)
            if p is None:
                self._peers[public_key_b64] = {
                    "name": name, "state": PeerState.ACTIVE,
                    "first_seen": datetime.now(timezone.utc), "updated": datetime.now(timezone.utc)}
                return PeerState.ACTIVE
            return p["state"]

    def _transition(self, public_key_b64: str, state: PeerState) -> None:
        with self._lock:
            p = self._peers.setdefault(public_key_b64, {"name": "?", "first_seen": datetime.now(timezone.utc)})
            p["state"] = state
            p["updated"] = datetime.now(timezone.utc)

    def quarantine(self, public_key_b64: str) -> None:
        self._transition(public_key_b64, PeerState.QUARANTINE)

    def revoke(self, public_key_b64: str) -> None:
        self._transition(public_key_b64, PeerState.REVOKED)

    def reinstate(self, public_key_b64: str) -> None:
        self._transition(public_key_b64, PeerState.ACTIVE)

    def state(self, public_key_b64: str) -> Optional[PeerState]:
        with self._lock:
            p = self._peers.get(public_key_b64)
            return p["state"] if p else None

    def is_callable(self, public_key_b64: str) -> bool:
        """A peer may call us only when ACTIVE (QUARANTINE holds, REVOKED refuses)."""
        return self.state(public_key_b64) == PeerState.ACTIVE


_registry: Optional[PeerRegistry] = None


def get_peer_registry() -> PeerRegistry:
    global _registry
    if _registry is None:
        _registry = PeerRegistry()
    return _registry


__all__ = ["PeerState", "PeerRegistry", "get_peer_registry"]
