"""
Camera routes with JWT authentication and zone support.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from ..database.models_production import User, Camera
from ..database.connection import get_db
from .auth_routes import get_current_user

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


# Request/Response Models
class ZoneSchema(BaseModel):
    zone_id: str
    name: str
    type: str  # "line", "polygon"
    coordinates: List[List[int]]
    direction: Optional[str] = None
    shelf_category: Optional[str] = None


class CameraCreateRequest(BaseModel):
    name: str
    rtsp_url: str
    is_entrance: bool = False
    capabilities: List[str]
    zones: List[ZoneSchema] = []


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    is_entrance: Optional[bool] = None
    capabilities: Optional[List[str]] = None
    zones: Optional[List[ZoneSchema]] = None
    is_active: Optional[bool] = None


class CameraResponse(BaseModel):
    camera_id: str
    store_id: str
    name: str
    is_entrance: bool
    rtsp_url: str | None
    capabilities: List[str] | None
    zones: List[ZoneSchema]
    last_heartbeat_at: str | None
    is_active: bool

    class Config:
        from_attributes = True


# Routes
@router.get("/", response_model=List[CameraResponse])
async def list_cameras(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all cameras for the user's store.
    Requires JWT authentication.
    """
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not assigned to a store",
        )

    cameras = db.query(Camera).filter(
        Camera.store_id == current_user.store_id
    ).all()

    result = []
    for camera in cameras:
        zones = camera.config.get("zones", []) if camera.config else []
        result.append({
            "camera_id": camera.camera_id,
            "store_id": camera.store_id,
            "name": camera.name,
            "is_entrance": camera.is_entrance,
            "rtsp_url": camera.rtsp_url,
            "capabilities": camera.capabilities,
            "zones": zones,
            "last_heartbeat_at": camera.last_heartbeat_at.isoformat() if camera.last_heartbeat_at else None,
            "is_active": camera.is_active
        })

    return result


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific camera by ID.
    Requires JWT authentication.
    """
    camera = db.query(Camera).filter(
        Camera.camera_id == camera_id,
        Camera.store_id == current_user.store_id
    ).first()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    zones = camera.config.get("zones", []) if camera.config else []

    return {
        "camera_id": camera.camera_id,
        "store_id": camera.store_id,
        "name": camera.name,
        "is_entrance": camera.is_entrance,
        "rtsp_url": camera.rtsp_url,
        "capabilities": camera.capabilities,
        "zones": zones,
        "last_heartbeat_at": camera.last_heartbeat_at.isoformat() if camera.last_heartbeat_at else None,
        "is_active": camera.is_active
    }


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_data: CameraCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new camera for the store.
    Maximum 3 cameras per store.
    Requires JWT authentication.
    """
    if not current_user.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not assigned to a store",
        )

    # Check camera limit (max 3 per store)
    camera_count = db.query(Camera).filter(
        Camera.store_id == current_user.store_id
    ).count()

    if camera_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 3 cameras per store allowed",
        )

    # Create camera
    camera_id = f"cam_{uuid.uuid4().hex[:12]}"

    config = {
        "zones": [zone.dict() for zone in camera_data.zones]
    }

    new_camera = Camera(
        camera_id=camera_id,
        store_id=current_user.store_id,
        name=camera_data.name,
        rtsp_url=camera_data.rtsp_url,
        is_entrance=camera_data.is_entrance,
        capabilities=camera_data.capabilities,
        config=config,
        is_active=True
    )

    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)

    return {
        "camera_id": new_camera.camera_id,
        "store_id": new_camera.store_id,
        "name": new_camera.name,
        "is_entrance": new_camera.is_entrance,
        "rtsp_url": new_camera.rtsp_url,
        "capabilities": new_camera.capabilities,
        "zones": camera_data.zones,
        "last_heartbeat_at": None,
        "is_active": new_camera.is_active
    }


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: str,
    camera_data: CameraUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update camera configuration.
    Requires JWT authentication.
    """
    camera = db.query(Camera).filter(
        Camera.camera_id == camera_id,
        Camera.store_id == current_user.store_id
    ).first()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    # Update fields
    if camera_data.name is not None:
        camera.name = camera_data.name
    if camera_data.rtsp_url is not None:
        camera.rtsp_url = camera_data.rtsp_url
    if camera_data.is_entrance is not None:
        camera.is_entrance = camera_data.is_entrance
    if camera_data.capabilities is not None:
        camera.capabilities = camera_data.capabilities
    if camera_data.is_active is not None:
        camera.is_active = camera_data.is_active
    if camera_data.zones is not None:
        camera.config = {
            "zones": [zone.dict() for zone in camera_data.zones]
        }

    db.commit()
    db.refresh(camera)

    zones = camera.config.get("zones", []) if camera.config else []

    return {
        "camera_id": camera.camera_id,
        "store_id": camera.store_id,
        "name": camera.name,
        "is_entrance": camera.is_entrance,
        "rtsp_url": camera.rtsp_url,
        "capabilities": camera.capabilities,
        "zones": zones,
        "last_heartbeat_at": camera.last_heartbeat_at.isoformat() if camera.last_heartbeat_at else None,
        "is_active": camera.is_active
    }


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a camera.
    Requires JWT authentication.
    """
    camera = db.query(Camera).filter(
        Camera.camera_id == camera_id,
        Camera.store_id == current_user.store_id
    ).first()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    db.delete(camera)
    db.commit()

    return None
