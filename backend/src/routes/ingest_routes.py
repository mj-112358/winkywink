"""
Event ingestion routes for edge devices.
Uses X-EDGE-KEY header for authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import List

from ..database.models_production import EdgeKey, Event
from ..database.connection import get_db

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


# Request Models
class EventPayload(BaseModel):
    event_id: str
    camera_id: str
    person_key: str | None = None
    type: str  # "footfall_in", "footfall_out", "shelf_interaction", "dwell"
    ts: datetime
    payload: dict | None = None


class IngestRequest(BaseModel):
    events: List[EventPayload]


class IngestResponse(BaseModel):
    received: int
    inserted: int
    duplicates: int


# Dependency to validate edge key
async def validate_edge_key(
    x_edge_key: str = Header(...),
    db: Session = Depends(get_db)
) -> EdgeKey:
    """
    Validate X-EDGE-KEY header and return the edge key record.
    """
    edge_key = db.query(EdgeKey).filter(
        EdgeKey.key == x_edge_key,
        EdgeKey.active == True
    ).first()

    if not edge_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive edge key",
        )

    return edge_key


# Routes
@router.post("/events", response_model=IngestResponse)
async def ingest_events(
    ingest_data: IngestRequest,
    edge_key: EdgeKey = Depends(validate_edge_key),
    db: Session = Depends(get_db)
):
    """
    Ingest events from edge device.
    Requires X-EDGE-KEY header for authentication.
    Uses event_id for idempotency.
    """
    received = len(ingest_data.events)
    inserted = 0
    duplicates = 0

    for event_data in ingest_data.events:
        try:
            # Create event with org_id and store_id from edge key
            event = Event(
                event_id=event_data.event_id,
                org_id=edge_key.org_id,
                store_id=edge_key.store_id,
                camera_id=event_data.camera_id,
                person_key=event_data.person_key,
                type=event_data.type,
                ts=event_data.ts,
                payload=event_data.payload
            )

            db.add(event)
            db.commit()
            inserted += 1

        except IntegrityError:
            # Duplicate event_id - skip silently
            db.rollback()
            duplicates += 1

        except Exception as e:
            db.rollback()
            print(f"Error inserting event {event_data.event_id}: {e}")
            # Continue processing other events

    return {
        "received": received,
        "inserted": inserted,
        "duplicates": duplicates
    }


@router.post("/heartbeat")
async def heartbeat(
    edge_key: EdgeKey = Depends(validate_edge_key),
    db: Session = Depends(get_db)
):
    """
    Heartbeat endpoint for edge devices.
    Updates last_heartbeat_at for all cameras in the store.
    """
    from ..database.models_production import Camera

    # Update all cameras in this store
    db.query(Camera).filter(
        Camera.store_id == edge_key.store_id
    ).update({
        "last_heartbeat_at": datetime.utcnow()
    })

    db.commit()

    return {"status": "ok", "store_id": edge_key.store_id}
