"""cdc value-change triggers — bidirectional CDC self-optimize (Stage 37 / G-024)

Extends the Stage-13 CDC (0006) so an operator's edit of an operational VALUE column (a stage's defect_rate /
throughput / energy / utilization, an inventory level, a supplier's reliability / lead-time) emits a value-change
event into `cdc_outbox`. The backend `cdc_listener` then routes it through `cdc_reasoner.diagnose_change` — DIAGNOSING
the induced problem (root-cause) rather than mapping to a canned incident — and drives the self-healing loop. Closes
the CDC loop the other way (research §48.1).

Revision ID: 0010_cdc_value_changes
Revises: 0009_mem0_app_login_role
"""
from alembic import op

revision = "0010_cdc_value_changes"
down_revision = "0009_mem0_app_login_role"
branch_labels = None
depends_on = None

CDC_CHANNEL = "cdc_events"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION cdc_emit_value() RETURNS trigger AS $$
        DECLARE
          ev     jsonb;
          obx_id bigint;
          col    text := NULL;
          oldv   double precision := NULL;
          newv   double precision := NULL;
          tid    integer := NULL;
        BEGIN
          IF TG_TABLE_NAME = 'stages' THEN
            tid := NEW.id;
            IF NEW.defect_rate IS DISTINCT FROM OLD.defect_rate THEN
              col := 'defect_rate'; oldv := OLD.defect_rate; newv := NEW.defect_rate;
            ELSIF NEW.throughput IS DISTINCT FROM OLD.throughput THEN
              col := 'throughput'; oldv := OLD.throughput; newv := NEW.throughput;
            ELSIF NEW.energy_consumption_kw IS DISTINCT FROM OLD.energy_consumption_kw THEN
              col := 'energy_consumption_kw'; oldv := OLD.energy_consumption_kw; newv := NEW.energy_consumption_kw;
            ELSIF NEW.utilization IS DISTINCT FROM OLD.utilization THEN
              col := 'utilization'; oldv := OLD.utilization; newv := NEW.utilization;
            END IF;
          ELSIF TG_TABLE_NAME = 'inventory' THEN
            tid := NEW.id;
            IF NEW.current_stock IS DISTINCT FROM OLD.current_stock THEN
              col := 'current_stock'; oldv := OLD.current_stock; newv := NEW.current_stock;
            ELSIF NEW.days_of_supply IS DISTINCT FROM OLD.days_of_supply THEN
              col := 'days_of_supply'; oldv := OLD.days_of_supply; newv := NEW.days_of_supply;
            END IF;
          ELSIF TG_TABLE_NAME = 'suppliers' THEN
            tid := NEW.id;
            IF NEW.reliability_score IS DISTINCT FROM OLD.reliability_score THEN
              col := 'reliability_score'; oldv := OLD.reliability_score; newv := NEW.reliability_score;
            ELSIF NEW.lead_time_days IS DISTINCT FROM OLD.lead_time_days THEN
              col := 'lead_time_days'; oldv := OLD.lead_time_days; newv := NEW.lead_time_days;
            END IF;
          END IF;

          IF col IS NULL THEN
            RETURN NEW;                       -- no monitored value column changed
          END IF;

          ev := jsonb_build_object('table', TG_TABLE_NAME, 'column', col,
                                   'old', oldv, 'new', newv, 'target_id', tid);
          INSERT INTO cdc_outbox (table_name, op, row_pk, change)
            VALUES (TG_TABLE_NAME, TG_OP, tid::text, ev)
            RETURNING id INTO obx_id;
          PERFORM pg_notify('{CDC_CHANNEL}', obx_id::text);
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS cdc_stages_value_update ON stages;")
    op.execute("CREATE TRIGGER cdc_stages_value_update AFTER UPDATE OF defect_rate, throughput, "
               "energy_consumption_kw, utilization ON stages FOR EACH ROW EXECUTE FUNCTION cdc_emit_value();")
    op.execute("DROP TRIGGER IF EXISTS cdc_inventory_value_update ON inventory;")
    op.execute("CREATE TRIGGER cdc_inventory_value_update AFTER UPDATE OF current_stock, days_of_supply "
               "ON inventory FOR EACH ROW EXECUTE FUNCTION cdc_emit_value();")
    op.execute("DROP TRIGGER IF EXISTS cdc_suppliers_value_update ON suppliers;")
    op.execute("CREATE TRIGGER cdc_suppliers_value_update AFTER UPDATE OF reliability_score, lead_time_days "
               "ON suppliers FOR EACH ROW EXECUTE FUNCTION cdc_emit_value();")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cdc_stages_value_update ON stages;")
    op.execute("DROP TRIGGER IF EXISTS cdc_inventory_value_update ON inventory;")
    op.execute("DROP TRIGGER IF EXISTS cdc_suppliers_value_update ON suppliers;")
    op.execute("DROP FUNCTION IF EXISTS cdc_emit_value();")
