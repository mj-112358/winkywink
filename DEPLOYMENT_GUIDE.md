# WINK Platform - Complete Deployment Guide

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    WINK Retail Analytics                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Edge (Store)              Cloud (Backend)                   │
│  ┌──────────────┐         ┌────────────────────────┐        │
│  │ RTSP Cameras │────────>│  FastAPI Backend       │        │
│  │  (Multi-cam) │  HTTPS  │  - Ingestion API       │        │
│  └──────────────┘         │  - Dashboard API       │        │
│         │                 │  - Analytics API       │        │
│         ↓                 └────────────────────────┘        │
│  ┌──────────────┐                    │                       │
│  │  YOLOv8 +    │                    ↓                       │
│  │  Tracking    │         ┌────────────────────────┐        │
│  └──────────────┘         │  PostgreSQL + Redis    │        │
│         │                 │  - Multi-store data    │        │
│         ↓                 │  - Real-time cache     │        │
│  ┌──────────────┐         └────────────────────────┘        │
│  │  Events      │                                            │
│  │  - Entrance  │                                            │
│  │  - Zones     │                                            │
│  │  - Shelves   │                                            │
│  │  - Queue     │                                            │
│  └──────────────┘                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### Backend (Cloud)
- PostgreSQL 14+
- Redis 7+
- Python 3.10+
- FastAPI application

### Edge (Store)
- Docker & Docker Compose
- Network access to RTSP cameras
- HTTPS connectivity to backend
- 4GB+ RAM per camera

## 🚀 Step-by-Step Deployment

### Phase 1: Backend Setup

#### 1.1 Database Setup

```bash
# Install PostgreSQL
sudo apt-get install postgresql-14

# Create database
sudo -u postgres createdb wink_production

# Run migration
cd backend
python -c "from src.database.database import init_db; init_db()"
psql -U postgres -d wink_production -f src/database/migration_production.sql
```

#### 1.2 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### 1.3 Configure Environment

```bash
# backend/.env
DATABASE_URL=postgresql://postgres:password@localhost:5432/wink_production
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
```

#### 1.4 Seed Test Data

```bash
python seed_production.py
```

Output:
```
🌱 Seeding production database...

1️⃣  Creating organization...
   ✓ Organization created: <uuid>

2️⃣  Creating store...
   ✓ Store created: store_demo_001

3️⃣  Creating cameras...
   ✓ Camera: Main Entrance Camera (cam_entrance_01)
      Capabilities: entrance, zones
      API Key: wink_edge_ABC123...
   ✓ Camera: Product Zone Camera (cam_zone_01)
      Capabilities: zones, shelves
      API Key: wink_edge_DEF456...
```

#### 1.5 Start Backend

```bash
# Development
uvicorn src.main:app --reload --port 8000

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Phase 2: Edge Deployment

#### 2.1 Provision Edge Keys

Use the backend admin API to create edge keys:

```bash
# Get organization UUID (from seed output or database)
ORG_ID="<uuid-from-seed>"
STORE_ID="store_demo_001"

# Create edge key for camera
curl -X POST https://api.winkai.in/api/admin/edge-keys \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "'"$ORG_ID"'",
    "store_id": "'"$STORE_ID"'",
    "camera_id": "cam_entrance_01"
  }'
```

Response:
```json
{
  "id": "key-uuid",
  "api_key": "wink_edge_abc123xyz...",
  "store_id": "store_demo_001",
  "camera_id": "cam_entrance_01",
  "message": "⚠️  Store this API key securely - it won't be shown again!"
}
```

#### 2.2 Configure Edge Collector

```bash
cd store-helper
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

```yaml
api_base: "https://api.winkai.in"
api_key: "wink_edge_abc123xyz..."  # From step 2.1
org_id: "<org-uuid>"
store_id: "store_demo_001"

cameras:
  - camera_id: "cam_entrance_01"
    rtsp: "rtsp://admin:pass@192.168.1.10:554/stream1"
    capabilities: ["entrance"]
    screenshot_size: [1920, 1080]
    entrance_line:
      - [960, 400]  # Top of doorway
      - [960, 700]  # Bottom of doorway

  - camera_id: "cam_zone_01"
    rtsp: "rtsp://admin:pass@192.168.1.11:554/stream1"
    capabilities: ["zones", "shelves"]
    screenshot_size: [1920, 1080]
    zones:
      electronics:
        - [300, 200]
        - [800, 200]
        - [800, 600]
        - [300, 600]
    shelves:
      shelf_promo:
        - [100, 100]
        - [500, 100]
        - [500, 400]
        - [100, 400]
```

