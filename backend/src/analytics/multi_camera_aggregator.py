import os
import logging
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, List, Any

from ..database.models_production import Camera, Event

logger = logging.getLogger(__name__)


def get_database_url():
    return os.getenv("DATABASE_URL", "postgresql://wink_user:password@localhost:5432/wink_analytics")


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def footfall_by_hour(store_id: str, from_dt: datetime, to_dt: datetime) -> List[Dict]:
    """
    Get hourly footfall counts from entrance cameras only.
    Only counts entrance events with direction='in' from cameras with is_entrance=true.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                date_trunc('hour', e.ts) AS bucket,
                COUNT(*) AS footfall
            FROM events e
            JOIN cameras_extended c ON e.camera_id = c.camera_id
            WHERE e.store_id = :store_id
              AND e.type = 'entrance'
              AND e.payload->>'direction' = 'in'
              AND c.is_entrance = true
              AND e.ts BETWEEN :from_dt AND :to_dt
            GROUP BY 1
            ORDER BY 1
        """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt})

        return [{"hour": row.bucket.isoformat(), "footfall": row.footfall} for row in result]
    finally:
        db.close()


def zones_metrics(store_id: str, from_dt: datetime, to_dt: datetime) -> Dict:
    """
    Get per-zone metrics: unique visitors and average dwell time.
    Deduplicates by (camera_id, person_id, minute) to handle cross-camera tracking.
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                payload->>'logical_zone' AS zone_id,
                COUNT(DISTINCT (camera_id || '_' || payload->>'person_id' || '_' ||
                    date_trunc('minute', ts)::text)) AS unique_visitors,
                AVG((payload->>'dwell_seconds')::float) AS avg_dwell
            FROM events
            WHERE store_id = :store_id
              AND type = 'zone_dwell'
              AND payload->>'dwell_seconds' IS NOT NULL
              AND (payload->>'dwell_seconds')::float >= 4.0
              AND ts BETWEEN :from_dt AND :to_dt
            GROUP BY 1
            ORDER BY 1
        """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt})

        metrics = {}
        for row in result:
            if row.zone_id:
                metrics[row.zone_id] = {
                    "unique_visitors": row.unique_visitors,
                    "avg_dwell": round(row.avg_dwell, 2) if row.avg_dwell else 0.0
                }
        return metrics
    finally:
        db.close()


def shelf_metrics(store_id: str, from_dt: datetime, to_dt: datetime) -> Dict:
    """Get per-shelf metrics: interaction count and average dwell time."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                payload->>'logical_shelf' AS shelf_id,
                COUNT(*) AS interactions,
                AVG((payload->>'dwell_seconds')::float) AS avg_dwell
            FROM events
            WHERE store_id = :store_id
              AND type = 'shelf_interaction'
              AND payload->>'action' = 'touch'
              AND payload->>'dwell_seconds' IS NOT NULL
              AND (payload->>'dwell_seconds')::float >= 4.0
              AND ts BETWEEN :from_dt AND :to_dt
            GROUP BY 1
            ORDER BY 1
        """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt})

        metrics = {}
        for row in result:
            if row.shelf_id:
                metrics[row.shelf_id] = {
                    "interactions": row.interactions,
                    "avg_dwell": round(row.avg_dwell, 2) if row.avg_dwell else 0.0
                }
        return metrics
    finally:
        db.close()


def queue_metrics(store_id: str, from_dt: datetime, to_dt: datetime) -> Dict:
    """
    Get queue metrics: average wait time and P90 wait time.
    """
    db = SessionLocal()
    try:
        # Get all wait times
        result = db.execute(text("""
            SELECT (payload->>'wait_seconds')::float AS wait_seconds
            FROM events
            WHERE store_id = :store_id
              AND type = 'queue_presence'
              AND payload->>'wait_seconds' IS NOT NULL
              AND ts BETWEEN :from_dt AND :to_dt
            ORDER BY wait_seconds
        """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt})

        wait_times = [row.wait_seconds for row in result if row.wait_seconds is not None]

        if not wait_times:
            return {
                "avg_wait": 0.0,
                "p90_wait": 0.0,
                "total_events": 0
            }

        avg_wait = np.mean(wait_times)
        p90_wait = np.percentile(wait_times, 90)

        return {
            "avg_wait": round(avg_wait, 2),
            "p90_wait": round(p90_wait, 2),
            "total_events": len(wait_times)
        }
    finally:
        db.close()


