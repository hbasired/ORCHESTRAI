"""mem0_memories row-level security — DB-enforced namespace isolation (Stage 19, CTO #3 G-073-adjacent)

Revision ID: 0008_mem0_rls
Revises: 0007_a2a_peers
Create Date: 2026-06-21 00:00:00.000000

Defense-in-depth BEHIND `mem0_adapter._authorize()` (the Python gate stays the first line; KB_14 §7). Postgres
**FORCE ROW LEVEL SECURITY** filters every SELECT/INSERT/UPDATE/DELETE on `mem0_memories` by the per-session
`app.mem0_namespace` setting — so even a direct SQL client (or a code path that forgot `_authorize`) sees ONLY the
namespace it set, and **NOTHING** if it set nothing (fail-closed). The adapter `set_config`s the bound namespace per
op; the trusted retention sweep sets the `*ALL*` escape. FORCE makes RLS apply to the table owner too (the app connects
as the owner). DDL is not subject to RLS, so migrations are unaffected.
"""
from __future__ import annotations

from alembic import op

revision = "0008_mem0_rls"
down_revision = "0007_a2a_peers"
branch_labels = None
depends_on = None

_POLICY = "mem0_namespace_isolation"


def upgrade() -> None:
    op.execute("ALTER TABLE mem0_memories ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE mem0_memories FORCE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        CREATE POLICY {_POLICY} ON mem0_memories
          USING (namespace = current_setting('app.mem0_namespace', true)
                 OR current_setting('app.mem0_namespace', true) = '*ALL*')
          WITH CHECK (namespace = current_setting('app.mem0_namespace', true)
                      OR current_setting('app.mem0_namespace', true) = '*ALL*');
        """
    )
    # The app connects as a SUPERUSER (compose default), which BYPASSES RLS even with FORCE. So create a
    # NON-superuser role the adapter drops to (`SET ROLE mem0_app`) per op — only then is RLS actually enforced.
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
    op.execute("GRANT USAGE ON SCHEMA public TO mem0_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON mem0_memories TO mem0_app;")


def _drop_role() -> None:
    # Idempotent: only revoke/drop if the role exists (a downgrade before the role was ever created must not error).
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mem0_app') THEN
            REVOKE ALL ON mem0_memories FROM mem0_app;
            REVOKE USAGE ON SCHEMA public FROM mem0_app;
            DROP ROLE mem0_app;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {_POLICY} ON mem0_memories;")
    op.execute("ALTER TABLE mem0_memories NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE mem0_memories DISABLE ROW LEVEL SECURITY;")
    _drop_role()
