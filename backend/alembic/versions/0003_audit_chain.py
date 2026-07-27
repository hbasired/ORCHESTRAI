"""audit_chain — append-only, SHA-256 hash-chained evidence log (Stage 12)

Revision ID: 0003_audit_chain
Revises: 0002_langgraph_checkpoints
Create Date: 2026-06-15 00:00:00.000000

Stage 12 (2026-06-15) — EU AI Act Art. 12 evidence. Every agent/operator decision appends one row whose
`hash = SHA-256(prev_hash || canonical(payload))` (research §19.4, KB_14 §"Audit chain"). BEFORE UPDATE/DELETE
triggers RAISE, so the table is append-only at the DB level (the app role can only INSERT/SELECT). A signature over
the hash gives non-repudiation: Stage 12 writes a STRUCTURALLY-correct placeholder (`algorithm='placeholder-sha256'`,
`key_version=0`); Stage 13.5 swaps in real ML-DSA-65 via `backend/crypto/pqc_signing.py`.

Naming note: the KB_14 "0002_audit_chain" name predates Stage 11's `0002_langgraph_checkpoints`; this is the real
next revision in the chain (0003), chained from 0002.
"""
from __future__ import annotations

from alembic import op

revision = "0003_audit_chain"
down_revision = "0002_langgraph_checkpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_chain (
          seq          bigserial PRIMARY KEY,
          ts           timestamptz NOT NULL DEFAULT now(),
          actor        text NOT NULL,
          action       text NOT NULL,
          payload      jsonb NOT NULL,
          prev_hash    bytea NOT NULL,
          hash         bytea NOT NULL,
          sig_mldsa    bytea NOT NULL,
          key_version  int  NOT NULL DEFAULT 0,
          algorithm    text NOT NULL DEFAULT 'placeholder-sha256'
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS audit_chain_seq_uniq ON audit_chain (seq);")
    op.execute("CREATE INDEX IF NOT EXISTS audit_chain_actor ON audit_chain (actor);")
    op.execute("CREATE INDEX IF NOT EXISTS audit_chain_action ON audit_chain (action);")
    op.execute("CREATE INDEX IF NOT EXISTS audit_chain_ts ON audit_chain (ts DESC);")
    # Append-only enforcement: UPDATE/DELETE raise. The app role inserts + reads only.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_chain_immutable() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'audit_chain is append-only (% blocked)', TG_OP;
        END; $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS no_update ON audit_chain;")
    op.execute("DROP TRIGGER IF EXISTS no_delete ON audit_chain;")
    op.execute(
        "CREATE TRIGGER no_update BEFORE UPDATE ON audit_chain "
        "FOR EACH ROW EXECUTE FUNCTION audit_chain_immutable();"
    )
    op.execute(
        "CREATE TRIGGER no_delete BEFORE DELETE ON audit_chain "
        "FOR EACH ROW EXECUTE FUNCTION audit_chain_immutable();"
    )


def downgrade() -> None:
    # Drop triggers first (they would otherwise block nothing on DROP TABLE, but be explicit).
    op.execute("DROP TRIGGER IF EXISTS no_update ON audit_chain;")
    op.execute("DROP TRIGGER IF EXISTS no_delete ON audit_chain;")
    op.execute("DROP FUNCTION IF EXISTS audit_chain_immutable();")
    op.execute("DROP TABLE IF EXISTS audit_chain CASCADE;")
