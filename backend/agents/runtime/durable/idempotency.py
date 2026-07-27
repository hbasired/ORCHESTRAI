"""Stage 27 — the effect ledger: at-most-once external effects with replay-returns (research §38.3).

Sourced pattern: a (key, response) table with a uniqueness constraint; "if you see this key again, return the
cached response". Three states per key: RUNNING (claimed, in flight), DONE (response recorded), FAILED (released —
retryable). A crash between claim and completion leaves RUNNING; `reclaim_stale()` releases claims older than a
lease so a crashed worker's effect can retry (the caller decides retry policy).

Honesty: with no DB the ledger degrades to an in-PROCESS dict (correct within one process; cross-process
at-most-once REQUIRES the DB — stated, same as the Stage-25 shard-router fallback).
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Optional

_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS effect_ledger (
  key         text PRIMARY KEY,
  state       text NOT NULL CHECK (state IN ('RUNNING', 'DONE')),
  response    jsonb,
  claimed_at  timestamptz NOT NULL DEFAULT now(),
  done_at     timestamptz
)"""


class EffectAlreadyDone(Exception):
    """Raised by `claim()` when the effect already completed — carries the recorded response."""

    def __init__(self, key: str, response: Any):
        super().__init__(f"effect {key!r} already done")
        self.key = key
        self.response = response


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


class EffectLedger:
    """At-most-once effect execution: claim(key) → run the effect → complete(key, response) | release(key)."""

    def __init__(self):
        self._local: dict[str, tuple[str, Any]] = {}
        self._mu = threading.Lock()
        self._table_ready = False

    def _conn(self):
        dsn = _dsn()
        if not dsn:
            return None
        try:
            import psycopg
            conn = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
            if not self._table_ready:
                with conn.cursor() as cur:
                    cur.execute(_TABLE_SQL)
                self._table_ready = True
            return conn
        except Exception:  # noqa: BLE001 — DB down: honest in-process fallback
            return None

    def claim(self, key: str) -> bool:
        """True = claimed (run the effect). False = another worker is RUNNING it right now.
        Raises EffectAlreadyDone (with the recorded response) if it already completed."""
        conn = self._conn()
        if conn is None:
            with self._mu:
                state = self._local.get(key)
                if state is None:
                    self._local[key] = ("RUNNING", None)
                    return True
                if state[0] == "DONE":
                    raise EffectAlreadyDone(key, state[1])
                return False
        with conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO effect_ledger (key, state) VALUES (%s, 'RUNNING') "
                            "ON CONFLICT (key) DO NOTHING", (key,))
                if cur.rowcount == 1:
                    return True
                cur.execute("SELECT state, response FROM effect_ledger WHERE key = %s", (key,))
                row = cur.fetchone()
                if row and row[0] == "DONE":
                    raise EffectAlreadyDone(key, row[1])
                return False

    def complete(self, key: str, response: Any = None) -> None:
        """Record the effect's outcome; future claims raise EffectAlreadyDone with this response."""
        conn = self._conn()
        if conn is None:
            with self._mu:
                self._local[key] = ("DONE", response)
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE effect_ledger SET state = 'DONE', response = %s, done_at = now() "
                            "WHERE key = %s", (json.dumps(response), key))

    def release(self, key: str) -> None:
        """The effect FAILED before completing — release the claim so a retry can re-claim."""
        conn = self._conn()
        if conn is None:
            with self._mu:
                if self._local.get(key, ("", None))[0] == "RUNNING":
                    del self._local[key]
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM effect_ledger WHERE key = %s AND state = 'RUNNING'", (key,))

    def reclaim_stale(self, lease_seconds: float = 600.0) -> int:
        """Release RUNNING claims older than the lease (a crashed worker's orphans). Returns count released."""
        conn = self._conn()
        if conn is None:
            return 0  # in-process claims die with the process — nothing to reclaim
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM effect_ledger WHERE state = 'RUNNING' "
                            "AND claimed_at < now() - make_interval(secs => %s)", (lease_seconds,))
                return cur.rowcount


__all__ = ["EffectLedger", "EffectAlreadyDone"]
