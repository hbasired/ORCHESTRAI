"""isa95_metadata — relational mirror of the Neo4j ISA-95 graph (Stage 12)

Revision ID: 0004_isa95_metadata
Revises: 0003_audit_chain
Create Date: 2026-06-15 00:00:00.000000

Stage 12 (2026-06-15) — KB_14 §"Neo4j ISA-95 schema". The equipment hierarchy lives in Neo4j (Cypher is better for
hierarchy queries); this PG table is the relational MIRROR for SQL joins that need ISA-95 context alongside
`decisions` / `audit_chain` / `mem0_memories` without crossing to the graph. `graph_isa95.py` keeps the two in sync
(graph = source of truth; this mirror is derived). `isa95_class` is one of the ISA-95 Part 2 object classes
(Enterprise/Site/Area/WorkCenter/WorkUnit/EquipmentClass/Equipment/…).
"""
from __future__ import annotations

from alembic import op

revision = "0004_isa95_metadata"
down_revision = "0003_audit_chain"
branch_labels = None
depends_on = None

_CLASSES = (
    "Enterprise", "Site", "Area", "WorkCenter", "WorkUnit",
    "EquipmentClass", "Equipment", "MaterialClass", "MaterialLot", "MaterialSublot",
    "ProcessSegment", "OperationsDefinition", "OperationsRequest", "OperationsResponse",
    "Personnel", "PersonnelClass",
)


def upgrade() -> None:
    classes_sql = ", ".join(f"'{c}'" for c in _CLASSES)
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS isa95_metadata (
          id           text PRIMARY KEY,                 -- stable id shared with the Neo4j node
          isa95_class  text NOT NULL CHECK (isa95_class IN ({classes_sql})),
          name         text NOT NULL,
          parent_id    text REFERENCES isa95_metadata (id) ON DELETE SET NULL,
          attributes   jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at   timestamptz NOT NULL DEFAULT now(),
          updated_at   timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS isa95_metadata_class ON isa95_metadata (isa95_class);")
    op.execute("CREATE INDEX IF NOT EXISTS isa95_metadata_parent ON isa95_metadata (parent_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS isa95_metadata CASCADE;")
