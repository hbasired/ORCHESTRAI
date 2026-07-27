"""langgraph checkpoints — durable LangGraph runtime persistence (Stage 11)

Revision ID: 0002_langgraph_checkpoints
Revises: 0001_init
Create Date: 2026-06-14 00:00:00.000000

Stage 11 (2026-06-14) — durable agent runtime. The LangGraph `PostgresSaver` writes one checkpoint per graph
super-step (keyed by `thread_id`), so a self-healing run can pause at HITL and resume across process boundaries —
the EU-AI-Act Art-12 audit/resumability path. The checkpointer manages its OWN schema (tables `checkpoints`,
`checkpoint_writes`, `checkpoint_blobs`, `checkpoint_migrations`); we invoke its idempotent `setup()` here so those
tables join the project's alembic chain rather than being created ad-hoc at first run.

Naming note: chained from `0001_init` (stages 2–5 added no migrations, so this is the real next revision; the task
doc's "0006" name assumed intervening migrations that were never created).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import op

revision = "0002_langgraph_checkpoints"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use the live alembic connection's DSN so the checkpoint tables land in the SAME database.
    url = op.get_bind().engine.url.render_as_string(hide_password=False)
    # langgraph's PostgresSaver expects a psycopg (libpq) DSN, not the SQLAlchemy +asyncpg driver form.
    dsn = (url.replace("postgresql+asyncpg://", "postgresql://")
              .replace("postgresql+psycopg://", "postgresql://"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/ on path
    try:
        from agents.runtime.checkpointer import setup_postgres_checkpointer
        ok = setup_postgres_checkpointer(dsn)
        if not ok:
            print("WARN 0002_langgraph_checkpoints: PostgresSaver.setup() could not run "
                  "(package/DB unavailable). The runtime falls back to in-memory until Postgres is reachable; "
                  "re-run `alembic upgrade head` once Postgres is up to create the checkpoint tables.")
    except Exception as e:  # never hard-fail the migration chain on the checkpointer
        print(f"WARN 0002_langgraph_checkpoints: checkpoint setup skipped ({e}).")


def downgrade() -> None:
    # Drop the langgraph-managed checkpoint tables (best-effort; they are runtime state, not domain data).
    for tbl in ("checkpoint_writes", "checkpoint_blobs", "checkpoints", "checkpoint_migrations"):
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
