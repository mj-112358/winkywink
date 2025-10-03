-- Create shelf_interactions table for enhanced interaction tracking
-- This replaces the simple counter-based approach with duration-based tracking

CREATE TABLE IF NOT EXISTS shelf_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    camera_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    shelf_name TEXT NOT NULL,
    shelf_type TEXT DEFAULT 'shelf',
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    created_at REAL NOT NULL,

    FOREIGN KEY (camera_id) REFERENCES cameras(id)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_shelf_interactions_store_camera
    ON shelf_interactions(store_id, camera_id);

CREATE INDEX IF NOT EXISTS idx_shelf_interactions_time
    ON shelf_interactions(store_id, created_at);

CREATE INDEX IF NOT EXISTS idx_shelf_interactions_shelf
    ON shelf_interactions(store_id, shelf_name, created_at);

-- Add sample query for analytics
/*
-- Get hourly shelf interaction counts
SELECT
    shelf_name,
    datetime(created_at, 'unixepoch', 'localtime') as hour,
    COUNT(*) as interaction_count,
    AVG(duration) as avg_duration,
    SUM(duration) as total_duration
FROM shelf_interactions
WHERE store_id = ? AND created_at >= ? AND created_at < ?
GROUP BY shelf_name, strftime('%H', datetime(created_at, 'unixepoch', 'localtime'))
ORDER BY hour, interaction_count DESC;

-- Get daily shelf performance
SELECT
    shelf_name,
    date(created_at, 'unixepoch', 'localtime') as date,
    COUNT(*) as total_interactions,
    COUNT(DISTINCT track_id) as unique_visitors,
    AVG(duration) as avg_interaction_duration,
    MAX(duration) as max_interaction_duration
FROM shelf_interactions
WHERE store_id = ? AND created_at >= ? AND created_at < ?
GROUP BY shelf_name, date
ORDER BY date, total_interactions DESC;
*/