"""Stage 11 — checkpointer factory for the LangGraph runtime.

Research §17 tiers: MemorySaver (dev) → SqliteSaver (single-server) → PostgresSaver (multi-instance + long-term
audit history, our EU-AI-Act Art-12 need). We return a **pool-backed PostgresSaver** (the documented durable-app
pattern — a long-lived `psycopg_pool.ConnectionPool`, not the scoped `from_conn_string` context manager) when a
Postgres URL is configured + reachable; otherwise MemorySaver, named honestly (no silent pretence of durability).

Verified (2026-06-14) against a clean Postgres: `setup()` creates the checkpoint tables, a graph run persists one
checkpoint per super-step, and a fresh saver instance durably reloads the run. The alembic migration
`0002_langgraph_checkpoints` calls `setup()` so the tables join the project's migration chain.
"""
from __future__ import annotations

import os
from typing import Any, Optional

# psycopg pool kwargs PostgresSaver requires (autocommit + no prepared-stmt caching across the pool).
_PG_CONN_KWARGS = {"autocommit": True, "prepare_threshold": 0}
_pg_pool = None  # module-level, long-lived for the app process


def _postgres_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def get_checkpointer(prefer_postgres: bool = True) -> tuple[Any, str]:
    """Return (checkpointer, backend_name). Honest: names the backend actually in use (no fake durability).

    Postgres path: a pool-backed `PostgresSaver` with the checkpoint tables ensured via `setup()`. Falls back to
    MemorySaver — and SAYS so — if the package/DB is absent or unreachable.
    """
    global _pg_pool
    if prefer_postgres:
        url = _postgres_url()
        if url:
            try:
                from psycopg_pool import ConnectionPool
                from langgraph.checkpoint.postgres import PostgresSaver
                if _pg_pool is None:
                    _pg_pool = ConnectionPool(conninfo=url, max_size=int(os.environ.get("PG_POOL_MAX", "5")),
                                              kwargs=_PG_CONN_KWARGS, open=True)
                cp = PostgresSaver(_pg_pool)
                cp.setup()  # idempotent — creates checkpoint tables if absent
                return cp, "postgres"
            except Exception:
                # package missing / DB unreachable / auth — fall through to in-memory, honestly reported.
                pass
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver(), "memory"


def setup_postgres_checkpointer(url: Optional[str] = None) -> bool:
    """Create the langgraph checkpoint tables (idempotent). Used by the alembic migration + optional startup.
    Returns True on success, False if Postgres is unavailable (honest — never raises into a migration)."""
    url = url or _postgres_url()
    if not url:
        return False
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        with PostgresSaver.from_conn_string(url) as cp:
            cp.setup()
        return True
    except Exception:
        return False


__all__ = ["get_checkpointer", "setup_postgres_checkpointer"]
