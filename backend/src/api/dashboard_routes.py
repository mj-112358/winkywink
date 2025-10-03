"""
Complete Dashboard API - no placeholders.
Provides live and historical metrics with multi-camera aggregation.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

from ..database.database import get_db_session
from ..database.models_production import StoreExtended, CameraExtended
from ..analytics.multi_camera_aggregator import get_aggregator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stores")
def list_stores(
    org_id: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    List all stores with camera count.

    Query params:
        org_id: Optional org filter

    Returns:
        {
            "stores": [
                {
                    "store_id": "...",
                    "name": "...",
                    "timezone": "...",
                    "camera_count": N,
                    "capabilities": ["entrance", "zones", ...]
                }
            ]
        }
    """
    try:
        query = db.query(StoreExtended).filter_by(is_active=True)

        if org_id:
            query = query.filter_by(org_id=org_id)

        stores = query.all()

        result = []
        for store in stores:
            # Get cameras for this store
            cameras = db.query(CameraExtended).filter_by(
                store_id=store.store_id,
                is_active=True
            ).all()

            # Collect unique capabilities
            all_caps = set()
            for cam in cameras:
                all_caps.update(cam.capabilities)

            result.append({
                "store_id": store.store_id,
                "name": store.name,
                "timezone": store.timezone,
                "camera_count": len(cameras),
                "capabilities": sorted(list(all_caps))
            })

        return {"stores": result}

    except Exception as e:
        logger.error(f"Error listing stores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live")
def get_live_metrics(
    store_id: str = Query(..., description="Store ID"),
    lookback_minutes: int = Query(15, ge=1, le=60, description="Lookback window in minutes"),
    db: Session = Depends(get_db_session)
):
    """
    Get live metrics for last N minutes.

    Uses multi-camera aggregator with capability-based filtering:
    - Footfall: Only from 'entrance' cameras
    - Zones: Union from 'zones' cameras
    - Shelves: Sum from 'shelves' cameras
    - Queue: From 'queue' cameras

    Returns:
        {
            "store_id": "...",
            "footfall": N,
            "zones": {"zone_1": {"entries": N, "unique_visitors": N, "avg_dwell": F}},
            "shelves": {"shelf_1": {"interactions": N, "avg_dwell": F}},
            "queue": {"avg_wait": F},
            "cameras": [...],
            "timestamp": "..."
        }
    """
    try:
        # Verify store exists
        store = db.query(StoreExtended).filter_by(store_id=store_id, is_active=True).first()
        if not store:
            raise HTTPException(status_code=404, detail=f"Store {store_id} not found")

        # Get aggregator
        aggregator = get_aggregator(store_id, db)

        # Get live snapshot
        metrics = aggregator.aggregate_live(lookback_minutes=lookback_minutes)
        metrics["store_id"] = store_id

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
def get_historical_metrics(
    store_id: str = Query(..., description="Store ID"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO8601)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO8601)"),
    bucket: str = Query("hourly", regex="^(hourly|daily)$", description="Aggregation bucket"),
    db: Session = Depends(get_db_session)
):
    """
    Get historical aggregated metrics.

    Query params:
        store_id: Store identifier
        from_date: Start date (defaults to today)
        to_date: End date (defaults to today)
        bucket: 'hourly' or 'daily'

    Returns:
        {
            "period": {"from": "...", "to": "...", "bucket": "hourly"},
            "footfall": N,
            "unique_visitors": N,
            "zones": {...},
            "shelves": {...},
            "queue": {...}
        }
    """
    try:
        # Verify store exists
        store = db.query(StoreExtended).filter_by(store_id=store_id, is_active=True).first()
        if not store:
            raise HTTPException(status_code=404, detail=f"Store {store_id} not found")

        # Parse dates
        if not from_date:
            from_ts = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            try:
                from_ts = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            except:
                from_ts = datetime.strptime(from_date, "%Y-%m-%d")

        if not to_date:
            to_ts = datetime.utcnow()
        else:
            try:
                to_ts = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            except:
                to_ts = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

        # Get aggregator
        aggregator = get_aggregator(store_id, db)

        # Get historical metrics
        metrics = aggregator.aggregate_historical(from_ts, to_ts, bucket=bucket)
        metrics["store_id"] = store_id

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting historical metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cameras")
def get_cameras(
    store_id: str = Query(..., description="Store ID"),
    db: Session = Depends(get_db_session)
):
    """
    Get cameras for a store with capability badges.

    Returns:
        {
            "cameras": [
                {
                    "camera_id": "...",
                    "name": "...",
                    "capabilities": ["entrance", "zones"],
                    "status": "online" | "offline"
                }
            ]
        }
    """
    try:
        cameras = db.query(CameraExtended).filter_by(
            store_id=store_id,
            is_active=True
        ).all()

        # Get aggregator for status lookup
        aggregator = get_aggregator(store_id, db)

        result = []
        for camera in cameras:
            status_data = aggregator._get_camera_status(camera.camera_id)

            result.append({
                "camera_id": camera.camera_id,
                "name": camera.name,
                "capabilities": camera.capabilities,
                "status": "online" if status_data.get("online") else "offline",
                "last_heartbeat": status_data.get("last_heartbeat")
            })

        return {"cameras": result}

    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e))