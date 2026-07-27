"""mem0_memories — pgvector episodic/semantic store (Stage 12)

Revision ID: 0005_mem0
Revises: 0004_isa95_metadata
Create Date: 2026-06-15 00:00:00.000000

Stage 12 (2026-06-15) — KB_14 §"Mem0 schema" + research §19. A direct pgvector-backed episodic/semantic store
(namespace-isolated; cross-namespace reads forbidden in `mem0_adapter.py`). The embedding dimension matches the
active embedder via `MEM0_EMBED_DIM` (default 1024 = BAAI/bge-large-en-v1.5, the KB default).

Index choice — **HNSW**, not the KB's ivfflat (research §19.2): the store is insert-as-you-go (a memory per
incident/decision), and HNSW handles incremental inserts + needs no training step + has higher recall, whereas
ivfflat must train its lists on existing data and degrades under inserts. `vector_cosine_ops` for cosine similarity.

Requires the `vector` extension — provided by the `pgvector/pgvector:pg15` Postgres image (KB_04 / docker-compose).
If the extension is unavailable the migration raises honestly (no silent skip): pgvector is a hard dependency of the
episodic memory layer.
"""
from __future__ import annotations

import os

from alembic import op

revision = "0005_mem0"
down_revision = "0004_isa95_metadata"
branch_labels = None
depends_on = None


def _embed_dim() -> int:
    try:
        return int(os.environ.get("MEM0_EMBED_DIM", "1024"))
    except ValueError:
        return 1024


def upgrade() -> None:
    dim = _embed_dim()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS mem0_memories (
          id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          namespace       text NOT NULL,
          content         text NOT NULL,
          embedding       vector({dim}) NOT NULL,
          metadata        jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at      timestamptz NOT NULL DEFAULT now(),
          updated_at      timestamptz NOT NULL DEFAULT now(),
          retained_until  timestamptz
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS mem0_memories_ns ON mem0_memories (namespace);")
    op.execute("CREATE INDEX IF NOT EXISTS mem0_memories_retain ON mem0_memories (retained_until);")
    # HNSW cosine index (research §19.2). Built on the (possibly empty) table — no training step.
    op.execute(
        "CREATE INDEX IF NOT EXISTS mem0_memories_vec ON mem0_memories "
        "USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mem0_memories CASCADE;")
    # Leave the `vector` extension installed (other objects may use it; dropping is destructive).
