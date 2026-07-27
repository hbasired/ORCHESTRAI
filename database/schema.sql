-- Supabase PostgreSQL Schema for AI Embodied Agent
-- Manufacturing Optimization Platform Database

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- ROBOTS TABLE
-- ============================================================================
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

CREATE INDEX idx_robots_status ON robots(status);
CREATE INDEX idx_robots_last_update ON robots(last_update);

-- ============================================================================
-- MANUFACTURING STAGES TABLE
-- ============================================================================
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

CREATE INDEX idx_stages_status ON stages(status);
CREATE INDEX idx_stages_queue ON stages(queue_depth DESC);

-- ============================================================================
-- AI DECISIONS TABLE
-- ============================================================================
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

CREATE INDEX idx_decisions_timestamp ON decisions(timestamp DESC);
CREATE INDEX idx_decisions_type ON decisions(decision_type);
CREATE INDEX idx_decisions_status ON decisions(status);

-- ============================================================================
-- SUPPLY ORDERS TABLE
-- ============================================================================
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

CREATE INDEX idx_orders_supplier ON supply_orders(supplier_id);
CREATE INDEX idx_orders_status ON supply_orders(status);
CREATE INDEX idx_orders_due_date ON supply_orders(due_date);

-- ============================================================================
-- SUPPLIERS TABLE
-- ============================================================================
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

-- ============================================================================
-- INVENTORY TABLE
-- ============================================================================
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

CREATE INDEX idx_inventory_status ON inventory(status);

-- ============================================================================
-- TELEMETRY LOG TABLE (Time-series data)
-- ============================================================================
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

CREATE INDEX idx_telemetry_timestamp ON telemetry_log(timestamp DESC);
CREATE INDEX idx_telemetry_source ON telemetry_log(source_type, source_id);
CREATE INDEX idx_telemetry_metric ON telemetry_log(metric_name);

-- Partition by time for better performance (optional)
-- CREATE TABLE telemetry_log_y2026m01 PARTITION OF telemetry_log
--     FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- ============================================================================
-- ALERTS TABLE
-- ============================================================================
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

CREATE INDEX idx_alerts_timestamp ON alerts(timestamp DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);

-- ============================================================================
-- SYSTEM METRICS TABLE (Aggregated KPIs)
-- ============================================================================
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

CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp DESC);

-- ============================================================================
-- HUMAN OVERRIDES LOG TABLE
-- ============================================================================
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

CREATE INDEX idx_override_decision ON override_log(decision_id);
CREATE INDEX idx_override_timestamp ON override_log(timestamp DESC);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Current system state
CREATE OR REPLACE VIEW v_current_system_state AS
SELECT 
    (SELECT COUNT(*) FROM robots WHERE status != 'error') as active_robots,
    (SELECT COUNT(*) FROM stages WHERE status != 'offline') as active_stages,
    (SELECT AVG(battery_pct) FROM robots) as avg_robot_battery,
    (SELECT SUM(queue_depth) FROM stages) as total_queue_depth,
    (SELECT SUM(throughput) FROM stages) as total_throughput,
    (SELECT SUM(energy_consumption_kw) FROM stages) as total_energy,
    (SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE AND severity = 'critical') as critical_alerts,
    (SELECT COUNT(*) FROM decisions WHERE status = 'pending') as pending_decisions;

-- View: Robot summary
CREATE OR REPLACE VIEW v_robot_summary AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(battery_pct) as avg_battery,
    AVG(speed) as avg_speed
FROM robots
GROUP BY status;

-- View: Stage bottlenecks
CREATE OR REPLACE VIEW v_stage_bottlenecks AS
SELECT 
    id,
    name,
    queue_depth,
    throughput,
    energy_consumption_kw,
    status
