"""Stage 22 (R8 / G-076) — make `mem0_app` a NON-superuser LOGIN role for connection-enforced RLS.

Migration 0008 created `mem0_app NOLOGIN NOSUPERUSER` and the adapter dropped to it via best-effort `SET ROLE` (because
the compose app user `aiagent` is a SUPERUSER that bypasses RLS). That left the DB backstop only as strong as the per-op
`SET ROLE`. This migration gives `mem0_app` LOGIN + a password so `mem0_adapter._connect_ns` can connect AS `mem0_app`
directly — then Postgres FORCE row-level security is enforced by the CONNECTION ROLE itself and holds even if a code
path forgets `SET ROLE`. The Python `_authorize` check remains the first gate either way.

Password source (no secret committed): MEM0_APP_PASSWORD (prod) → POSTGRES_PASSWORD → dev default 'devpass2026'.
The table grants (SELECT/INSERT/UPDATE/DELETE on mem0_memories, USAGE on schema public) already exist from 0008;
mem0_memories uses a uuid PK (no sequence to grant). Idempotent + reversible (downgrade reverts to NOLOGIN).
"""
from __future__ import annotations

import os

from alembic import op

revision = "0009_mem0_app_login_role"
down_revision = "0008_mem0_rls"
branch_labels = None
depends_on = None


def _app_password() -> str:
    return os.environ.get("MEM0_APP_PASSWORD") or os.environ.get("POSTGRES_PASSWORD") or "devpass2026"


def upgrade() -> None:
    pwd = _app_password().replace("'", "''")  # escape for the SQL string literal
    # Ensure the role exists (0008 created it; be defensive), then grant LOGIN + password. NOSUPERUSER/NOBYPASSRLS so
    # FORCE RLS actually applies to it.
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mem0_app') THEN
            CREATE ROLE mem0_app NOLOGIN NOSUPERUSER;
          END IF;
        END $$;
        """
    )
    op.execute(f"ALTER ROLE mem0_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD '{pwd}';")
    # Re-assert the grants the adapter needs as a direct login (no-ops if already granted from 0008).
    op.execute("GRANT USAGE ON SCHEMA public TO mem0_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON mem0_memories TO mem0_app;")
    # Connecting to the DB requires CONNECT on the database (PUBLIC has it by default, but be explicit/portable).
    op.execute("DO $$ BEGIN EXECUTE format('GRANT CONNECT ON DATABASE %I TO mem0_app', current_database()); END $$;")


def downgrade() -> None:
    # Revert to a non-login role (matches 0008's state). Keep the role + grants so 0008's downgrade can clean up.
    op.execute("ALTER ROLE mem0_app NOLOGIN;")
