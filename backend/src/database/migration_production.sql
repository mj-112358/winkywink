-- Production Schema Migration v2.0.0
-- Complete multi-tenant schema with org/store/camera isolation

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations table
CREATE TABLE IF NOT EXISTS orgs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orgs_slug ON orgs(slug);
CREATE INDEX IF NOT EXISTS idx_orgs_active ON orgs(is_active);

-- Stores table
CREATE TABLE IF NOT EXISTS stores_extended (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stores_org ON stores_extended(org_id);
CREATE INDEX IF NOT EXISTS idx_stores_store_id ON stores_extended(store_id);
CREATE INDEX IF NOT EXISTS idx_stores_active ON stores_extended(org_id, is_active);

-- Cameras table with capabilities
CREATE TABLE IF NOT EXISTS cameras_extended (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    capabilities TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, camera_id)
);

CREATE INDEX IF NOT EXISTS idx_cameras_store ON cameras_extended(store_id);
CREATE INDEX IF NOT EXISTS idx_cameras_org ON cameras_extended(org_id);
CREATE INDEX IF NOT EXISTS idx_cameras_active ON cameras_extended(store_id, is_active);
CREATE INDEX IF NOT EXISTS idx_cameras_capabilities ON cameras_extended USING GIN(capabilities);

-- Edge API keys
CREATE TABLE IF NOT EXISTS edge_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    FOREIGN KEY (store_id, camera_id) REFERENCES cameras_extended(store_id, camera_id)
);

CREATE INDEX IF NOT EXISTS idx_edge_keys_api_key ON edge_keys(api_key) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_edge_keys_store_camera ON edge_keys(store_id, camera_id);

-- Generic events table (JSONB for all events)
CREATE TABLE IF NOT EXISTS events_generic (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    person_key VARCHAR(150) NOT NULL,
    ts TIMESTAMP NOT NULL,
    device_ts TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_generic_store_ts ON events_generic(store_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_generic_camera_ts ON events_generic(store_id, camera_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_generic_type ON events_generic(store_id, event_type, ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_generic_payload ON events_generic USING GIN(payload);
CREATE INDEX IF NOT EXISTS idx_events_generic_person ON events_generic(store_id, person_key, ts DESC);

-- Entrance events table
CREATE TABLE IF NOT EXISTS entrance_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    person_key VARCHAR(150) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('in', 'out')),
    ts TIMESTAMP NOT NULL,
    device_ts TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entrance_events_store_ts ON entrance_events(store_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_entrance_events_direction ON entrance_events(store_id, direction, ts DESC);
CREATE INDEX IF NOT EXISTS idx_entrance_events_camera ON entrance_events(store_id, camera_id, ts DESC);

-- Zone events table
CREATE TABLE IF NOT EXISTS zone_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    zone_id VARCHAR(100) NOT NULL,
    person_key VARCHAR(150) NOT NULL,
    enter_ts TIMESTAMP,
    exit_ts TIMESTAMP,
    dwell_seconds DOUBLE PRECISION,
    ts TIMESTAMP NOT NULL,
    device_ts TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zone_events_store_ts ON zone_events(store_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_zone_events_zone ON zone_events(store_id, zone_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_zone_events_camera ON zone_events(store_id, camera_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_zone_events_dwell ON zone_events(store_id, dwell_seconds DESC) WHERE dwell_seconds IS NOT NULL;

-- Shelf interactions table
CREATE TABLE IF NOT EXISTS shelf_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    shelf_id VARCHAR(100) NOT NULL,
    person_key VARCHAR(150) NOT NULL,
    dwell_seconds DOUBLE PRECISION NOT NULL,
    ts TIMESTAMP NOT NULL,
    device_ts TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shelf_interactions_store_ts ON shelf_interactions(store_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_shelf_interactions_shelf ON shelf_interactions(store_id, shelf_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_shelf_interactions_camera ON shelf_interactions(store_id, camera_id, ts DESC);

-- Queue events table
CREATE TABLE IF NOT EXISTS queue_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    queue_id VARCHAR(100) NOT NULL,
    person_key VARCHAR(150) NOT NULL,
    enter_ts TIMESTAMP,
    exit_ts TIMESTAMP,
    wait_seconds DOUBLE PRECISION,
    ts TIMESTAMP NOT NULL,
    device_ts TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queue_events_store_ts ON queue_events(store_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_queue_events_queue ON queue_events(store_id, queue_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_queue_events_camera ON queue_events(store_id, camera_id, ts DESC);

-- Hourly metrics aggregation
CREATE TABLE IF NOT EXISTS metrics_hourly (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100),
    hour_bucket TIMESTAMP NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, camera_id, hour_bucket, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_metrics_hourly_store_hour ON metrics_hourly(store_id, hour_bucket DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_hourly_metric ON metrics_hourly(store_id, metric_type, hour_bucket DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_hourly_camera ON metrics_hourly(store_id, camera_id, hour_bucket DESC) WHERE camera_id IS NOT NULL;

-- Daily metrics aggregation
CREATE TABLE IF NOT EXISTS metrics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100),
    date DATE NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, camera_id, date, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_metrics_daily_store_date ON metrics_daily(store_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_daily_metric ON metrics_daily(store_id, metric_type, date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_daily_camera ON metrics_daily(store_id, camera_id, date DESC) WHERE camera_id IS NOT NULL;

-- Camera heartbeat status
CREATE TABLE IF NOT EXISTS camera_heartbeats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores_extended(store_id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    device_ts TIMESTAMP NOT NULL,
    status_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, camera_id)
);

CREATE INDEX IF NOT EXISTS idx_camera_heartbeats_store ON camera_heartbeats(store_id, updated_at DESC);

-- Row-level security policies
ALTER TABLE stores_extended ENABLE ROW LEVEL SECURITY;
ALTER TABLE cameras_extended ENABLE ROW LEVEL SECURITY;
ALTER TABLE events_generic ENABLE ROW LEVEL SECURITY;
ALTER TABLE entrance_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE zone_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE shelf_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE queue_events ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (customize per deployment)
-- CREATE POLICY org_isolation ON stores_extended
--     USING (org_id = current_setting('app.current_org_id')::uuid);