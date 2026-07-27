"""Stage 35 (C6-R3 tail) — durable multi-turn dialogue memory for the conversational endpoints (research §46).

A SLIDING-WINDOW (last-N-turns) conversation store, keyed by `session_id`, persisted in Postgres so a session
survives a restart. It lets `/factory/ask` and `/factory/inject` be multi-turn (coreference: "and what did we do
about it?") WITHOUT ever weakening the Stage-29 grounding/Verifier invariant — history helps the LLM PHRASE and
RESOLVE COREFERENCE; each answer's EVIDENCE is still gathered per-current-question, and honest-empty still fires when
nothing grounds it. Prior turns are NEVER cited as evidence.

Honest-degrading: if Postgres is unreachable, `recent_turns` returns `[]` and `append_turn` is a no-op — the
endpoints simply behave single-turn (never fabricate a history). No new deps (psycopg present). Sliding window over
summarization (research §46.1): robust for the typical short operator dialogue, no over-summarization risk.
"""
from __future__ import annotations

import os
from typing import Any, Optional

DEFAULT_WINDOW = 6                 # last N turns fed to the LLM as dialogue context
_MAX_CONTENT = 4000                # clamp a stored turn (defensive)

_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    session_id  TEXT        NOT NULL,
    turn_index  INTEGER     NOT NULL,
    role        TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, turn_index)
);
"""


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def _connect():
    dsn = _dsn()
    if not dsn:
        return None
    try:
        import psycopg
        return psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except Exception:  # noqa: BLE001 - store unavailable -> honest single-turn behaviour
        return None


def append_turn(session_id: str, role: str, content: str) -> bool:
    """Append one turn (role='user'|'assistant'). Returns True if persisted, False if the store is unavailable (no-op)."""
    if not session_id or not role or not content:
        return False
    conn = _connect()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLE_SQL)
            cur.execute("SELECT COALESCE(MAX(turn_index), -1) + 1 FROM conversation_turns WHERE session_id = %s",
                        (session_id,))
            idx = cur.fetchone()[0]
            cur.execute("INSERT INTO conversation_turns (session_id, turn_index, role, content) VALUES (%s,%s,%s,%s)",
                        (session_id, idx, role, str(content)[:_MAX_CONTENT]))
        return True
    except Exception:  # noqa: BLE001 - surfaced as no-op; never fabricated
        return False
    finally:
        conn.close()


def recent_turns(session_id: str, *, window: int = DEFAULT_WINDOW) -> list[dict[str, Any]]:
    """Return the last `window` turns for `session_id`, oldest-first. Empty list if unavailable (honest single-turn)."""
    if not session_id:
        return []
    conn = _connect()
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLE_SQL)
            cur.execute("SELECT role, content, turn_index FROM conversation_turns WHERE session_id = %s "
                        "ORDER BY turn_index DESC LIMIT %s", (session_id, int(max(1, window))))
            rows = cur.fetchall()
        rows.reverse()                                   # chronological
        return [{"role": r, "content": c, "turn_index": i} for (r, c, i) in rows]
    except Exception:  # noqa: BLE001
        return []
    finally:
        conn.close()


def format_history(turns: list[dict[str, Any]]) -> str:
    """Render turns as a compact dialogue-history block for an LLM prompt. Empty string if no history."""
    if not turns:
        return ""
    lines = [f"{t['role'].upper()}: {t['content']}" for t in turns]
    return "DIALOGUE HISTORY (for coreference/phrasing only — NOT evidence):\n" + "\n".join(lines)


__all__ = ["append_turn", "recent_turns", "format_history", "DEFAULT_WINDOW"]