#### 2.3 Deploy with Docker

```bash
# Build and start
docker-compose -f docker-compose.v2.yml up --build -d

# View logs
docker-compose -f docker-compose.v2.yml logs -f

# Check status
docker-compose -f docker-compose.v2.yml ps
```

Expected output:
```
🎯 WINK STORE HELPER - EDGE RUNTIME
======================================================================
Store ID: store_demo_001
Cameras: 2
API Endpoint: https://api.winkai.in
======================================================================

📹 CAMERA CONFIGURATION:
1. Camera ID: cam_entrance_01
   RTSP: rtsp://admin:pass@192.168.1.10:554/stream1
   Capabilities: entrance
   🚪 Entrance tracking: Enabled

2. Camera ID: cam_zone_01
   RTSP: rtsp://admin:pass@192.168.1.11:554/stream1
   Capabilities: zones, shelves
   🏪 Zones: electronics
   🛒 Shelves: shelf_promo

🚀 STARTING DETECTION...
✅ All cameras started successfully
```

### Phase 3: Verification

#### 3.1 Test Heartbeat

```bash
# Check if heartbeats are being received
curl "https://api.winkai.in/api/dashboard/cameras?store_id=store_demo_001"
```

Expected response:
```json
{
  "cameras": [
    {
      "camera_id": "cam_entrance_01",
      "name": "Main Entrance Camera",
      "capabilities": ["entrance", "zones"],
      "status": "online",
      "last_heartbeat": "2025-10-01T10:30:00Z"
    }
  ]
}
```

#### 3.2 Test Live Metrics

```bash
# Get live metrics
curl "https://api.winkai.in/api/dashboard/live?store_id=store_demo_001"
```

Expected response:
```json
{
  "store_id": "store_demo_001",
  "footfall": 45,
  "zones": {
    "electronics": {
      "entries": 12,
      "unique_visitors": 8,
      "avg_dwell": 67.5
    }
  },
  "shelves": {
    "shelf_promo": {
      "interactions": 5,
      "avg_dwell": 15.2
    }
  },
  "cameras": [...],
  "timestamp": "2025-10-01T10:30:00Z"
}
```

#### 3.3 Test Analytics

```bash
# Spike detection
curl "https://api.winkai.in/api/analytics/spikes?store_id=store_demo_001&days=7"

# Promo analysis
curl "https://api.winkai.in/api/analytics/promo?store_id=store_demo_001&start_date=2025-10-01&end_date=2025-10-07"
```

## 🧪 Testing Guide

### Manual Event Testing

Send test events directly:

```bash
# Test entrance event
curl -X POST https://api.winkai.in/api/ingest/events \
  -H "Authorization: Bearer wink_edge_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "'"$ORG_ID"'",
    "store_id": "store_demo_001",
    "camera_id": "cam_entrance_01",
    "device_ts": "2025-10-01T10:00:00Z",
    "events": [
      {
        "type": "entrance",
        "ts": "2025-10-01T10:00:00Z",
        "direction": "in",
        "person_key": "test_track_1"
      }
    ]
  }'

# Test zone event
curl -X POST https://api.winkai.in/api/ingest/events \
  -H "Authorization: Bearer wink_edge_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "'"$ORG_ID"'",
    "store_id": "store_demo_001",
    "camera_id": "cam_zone_01",
    "device_ts": "2025-10-01T10:05:00Z",
    "events": [
      {
        "type": "zone",
        "ts": "2025-10-01T10:05:00Z",
        "zone_id": "electronics",
        "enter_ts": "2025-10-01T10:00:00Z",
        "exit_ts": "2025-10-01T10:05:00Z",
        "dwell_seconds": 300.0,
        "person_key": "test_track_1"
      }
    ]
  }'

# Test shelf interaction
curl -X POST https://api.winkai.in/api/ingest/events \
  -H "Authorization: Bearer wink_edge_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "'"$ORG_ID"'",
    "store_id": "store_demo_001",
    "camera_id": "cam_zone_01",
    "device_ts": "2025-10-01T10:03:00Z",
    "events": [
      {
        "type": "shelf",
        "ts": "2025-10-01T10:03:00Z",
        "shelf_id": "shelf_promo",
        "dwell_seconds": 15.5,
        "person_key": "test_track_1"
      }
    ]
  }'

# Test queue event
curl -X POST https://api.winkai.in/api/ingest/events \
  -H "Authorization: Bearer wink_edge_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "'"$ORG_ID"'",
    "store_id": "store_demo_001",
    "camera_id": "cam_checkout_01",
    "device_ts": "2025-10-01T10:10:00Z",
    "events": [
      {
        "type": "queue",
        "ts": "2025-10-01T10:10:00Z",
        "queue_id": "checkout",
        "enter_ts": "2025-10-01T10:08:00Z",
        "exit_ts": "2025-10-01T10:10:00Z",
        "wait_seconds": 120.0,
        "person_key": "test_track_8"
      }
    ]
  }'
```

