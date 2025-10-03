import os
import logging
from datetime import datetime
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from ..database.models_production import EdgeKey, Event

logger = logging.getLogger(__name__)

# Create routers for both v1 and legacy api endpoints
router_v1 = APIRouter(prefix="/v1", tags=["ingestion-v1"])
router_api = APIRouter(prefix="/api/ingest", tags=["ingestion-legacy"])


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


def authenticate_edge(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Authenticate edge device via Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "").strip()

    edge_key = db.query(EdgeKey).filter(EdgeKey.token == token, EdgeKey.active == True).first()
    if not edge_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive edge key")

    # Update last_seen timestamp
    edge_key.last_seen = datetime.utcnow()
    db.commit()

    return {
        "org_id": edge_key.org_id,
        "store_id": edge_key.store_id,
        "camera_id": edge_key.camera_id,
        "token": token
    }


# Pydantic Models for V1 API
class V1HeartbeatRequest(BaseModel):
    org_id: str
    store_id: str
    camera_ids: List[str]
    ts: str


class V1IngestEvent(BaseModel):
    """Event schema matching edge runtime v2 output."""
    event_id: str = Field(..., description="SHA256 hash for idempotency")
    org_id: str
    store_id: str
    camera_id: str
    type: Literal["entrance", "zone_dwell", "shelf_interaction", "queue_presence"]
    ts: str
    payload: dict


class V1EventsBulkRequest(BaseModel):
    """Bulk events request from edge runtime."""
    events: List[V1IngestEvent]


# Legacy Pydantic Models
class HeartbeatRequest(BaseModel):
    org_id: str
    store_id: str
    camera_id: str


class IngestEvent(BaseModel):
    type: Literal["entrance", "zone_dwell", "shelf_interaction", "queue_presence"]
    ts: datetime
    person_key: Optional[str] = None
    payload: dict


class IngestBatch(BaseModel):
    org_id: str
    store_id: str
    camera_id: str
    events: List[IngestEvent]


# V1 API Endpoints (used by edge_runtime_v2.py)
@router_v1.post("/ingest/heartbeat")
def v1_post_heartbeat(
    req: V1HeartbeatRequest,
    auth=Depends(authenticate_edge),
    db: Session = Depends(get_db)
):
    """
    Receive heartbeat from edge device.
    Updates last_seen timestamp for monitoring.
    """
    if req.org_id != auth["org_id"] or req.store_id != auth["store_id"]:
        raise HTTPException(status_code=403, detail="Token scope mismatch")

    logger.debug(f"Heartbeat from {req.org_id}/{req.store_id} - cameras: {len(req.camera_ids)}")

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "cameras_count": len(req.camera_ids)
    }


@router_v1.post("/events/bulk")
def v1_post_events_bulk(
    req: V1EventsBulkRequest,
    auth=Depends(authenticate_edge),
    db: Session = Depends(get_db)
):
    """
    Idempotent bulk event ingestion.
    Uses event_id for deduplication - duplicate events are ignored.
    """
    if not req.events:
        return {"status": "ok", "inserted": 0, "duplicates": 0}

    # Verify auth scope matches first event (all should be from same org/store)
    if req.events:
        first_evt = req.events[0]
        if first_evt.org_id != auth["org_id"] or first_evt.store_id != auth["store_id"]:
            raise HTTPException(status_code=403, detail="Token scope mismatch")

    inserted = 0
    duplicates = 0

    for evt in req.events:
        try:
            # Parse timestamp
            ts = datetime.fromisoformat(evt.ts.replace("Z", "+00:00"))

            # Extract person_key from payload if present
            person_key = evt.payload.get("person_id") or evt.payload.get("person_key")

            event_row = Event(
                event_id=evt.event_id,
                org_id=evt.org_id,
                store_id=evt.store_id,
                camera_id=evt.camera_id,
                person_key=person_key,
                type=evt.type,
                ts=ts,
                payload=evt.payload
            )
            db.add(event_row)
            db.flush()
            inserted += 1

        except IntegrityError as e:
            # Duplicate event_id - this is expected for idempotency
            db.rollback()
            duplicates += 1
            logger.debug(f"Duplicate event_id: {evt.event_id}")
            continue
        except Exception as e:
            db.rollback()
            logger.error(f"Error inserting event: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to insert event: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to commit batch: {str(e)}")

    logger.info(f"Bulk ingest: {inserted} inserted, {duplicates} duplicates from {auth['store_id']}/{auth['camera_id']}")

    # Optional: Publish to Redis for live dashboard
    try:
        publish_event_summary(req.events, inserted)
    except Exception as e:
        logger.warning(f"Failed to publish to Redis: {e}")

    return {
        "status": "ok",
        "inserted": inserted,
        "duplicates": duplicates,
        "total": len(req.events)
    }


