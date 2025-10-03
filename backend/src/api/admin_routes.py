import os
import logging
import secrets
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..database.models_production import Org, Store, Camera, EdgeKey

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


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


class CreateOrgRequest(BaseModel):
    org_id: str
    name: str


class CreateStoreRequest(BaseModel):
    store_id: str
    org_id: str
    name: str
    timezone: str = "UTC"


class CreateCameraRequest(BaseModel):
    camera_id: str
    store_id: str
    name: str
    capabilities: List[str]
    config: Optional[dict] = None


class CreateEdgeKeyRequest(BaseModel):
    org_id: str
    store_id: str
    camera_id: str


@router.post("/orgs")
def create_org(req: CreateOrgRequest, db: Session = Depends(get_db)):
    existing = db.query(Org).filter(Org.org_id == req.org_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Org already exists")

    org = Org(org_id=req.org_id, name=req.name)
    db.add(org)
    db.commit()
    db.refresh(org)

    logger.info(f"Created org: {req.org_id}")
    return {"org_id": org.org_id, "name": org.name}


@router.post("/stores")
def create_store(req: CreateStoreRequest, db: Session = Depends(get_db)):
    org = db.query(Org).filter(Org.org_id == req.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    existing = db.query(Store).filter(Store.store_id == req.store_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Store already exists")

    store = Store(
        store_id=req.store_id,
        org_id=req.org_id,
        name=req.name,
        timezone=req.timezone
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    logger.info(f"Created store: {req.store_id}")
    return {"store_id": store.store_id, "org_id": store.org_id, "name": store.name}


@router.post("/cameras")
def create_camera(req: CreateCameraRequest, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == req.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    valid_capabilities = {"entrance", "zones", "shelves", "queue"}
    for cap in req.capabilities:
        if cap not in valid_capabilities:
            raise HTTPException(status_code=400, detail=f"Invalid capability: {cap}")

    existing = db.query(Camera).filter(Camera.camera_id == req.camera_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Camera already exists")

    camera = Camera(
        camera_id=req.camera_id,
        store_id=req.store_id,
        name=req.name,
        capabilities=req.capabilities,
        config=req.config or {}
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    logger.info(f"Created camera: {req.camera_id}")
    return {
        "camera_id": camera.camera_id,
        "store_id": camera.store_id,
        "name": camera.name,
        "capabilities": camera.capabilities
    }


@router.post("/edge-keys")
def create_edge_key(req: CreateEdgeKeyRequest, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.camera_id == req.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    token = f"sk_edge_{secrets.token_urlsafe(32)}"

    edge_key = EdgeKey(
        token=token,
        org_id=req.org_id,
        store_id=req.store_id,
        camera_id=req.camera_id,
        active=True
    )
    db.add(edge_key)
    db.commit()
    db.refresh(edge_key)

    logger.info(f"Created edge key for camera: {req.camera_id}")
    return {
        "token": token,
        "org_id": req.org_id,
        "store_id": req.store_id,
        "camera_id": req.camera_id,
        "message": "Store this token securely - it cannot be retrieved later"
    }


@router.get("/orgs")
def list_orgs(db: Session = Depends(get_db)):
    orgs = db.query(Org).all()
    return {"orgs": [{"org_id": o.org_id, "name": o.name} for o in orgs]}


@router.get("/stores")
def list_stores(org_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Store)
    if org_id:
        query = query.filter(Store.org_id == org_id)
    stores = query.all()
    return {
        "stores": [
            {"store_id": s.store_id, "org_id": s.org_id, "name": s.name, "timezone": s.timezone}
            for s in stores
        ]
    }


@router.get("/cameras")
def list_cameras(store_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Camera)
    if store_id:
        query = query.filter(Camera.store_id == store_id)
    cameras = query.all()
    return {
        "cameras": [
            {
                "camera_id": c.camera_id,
                "store_id": c.store_id,
                "name": c.name,
                "capabilities": c.capabilities
            }
            for c in cameras
        ]
    }
