"""init — port database/schema.sql + add incidents & decision_logs

Revision ID: 0001_init
Revises:
Create Date: 2026-05-11 00:00:00.000000

Stage 1 (2026-05-11) — first migration. Recreates every table previously
applied by hand from database/schema.sql, plus two new tables required by
KB_04_Data_Schema.md:

  - incidents       : EU AI Act Art. 12 evidence trail for events fired by
                      the simulator or external CDC stream.
  - decision_logs   : per-call ledger for every agent tool invocation;
                      6-month retention is enforced by a cleanup job that
                      ships in Stage 3 (not in this migration).

The earlier database/schema.sql is now archival; do not edit it. All schema
changes from here forward land as new revisions in this folder.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS robots (
            id SERIAL PRIMARY KEY,
            position_x FLOAT NOT NULL DEFAULT 0,
            position_y FLOAT NOT NULL DEFAULT 0,
            battery_pct FLOAT NOT NULL DEFAULT 100 CHECK (battery_pct >= 0 AND battery_pct <= 100),
            speed FLOAT NOT NULL DEFAULT 0 CHECK (speed >= 0),
            task TEXT,
            destination_x FLOAT,
            destination_y FLOAT,
            status VARCHAR(20) NOT NULL DEFAULT 'idle'
                CHECK (status IN ('idle', 'working', 'charging', 'warning', 'error')),
            task_queue_length INT NOT NULL DEFAULT 0 CHECK (task_queue_length >= 0),
            detection_confidence FLOAT,
            last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_robots_status ON robots(status);
        CREATE INDEX IF NOT EXISTS idx_robots_last_update ON robots(last_update);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stages (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            queue_depth INT NOT NULL DEFAULT 0 CHECK (queue_depth >= 0),
            throughput FLOAT NOT NULL DEFAULT 0 CHECK (throughput >= 0),
            target_throughput FLOAT NOT NULL DEFAULT 100,
            cycle_time_sec FLOAT NOT NULL DEFAULT 0 CHECK (cycle_time_sec >= 0),
            defect_rate FLOAT NOT NULL DEFAULT 0 CHECK (defect_rate >= 0 AND defect_rate <= 100),
            energy_consumption_kw FLOAT NOT NULL DEFAULT 0 CHECK (energy_consumption_kw >= 0),
            status VARCHAR(20) NOT NULL DEFAULT 'normal'
                CHECK (status IN ('normal', 'warning', 'bottleneck', 'maintenance', 'offline')),
            utilization FLOAT NOT NULL DEFAULT 0 CHECK (utilization >= 0 AND utilization <= 100),
            idle_time_sec FLOAT NOT NULL DEFAULT 0,
            last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_stages_status ON stages(status);
        CREATE INDEX IF NOT EXISTS idx_stages_queue ON stages(queue_depth DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            decision_id VARCHAR(50) UNIQUE NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            decision_type VARCHAR(50) NOT NULL,
            actions JSONB NOT NULL DEFAULT '[]'::jsonb,
            reasoning TEXT NOT NULL,
            confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            expected_impact JSONB,
            actual_impact JSONB,
            state_snapshot JSONB,
            weights_used JSONB,
            priority VARCHAR(50),
            constraints TEXT[],
            status VARCHAR(20) DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted', 'rejected', 'modified', 'executed')),
            requires_approval BOOLEAN DEFAULT FALSE,
            override JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_decisions_type ON decisions(decision_type);
        CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'on_time', 'delayed', 'at_risk', 'inactive')),
            lead_time_days FLOAT NOT NULL DEFAULT 5,
            reliability_score FLOAT DEFAULT 0.9 CHECK (reliability_score >= 0 AND reliability_score <= 1),
            carbon_footprint_kg_per_unit FLOAT DEFAULT 1.0,
            contact_email VARCHAR(255),
            contact_phone VARCHAR(50),
            address TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS supply_orders (
            id SERIAL PRIMARY KEY,
            supplier_id INT NOT NULL,
            supplier_name VARCHAR(100),
            material_id INT,
            material_name VARCHAR(100),
            quantity INT NOT NULL CHECK (quantity > 0),
            unit_price DECIMAL(10, 2),
            total_cost DECIMAL(12, 2),
            order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            due_date DATE NOT NULL,
            delivery_date DATE,
            status VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'confirmed', 'shipped', 'delayed', 'received', 'cancelled')),
            carbon_footprint_kg FLOAT DEFAULT 0,
            lead_time_days FLOAT,
            tracking_number VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_orders_supplier ON supply_orders(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON supply_orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_due_date ON supply_orders(due_date);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            material_name VARCHAR(100) NOT NULL,
            current_stock INT NOT NULL DEFAULT 0 CHECK (current_stock >= 0),
            min_stock INT NOT NULL DEFAULT 100,
            max_stock INT NOT NULL DEFAULT 5000,
            reorder_point INT NOT NULL DEFAULT 500,
            unit_cost DECIMAL(10, 2),
            last_reorder_date DATE,
            days_of_supply FLOAT,
            status VARCHAR(20) DEFAULT 'healthy'
                CHECK (status IN ('healthy', 'low', 'critical', 'overstocked')),
            last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_log (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('robot', 'stage', 'system', 'external')),
            source_id INT,
            metric_name VARCHAR(100) NOT NULL,
            metric_value FLOAT NOT NULL,
            unit VARCHAR(20),
            metadata JSONB
        );
        CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_log(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_telemetry_source ON telemetry_log(source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_telemetry_metric ON telemetry_log(metric_name);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            severity VARCHAR(20) NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            source VARCHAR(50) NOT NULL,
            source_id INT,
            recommended_actions TEXT[],
            acknowledged BOOLEAN DEFAULT FALSE,
            acknowledged_by VARCHAR(100),
            acknowledged_at TIMESTAMP WITH TIME ZONE,
            resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_metrics (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            overall_throughput FLOAT NOT NULL DEFAULT 0,
            overall_quality FLOAT NOT NULL DEFAULT 100,
            overall_energy_kw FLOAT NOT NULL DEFAULT 0,
            carbon_footprint_kg_hr FLOAT NOT NULL DEFAULT 0,
            system_uptime_pct FLOAT NOT NULL DEFAULT 100,
            active_robots INT NOT NULL DEFAULT 0,
            active_stages INT NOT NULL DEFAULT 0,
            bottleneck_stage_id INT,
            efficiency_score FLOAT NOT NULL DEFAULT 0,
            mode VARCHAR(20) DEFAULT 'normal'
        );
        CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS override_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            decision_id VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            operator_id VARCHAR(100),
            action VARCHAR(20) NOT NULL CHECK (action IN ('accept', 'reject', 'modify')),
            reason TEXT NOT NULL,
            original_actions JSONB,
            modified_actions JSONB,
            feedback_category VARCHAR(50),
            learned BOOLEAN DEFAULT FALSE
        );
        CREATE INDEX IF NOT EXISTS idx_override_decision ON override_log(decision_id);
        CREATE INDEX IF NOT EXISTS idx_override_timestamp ON override_log(timestamp DESC);
        """
    )

    # -------------------------------------------------------------------------
    # New in Stage 1: incidents + decision_logs (KB_04 §Postgres schema).
    # incidents anchors every problem the simulator fires; decision_logs is
    # the per-call audit ledger for EU AI Act Art. 12 evidence.
    # -------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP WITH TIME ZONE,
            type VARCHAR(50) NOT NULL
                CHECK (type IN (
                    'machine_crack', 'robot_down', 'late_delivery',
                    'demand_spike', 'defect_surge', 'power_dip'
                )),
            target_id INT,
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            severity VARCHAR(20) NOT NULL DEFAULT 'warning'
                CHECK (severity IN ('info', 'warning', 'critical'))
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_started_at ON incidents(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents(type);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_logs (
            decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            incident_id UUID REFERENCES incidents(incident_id) ON DELETE SET NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            caller VARCHAR(100) NOT NULL,
            tool VARCHAR(100) NOT NULL,
            input_hash CHAR(64) NOT NULL,
            output_hash CHAR(64) NOT NULL,
            inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
            outputs JSONB NOT NULL DEFAULT '{}'::jsonb,
            operator_override BOOLEAN NOT NULL DEFAULT FALSE,
            override_reason TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_decision_logs_timestamp ON decision_logs(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_decision_logs_incident ON decision_logs(incident_id);
        CREATE INDEX IF NOT EXISTS idx_decision_logs_caller ON decision_logs(caller);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS decision_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS incidents CASCADE")
    op.execute("DROP TABLE IF EXISTS override_log CASCADE")
    op.execute("DROP TABLE IF EXISTS system_metrics CASCADE")
    op.execute("DROP TABLE IF EXISTS alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS telemetry_log CASCADE")
    op.execute("DROP TABLE IF EXISTS inventory CASCADE")
    op.execute("DROP TABLE IF EXISTS supply_orders CASCADE")
    op.execute("DROP TABLE IF EXISTS suppliers CASCADE")
    op.execute("DROP TABLE IF EXISTS decisions CASCADE")
    op.execute("DROP TABLE IF EXISTS stages CASCADE")
    op.execute("DROP TABLE IF EXISTS robots CASCADE")