### Edge Collector Testing

```bash
# Run test suite
cd store-helper
python test_edge.py config.yaml
```

Expected output:
```
======================================================================
🧪 WINK EDGE COLLECTOR TEST SUITE
======================================================================
📋 Validating configuration...
  ✅ Config valid
     API: https://api.winkai.in
     Store: store_demo_001
     Cameras: 2

📐 Testing polygon scaling...
  ✅ Polygon scaling correct
  ✅ Point-in-polygon check correct

💾 Testing offline buffering...
  🔌 Simulating offline mode...
  ✅ Event buffered to disk (1 events)

🔗 Testing API connectivity...
  📡 Sending heartbeat...
  ✅ Heartbeat successful

📤 Testing event ingestion...
  📊 Sending 4 test events...
  ✅ Events sent successfully

======================================================================
✅ ALL TESTS PASSED
======================================================================
```

## 🔧 Troubleshooting

### Backend Issues

**Database connection failed:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -U postgres -d wink_production -c "SELECT 1"
```

**Redis connection failed:**
```bash
# Check Redis status
redis-cli ping
```

### Edge Issues

**RTSP connection failed:**
```bash
# Test RTSP stream
ffplay rtsp://admin:pass@192.168.1.10:554/stream1

# Check network
ping 192.168.1.10
```

**API authentication failed:**
```bash
# Verify API key
curl -X POST https://api.winkai.in/api/ingest/heartbeat \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"...","store_id":"...","camera_id":"...","device_ts":"2025-10-01T10:00:00Z","status_data":{}}'

# Check logs
docker-compose -f docker-compose.v2.yml logs wink-edge | grep "401\|403"
```

**No events appearing:**
```bash
# Check detector logs
docker-compose -f docker-compose.v2.yml logs wink-edge | grep "event"

# Verify polygon configuration
# Events only emit if person is inside polygon for >2-3 seconds
```

## 📊 Monitoring

### Backend Health

```bash
# Check API health
curl https://api.winkai.in/api/ingest/health
curl https://api.winkai.in/api/analytics/health

# Database stats
psql -U postgres -d wink_production -c "
  SELECT
    'entrance' as type, COUNT(*) as count FROM entrance_events
  UNION
  SELECT 'zone', COUNT(*) FROM zone_events
  UNION
  SELECT 'shelf', COUNT(*) FROM shelf_interactions
  UNION
  SELECT 'queue', COUNT(*) FROM queue_events;
"
```

### Edge Health

```bash
# Container status
docker-compose -f docker-compose.v2.yml ps

# Resource usage
docker stats wink-store-helper

# Event buffer
ls -lh buffers/*/buffer_*.jsonl
```

## 🚢 Production Deployment

### Backend (Cloud)

Use systemd service:

```ini
# /etc/systemd/system/wink-backend.service
[Unit]
Description=WINK Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=wink
WorkingDirectory=/opt/wink-backend
Environment="DATABASE_URL=postgresql://..."
ExecStart=/opt/wink-backend/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable wink-backend
sudo systemctl start wink-backend
```

### Edge (Store)

Use Docker with auto-restart:

```yaml
# docker-compose.v2.yml (already configured)
services:
  wink-edge:
    restart: unless-stopped
    # ... rest of config
```

Ensure Docker starts on boot:
```bash
sudo systemctl enable docker
```

## 📝 Summary

✅ **Backend Deployed**
- PostgreSQL with multi-tenant schema
- FastAPI with ingestion + dashboard + analytics APIs
- Redis for real-time caching

✅ **Edge Deployed**
- Multi-camera YOLO detection
- Event generation (entrance/zone/shelf/queue)
- Offline buffering & retry logic
- Docker containerization

✅ **Tested**
- API authentication
- Event ingestion
- Live metrics
- Analytics endpoints

🎉 **System is production-ready!**