FROM stages
WHERE queue_depth > 15 OR status = 'bottleneck'
ORDER BY queue_depth DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Update robot position
CREATE OR REPLACE FUNCTION update_robot_position(
    p_robot_id INT,
    p_x FLOAT,
    p_y FLOAT,
    p_battery FLOAT DEFAULT NULL,
    p_status VARCHAR DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE robots
    SET 
        position_x = p_x,
        position_y = p_y,
        battery_pct = COALESCE(p_battery, battery_pct),
        status = COALESCE(p_status, status),
        last_update = CURRENT_TIMESTAMP
    WHERE id = p_robot_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Log telemetry
CREATE OR REPLACE FUNCTION log_telemetry(
    p_source_type VARCHAR,
    p_source_id INT,
    p_metric_name VARCHAR,
    p_metric_value FLOAT,
    p_unit VARCHAR DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO telemetry_log (source_type, source_id, metric_name, metric_value, unit)
    VALUES (p_source_type, p_source_id, p_metric_name, p_metric_value, p_unit)
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get decision stats
CREATE OR REPLACE FUNCTION get_decision_stats(p_hours INT DEFAULT 24)
RETURNS TABLE (
    total_decisions BIGINT,
    accepted_count BIGINT,
    rejected_count BIGINT,
    avg_confidence FLOAT,
    override_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE status = 'accepted')::BIGINT,
        COUNT(*) FILTER (WHERE status = 'rejected')::BIGINT,
        AVG(confidence),
        (COUNT(*) FILTER (WHERE override IS NOT NULL)::FLOAT / NULLIF(COUNT(*), 0))
    FROM decisions
    WHERE timestamp > CURRENT_TIMESTAMP - (p_hours || ' hours')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert initial robots
INSERT INTO robots (id, position_x, position_y, battery_pct, status, task) VALUES
(1, 15.5, 10.2, 85, 'working', 'Transporting to Stage 3'),
(2, 45.0, 25.0, 62, 'working', 'Picking items'),
(3, 30.0, 40.0, 18, 'warning', 'Moving to charger'),
(4, 80.0, 15.0, 95, 'idle', NULL),
(5, 55.0, 35.0, 45, 'working', 'Delivery to Stage 7'),
(6, 20.0, 50.0, 100, 'charging', 'Charging'),
(7, 70.0, 45.0, 78, 'working', 'Material handling'),
(8, 35.0, 20.0, 55, 'idle', NULL),
(9, 90.0, 30.0, 30, 'working', 'Transit'),
(10, 10.0, 55.0, 88, 'working', 'Assembly support')
ON CONFLICT (id) DO NOTHING;

-- Insert initial stages
INSERT INTO stages (id, name, queue_depth, throughput, status, energy_consumption_kw) VALUES
(1, 'Receiving', 5, 120, 'normal', 8.5),
(2, 'Inspection', 8, 100, 'normal', 5.2),
(3, 'Sorting', 12, 95, 'warning', 12.0),
(4, 'Assembly Line A', 22, 80, 'bottleneck', 25.0),
(5, 'Assembly Line B', 10, 110, 'normal', 22.0),
(6, 'Quality Check', 6, 105, 'normal', 8.0),
(7, 'Packaging', 15, 90, 'warning', 10.5),
(8, 'Labeling', 4, 130, 'normal', 3.5),
(9, 'Dispatch Prep', 7, 115, 'normal', 6.0),
(10, 'Shipping', 3, 140, 'normal', 4.5)
ON CONFLICT (id) DO NOTHING;

-- Insert initial suppliers
INSERT INTO suppliers (id, name, status, lead_time_days, reliability_score) VALUES
(1, 'Alpha Components', 'on_time', 3.5, 0.92),
(2, 'Beta Materials', 'delayed', 5.0, 0.78),
(3, 'Gamma Electronics', 'on_time', 2.0, 0.95)
ON CONFLICT (id) DO NOTHING;

-- Insert initial inventory
INSERT INTO inventory (id, material_name, current_stock, min_stock, max_stock, reorder_point, status) VALUES
(1, 'Circuit Boards', 1500, 500, 3000, 800, 'healthy'),
(2, 'Enclosures', 320, 400, 2000, 600, 'low'),
(3, 'Connectors', 8500, 2000, 15000, 4000, 'healthy')
ON CONFLICT (id) DO NOTHING;

-- Grant permissions (for Supabase)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
