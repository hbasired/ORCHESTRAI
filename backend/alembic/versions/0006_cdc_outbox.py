"""cdc_outbox — transactional-outbox CDC for DB-driven incident injection (Stage 13)

Revision ID: 0006_cdc_outbox
Revises: 0005_mem0
Create Date: 2026-06-15 00:00:00.000000

Stage 13 (2026-06-15) — "a DB write triggers agent reasoning" (KB_05 §97, KB_25 bidirectional, PRD v3 dynamic
operator features, G-023). Research §22: the transactional-outbox pattern (durable + ordered + transactional) +
LISTEN/NOTIFY as the low-latency signal — the research-endorsed robust self-hosted CDC for our single-Postgres,
free-cost constraint (Debezium is EOL 2026-03; Supabase Realtime is a heavy Elixir server; test_decoding is
"avoid in prod"; pgoutput needs fragile from-scratch binary parsing; wal2json isn't in the image).

A trigger on `incidents` (INSERT) and `stages` (UPDATE OF status) writes a JSON change event into the durable
`cdc_outbox` within the SAME transaction, then `pg_notify('cdc_events', <outbox id>)`. The backend `cdc_listener`
LISTENs + drains the outbox (catching anything missed while it was offline) and converts each change to a SimWorld
inject. pgoutput-based WAL logical replication (for streaming to a non-PG sink at scale) is a future stage.
"""
from __future__ import annotations

from alembic import op

revision = "0006_cdc_outbox"
down_revision = "0005_mem0"
branch_labels = None
depends_on = None

CDC_CHANNEL = "cdc_events"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cdc_outbox (
          id            bigserial PRIMARY KEY,
          table_name    text NOT NULL,
          op            text NOT NULL,          -- INSERT | UPDATE
          row_pk        text NOT NULL,          -- primary key of the changed row (text-encoded)
          change        jsonb NOT NULL,         -- the change event (row diff)
          created_at    timestamptz NOT NULL DEFAULT now(),
          processed_at  timestamptz             -- NULL until the listener converts it to an inject
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS cdc_outbox_unprocessed ON cdc_outbox (id) WHERE processed_at IS NULL;")

    # Trigger fn: build the change event, write the durable outbox row, then NOTIFY the new id as the low-latency
    # signal. Runs inside the writing transaction → the outbox row commits atomically with the change.
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION cdc_emit() RETURNS trigger AS $$
        DECLARE
          ev     jsonb;
          pk     text;
          obx_id bigint;
        BEGIN
          IF TG_TABLE_NAME = 'incidents' AND TG_OP = 'INSERT' THEN
            pk := NEW.incident_id::text;
            ev := jsonb_build_object(
                    'type', NEW.type, 'target_id', NEW.target_id,
                    'details', COALESCE(NEW.details, '{{}}'::jsonb), 'severity', NEW.severity);
          ELSIF TG_TABLE_NAME = 'stages' AND TG_OP = 'UPDATE' THEN
            -- only emit when status actually changed (the trigger is also scoped to OF status)
            IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
              RETURN NEW;
            END IF;
            pk := NEW.id::text;
            ev := jsonb_build_object(
                    'stage_id', NEW.id, 'name', NEW.name,
                    'old_status', OLD.status, 'new_status', NEW.status);
          ELSE
            RETURN NEW;
          END IF;

          INSERT INTO cdc_outbox (table_name, op, row_pk, change)
            VALUES (TG_TABLE_NAME, TG_OP, pk, ev)
            RETURNING id INTO obx_id;
          PERFORM pg_notify('{CDC_CHANNEL}', obx_id::text);
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS cdc_incidents_insert ON incidents;")
    op.execute("CREATE TRIGGER cdc_incidents_insert AFTER INSERT ON incidents "
               "FOR EACH ROW EXECUTE FUNCTION cdc_emit();")
    op.execute("DROP TRIGGER IF EXISTS cdc_stages_status_update ON stages;")
    op.execute("CREATE TRIGGER cdc_stages_status_update AFTER UPDATE OF status ON stages "
               "FOR EACH ROW EXECUTE FUNCTION cdc_emit();")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cdc_incidents_insert ON incidents;")
    op.execute("DROP TRIGGER IF EXISTS cdc_stages_status_update ON stages;")
    op.execute("DROP FUNCTION IF EXISTS cdc_emit();")
    op.execute("DROP TABLE IF EXISTS cdc_outbox CASCADE;")