def live_snapshot(store_id: str, window_sec: int = 60) -> Dict[str, Any]:
    """
    Get live metrics for the last N seconds.
    Returns current footfall, active zones, and queue length.
    """
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(seconds=window_sec)

        # Footfall in window (from entrance cameras only)
        footfall = db.execute(text("""
            SELECT COUNT(*)
            FROM events e
            JOIN cameras_extended c ON e.camera_id = c.camera_id
            WHERE e.store_id = :store_id
              AND e.type = 'entrance'
              AND e.payload->>'direction' = 'in'
              AND c.is_entrance = true
              AND e.ts >= :since
        """), {"store_id": store_id, "since": since}).scalar()

        # Active zones (people currently in zones based on recent enter events)
        active_zones_result = db.execute(text("""
            SELECT
                payload->>'logical_zone' AS zone_id,
                COUNT(DISTINCT payload->>'person_id') AS active_count
            FROM events
            WHERE store_id = :store_id
              AND type = 'zone_dwell'
              AND ts >= :since
            GROUP BY 1
        """), {"store_id": store_id, "since": since})

        per_zone_active = {}
        for row in active_zones_result:
            if row.zone_id:
                per_zone_active[row.zone_id] = row.active_count

        # Queue length (people in queue based on recent events)
        queue_len = db.execute(text("""
            SELECT COUNT(DISTINCT payload->>'person_id')
            FROM events
            WHERE store_id = :store_id
              AND type = 'queue_presence'
              AND ts >= :since
        """), {"store_id": store_id, "since": since}).scalar()

        return {
            "footfall_now": footfall or 0,
            "per_zone_active": per_zone_active,
            "queue_now": queue_len or 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        db.close()


def peak_hour(store_id: str, from_dt: datetime, to_dt: datetime) -> Dict:
    """Identify the peak hour based on footfall."""
    hourly = footfall_by_hour(store_id, from_dt, to_dt)
    if not hourly:
        return {"peak_hour": None, "footfall": 0}

    peak = max(hourly, key=lambda x: x["footfall"])
    return {"peak_hour": peak["hour"], "footfall": peak["footfall"]}


def footfall_by_day(store_id: str, from_dt: datetime, to_dt: datetime) -> List[Dict]:
    """Get daily footfall counts from entrance cameras only."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                DATE(e.ts) AS day,
                COUNT(*) AS footfall
            FROM events e
            JOIN cameras_extended c ON e.camera_id = c.camera_id
            WHERE e.store_id = :store_id
              AND e.type = 'entrance'
              AND e.payload->>'direction' = 'in'
              AND c.is_entrance = true
              AND e.ts BETWEEN :from_dt AND :to_dt
            GROUP BY 1
            ORDER BY 1
        """), {"store_id": store_id, "from_dt": from_dt, "to_dt": to_dt})

        return [{"day": str(row.day), "footfall": row.footfall} for row in result]
    finally:
        db.close()


def aggregate_all_metrics(store_id: str, from_dt: datetime, to_dt: datetime) -> Dict:
    """
    Aggregate all metrics for a store in one call.
    Returns comprehensive dashboard data.
    """
    return {
        "footfall_by_hour": footfall_by_hour(store_id, from_dt, to_dt),
        "zone_metrics": zones_metrics(store_id, from_dt, to_dt),
        "shelf_metrics": shelf_metrics(store_id, from_dt, to_dt),
        "queue_metrics": queue_metrics(store_id, from_dt, to_dt),
        "peak_hour": peak_hour(store_id, from_dt, to_dt),
        "live": live_snapshot(store_id),
        "period": {
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat()
        }
    }
