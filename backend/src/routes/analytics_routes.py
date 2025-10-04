"""
Analytics routes with real-time aggregation from events table.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List

from ..database.models_production import User, Event
from ..database.connection import get_db
from .auth_routes import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Response Models
class HourlyDataPoint(BaseModel):
    hour: str
    footfall: int


class DailyDataPoint(BaseModel):
    date: str
    footfall: int


class CameraFootfallDataPoint(BaseModel):
    date: str
    camera_name: str
    footfall: int


class DashboardKPIs(BaseModel):
    today_footfall: int
    avg_dwell_seconds: float
    total_shelf_interactions: int
    active_cameras: int


class HourlyFootfallResponse(BaseModel):
    hours: List[HourlyDataPoint]


class DailyFootfallResponse(BaseModel):
    series: List[DailyDataPoint]


class DailyCameraFootfallResponse(BaseModel):
    series: List[CameraFootfallDataPoint]


# Routes
@router.get("/dashboard_kpis", response_model=DashboardKPIs)
async def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time KPIs for dashboard.
    """
    from ..database.models_production import Camera

    store_id = current_user.store_id
    if not store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not assigned to a store")

    # Today's footfall (footfall_in events)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_footfall = db.query(func.count(Event.id)).filter(
        Event.store_id == store_id,
        Event.type == "footfall_in",
        Event.ts >= today_start
    ).scalar() or 0

    # Avg dwell time (dwell events) - calculate in Python for SQLite compatibility
    dwell_events = db.query(Event.payload).filter(
        Event.store_id == store_id,
        Event.type == "dwell",
        Event.ts >= today_start
    ).all()

    dwell_times = [e.payload.get("dwell_seconds", 0) if isinstance(e.payload, dict) else 0 for e in dwell_events]
    avg_dwell = sum(dwell_times) / len(dwell_times) if dwell_times else 0.0

    # Total shelf interactions
    total_shelf_interactions = db.query(func.count(Event.id)).filter(
        Event.store_id == store_id,
        Event.type == "shelf_interaction",
        Event.ts >= today_start
    ).scalar() or 0

    # Active cameras
    active_cameras = db.query(func.count(Camera.camera_id)).filter(
        Camera.store_id == store_id,
        Camera.is_active == True
    ).scalar() or 0

    return {
        "today_footfall": today_footfall,
        "avg_dwell_seconds": float(avg_dwell),
        "total_shelf_interactions": total_shelf_interactions,
        "active_cameras": active_cameras
    }


@router.get("/hourly_footfall", response_model=HourlyFootfallResponse)
async def get_hourly_footfall(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get hourly footfall for today.
    """
    store_id = current_user.store_id
    if not store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not assigned to a store")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Query events grouped by hour
    results = db.query(
        func.extract('hour', Event.ts).label('hour'),
        func.count(Event.id).label('footfall')
    ).filter(
        Event.store_id == store_id,
        Event.type == "footfall_in",
        Event.ts >= today_start
    ).group_by('hour').all()

    # Convert to hour labels
    hour_map = {int(r.hour): r.footfall for r in results}
    hours = []
    for h in range(24):
        label = f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"
        hours.append({
            "hour": label,
            "footfall": hour_map.get(h, 0)
        })

    return {"hours": hours}


@router.get("/footfall_daily", response_model=DailyFootfallResponse)
async def get_daily_footfall(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily footfall for last N days.
    """
    store_id = current_user.store_id
    if not store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not assigned to a store")

    start_date = datetime.utcnow() - timedelta(days=days)

    # Query events grouped by day
    results = db.query(
        func.date(Event.ts).label('date'),
        func.count(Event.id).label('footfall')
    ).filter(
        Event.store_id == store_id,
        Event.type == "footfall_in",
        Event.ts >= start_date
    ).group_by('date').order_by('date').all()

    series = [
        {
            "date": r.date.isoformat(),
            "footfall": r.footfall
        }
        for r in results
    ]

    return {"series": series}


@router.get("/daily_by_camera", response_model=DailyCameraFootfallResponse)
async def get_daily_by_camera(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily footfall grouped by camera.
    """
    from ..database.models_production import Camera

    store_id = current_user.store_id
    if not store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not assigned to a store")

    start_date = datetime.utcnow() - timedelta(days=days)

    # Query events grouped by day and camera
    results = db.query(
        func.date(Event.ts).label('date'),
        Camera.name.label('camera_name'),
        func.count(Event.id).label('footfall')
    ).join(
        Camera, Event.camera_id == Camera.camera_id
    ).filter(
        Event.store_id == store_id,
        Event.type == "footfall_in",
        Event.ts >= start_date
    ).group_by('date', Camera.name).order_by('date').all()

    series = [
        {
            "date": r.date.isoformat(),
            "camera_name": r.camera_name,
            "footfall": r.footfall
        }
        for r in results
    ]

    return {"series": series}
