import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from ..database.models_production import Store, Camera
from ..analytics import multi_camera_aggregator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_database_url():
    return os.getenv("DATABASE_URL", "postgresql://wink_user:password@localhost:5432/wink_analytics")


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).all()
    return {
        "stores": [
            {"store_id": s.store_id, "name": s.name, "timezone": s.timezone}
            for s in stores
        ]
    }


@router.get("/cameras")
def list_cameras(store_id: str = Query(...), db: Session = Depends(get_db)):
    cameras = db.query(Camera).filter(Camera.store_id == store_id).all()
    return {
        "cameras": [
            {
                "camera_id": c.camera_id,
                "name": c.name,
                "capabilities": c.capabilities or []
            }
            for c in cameras
        ]
    }


@router.get("/live")
def get_live(store_id: str = Query(...)):
    snapshot = multi_camera_aggregator.live_snapshot(store_id, window_sec=60)

    today_midnight = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_footfall_list = multi_camera_aggregator.footfall_by_hour(store_id, today_midnight, datetime.utcnow())
    footfall_today = sum(item["footfall"] for item in today_footfall_list)

    zones = multi_camera_aggregator.zones_metrics(store_id, today_midnight, datetime.utcnow())
    shelf = multi_camera_aggregator.shelf_metrics(store_id, today_midnight, datetime.utcnow())

    return {
        "footfall_today": footfall_today,
        "per_zone_active": snapshot["per_zone_active"],
        "per_zone_unique_today": {k: v["unique_visitors"] for k, v in zones.items()},
        "per_shelf_interactions_today": {k: v["interactions"] for k, v in shelf.items()},
        "queue_now": snapshot["queue_now"],
        "timestamp": snapshot["timestamp"]
    }


@router.get("/metrics")
def get_metrics(
    store_id: str = Query(...),
    from_dt: Optional[str] = Query(None, alias="from"),
    to_dt: Optional[str] = Query(None, alias="to"),
    granularity: str = Query("hour", regex="^(hour|day)$")
):
    if not from_dt:
        from_dt = (datetime.utcnow() - timedelta(days=1)).isoformat()
    if not to_dt:
        to_dt = datetime.utcnow().isoformat()

    from_datetime = datetime.fromisoformat(from_dt.replace("Z", "+00:00"))
    to_datetime = datetime.fromisoformat(to_dt.replace("Z", "+00:00"))

    footfall_hourly = multi_camera_aggregator.footfall_by_hour(store_id, from_datetime, to_datetime)
    zones = multi_camera_aggregator.zones_metrics(store_id, from_datetime, to_datetime)
    shelf = multi_camera_aggregator.shelf_metrics(store_id, from_datetime, to_datetime)
    queue = multi_camera_aggregator.queue_metrics(store_id, from_datetime, to_datetime)
    peak = multi_camera_aggregator.peak_hour(store_id, from_datetime, to_datetime)

    return {
        "footfall_by_hour": footfall_hourly,
        "zone_metrics": zones,
        "shelf_interactions": shelf,
        "queue_avg_wait": queue["avg_wait"],
        "peak_hour": peak["peak_hour"],
        "peak_hour_footfall": peak["footfall"]
    }
