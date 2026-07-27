"""Stage 14 — A2A revocation list (KB_16 §"Revocation").

Polls a configurable URL (default `A2A_REVOCATION_URL`) on a 5-minute cycle, caches the revoked public-key set, and
`is_revoked(public_key_b64)` checks it BEFORE signature verification (KB_16). Honest fail-safe: an unreachable list
keeps the LAST cached set (never silently clears a known-revoked key); a `revoke()`/local set supports tests + local
revocations. Background poller uses a bounded thread with clean shutdown (the Stage-11/13 lesson).
"""
from __future__ import annotations

import json
import os
import threading
from typing import Optional


class RevocationList:
    def __init__(self, url: Optional[str] = None, poll_seconds: float = 300.0) -> None:
        self._url = url or os.environ.get("A2A_REVOCATION_URL")
        self._poll_seconds = poll_seconds
        self._revoked: set[str] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def is_revoked(self, public_key_b64: str) -> bool:
        with self._lock:
            return public_key_b64 in self._revoked

    def revoke(self, public_key_b64: str) -> None:
        """Local revocation (also used by tests + operator action)."""
        with self._lock:
            self._revoked.add(public_key_b64)

    def load_once(self) -> int:
        """Fetch the revocation list from the URL (if any) + MERGE into the cache. Returns the cache size.
        Fail-safe: on error the cache is unchanged (a known-revoked key is never dropped)."""
        if not self._url:
            return len(self._revoked)
        try:
            import httpx
            resp = httpx.get(self._url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            keys = data.get("revoked", data) if isinstance(data, dict) else data
            with self._lock:
                self._revoked.update(str(k) for k in keys)
        except Exception:  # noqa: BLE001 - keep the last cached set; do not clear on failure
            pass
        with self._lock:
            return len(self._revoked)

    def start_polling(self) -> None:
        if self._thread is not None or not self._url:
            return
        self._stop.clear()
        self.load_once()

        def _loop() -> None:
            while not self._stop.wait(self._poll_seconds):
                self.load_once()

        self._thread = threading.Thread(target=_loop, name="a2a-revocation", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None


_revocation: Optional[RevocationList] = None


def get_revocation_list() -> RevocationList:
    global _revocation
    if _revocation is None:
        _revocation = RevocationList()
    return _revocation


__all__ = ["RevocationList", "get_revocation_list"]