# Legacy API Endpoints (backward compatibility)
@router_api.post("/heartbeat")
def post_heartbeat(
    req: HeartbeatRequest,
    auth=Depends(authenticate_edge),
    db: Session = Depends(get_db)
):
    """Legacy heartbeat endpoint."""
    if req.org_id != auth["org_id"] or req.store_id != auth["store_id"] or req.camera_id != auth["camera_id"]:
        raise HTTPException(status_code=403, detail="Token scope mismatch")

    logger.info(f"Heartbeat from {req.store_id}/{req.camera_id}")
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router_api.post("/events")
def post_events(
    batch: IngestBatch,
    auth=Depends(authenticate_edge),
    db: Session = Depends(get_db)
):
    """
    Legacy event ingestion endpoint.
    Note: This does not use event_id for idempotency.
    """
    if batch.org_id != auth["org_id"] or batch.store_id != auth["store_id"] or batch.camera_id != auth["camera_id"]:
        raise HTTPException(status_code=403, detail="Token scope mismatch")

    if not batch.events:
        return {"status": "ok", "inserted": 0}

    inserted = 0
    for evt in batch.events:
        try:
            # Generate event_id if not present (for legacy compatibility)
            import hashlib
            event_id_data = f"{batch.camera_id}|{evt.person_key}|{evt.ts.isoformat()}|{evt.type}"
            event_id = hashlib.sha256(event_id_data.encode()).hexdigest()

            event_row = Event(
                event_id=event_id,
                org_id=batch.org_id,
                store_id=batch.store_id,
                camera_id=batch.camera_id,
                person_key=evt.person_key,
                type=evt.type,
                ts=evt.ts,
                payload=evt.payload
            )
            db.add(event_row)
            db.flush()
            inserted += 1
        except IntegrityError:
            db.rollback()
            continue
        except Exception as e:
            db.rollback()
            logger.error(f"Error inserting event: {e}")
            continue

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"Ingested {inserted} events from {batch.store_id}/{batch.camera_id}")

    return {"status": "ok", "inserted": inserted}


def publish_event_summary(events: List[V1IngestEvent], count: int):
    """
    Publish event summary to Redis for live dashboard updates.
    Optional feature - gracefully fails if Redis is not available.
    """
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url, decode_responses=True)

        # Group events by store
        store_summaries = {}
        for evt in events:
            store_id = evt.store_id
            if store_id not in store_summaries:
                store_summaries[store_id] = {"footfall": 0, "zones": 0, "shelves": 0, "queues": 0}

            if evt.type == "entrance" and evt.payload.get("direction") == "in":
                store_summaries[store_id]["footfall"] += 1
            elif evt.type == "zone_dwell":
                store_summaries[store_id]["zones"] += 1
            elif evt.type == "shelf_interaction":
                store_summaries[store_id]["shelves"] += 1
            elif evt.type == "queue_presence":
                store_summaries[store_id]["queues"] += 1

        # Publish to Redis channel
        for store_id, summary in store_summaries.items():
            channel = f"live_updates:{store_id}"
            message = {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": summary
            }
            r.publish(channel, str(message))

    except ImportError:
        logger.debug("Redis not available - skipping live updates")
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")


# Export both routers
routers = [router_v1, router_api]
