"""a2a_peers — A2A peer + agent-card storage (Stage 14)

Revision ID: 0007_a2a_peers
Revises: 0006_cdc_outbox
Create Date: 2026-06-15 00:00:00.000000

Stage 14 (KB_16). Persists known A2A peers (by ML-DSA-65 public-key fingerprint), their trust state
(active/quarantine/revoked), and the last agent card we verified from them. The in-process `PeerRegistry`
(`a2a/peer_state.py`) is the runtime source of truth; this table is the durable mirror for restart + audit.

Naming note: the task doc's "0004_a2a_peers" predates the Stage-12/13 migrations; this is the real next revision
(0007), chained from 0006_cdc_outbox.
"""
from __future__ import annotations

from alembic import op

revision = "0007_a2a_peers"
down_revision = "0006_cdc_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS a2a_peers (
          public_key_b64  text PRIMARY KEY,                 -- ML-DSA-65 public key (the peer's identity)
          name            text NOT NULL,
          state           text NOT NULL DEFAULT 'active'
                            CHECK (state IN ('active','quarantine','revoked')),
          last_card       jsonb,                            -- last verified agent card
          first_seen      timestamptz NOT NULL DEFAULT now(),
          updated_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS a2a_peers_state ON a2a_peers (state);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS a2a_peers CASCADE;")
