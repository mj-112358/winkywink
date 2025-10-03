"""
Test bulk event ingestion with idempotency guarantees.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.database.models_production import Event
from .conftest import create_test_event


def test_bulk_ingest_idempotency(db_session, test_org, test_store, test_camera_entrance):
    """Test that duplicate event_id insertions are rejected."""
    event_id = "evt-12345-unique"
    timestamp = datetime.utcnow()

    # First insertion should succeed
    event1 = create_test_event(
        db_session,
        event_id=event_id,
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_entrance.camera_id,
        event_type="entrance",
        timestamp=timestamp,
        person_key="person-001"
    )

    assert event1.id is not None
    assert event1.event_id == event_id

    # Second insertion with same event_id should fail
    with pytest.raises(IntegrityError):
        create_test_event(
            db_session,
            event_id=event_id,  # Same event_id
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=timestamp,
            person_key="person-002"  # Different person
        )

    # Verify only one event exists
    db_session.rollback()
    count = db_session.query(Event).filter(Event.event_id == event_id).count()
    assert count == 1


def test_bulk_ingest_multiple_events(db_session, test_org, test_store, test_camera_entrance):
    """Test inserting multiple events with unique event_ids."""
    timestamp = datetime.utcnow()

    events_data = [
        ("evt-001", "entrance", "person-001"),
        ("evt-002", "entrance", "person-002"),
        ("evt-003", "entrance", "person-003"),
    ]

    for event_id, event_type, person_key in events_data:
        create_test_event(
            db_session,
            event_id=event_id,
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type=event_type,
            timestamp=timestamp,
            person_key=person_key
        )

    # Verify all events were inserted
    count = db_session.query(Event).count()
    assert count == 3


def test_event_id_uniqueness_across_stores(db_session, test_org):
    """Test that event_id is globally unique, not just per store."""
    from src.database.models_production import Store, Camera

    # Create two stores
    store1 = Store(store_id="store-001", org_id=test_org.org_id, name="Store 1", timezone="UTC")
    store2 = Store(store_id="store-002", org_id=test_org.org_id, name="Store 2", timezone="UTC")
    db_session.add_all([store1, store2])
    db_session.commit()

    # Create cameras for each store
    cam1 = Camera(camera_id="cam-001", store_id=store1.store_id, name="Cam 1", is_entrance=True)
    cam2 = Camera(camera_id="cam-002", store_id=store2.store_id, name="Cam 2", is_entrance=True)
    db_session.add_all([cam1, cam2])
    db_session.commit()

    event_id = "global-unique-event-001"
    timestamp = datetime.utcnow()

    # Insert event in store 1
    create_test_event(
        db_session,
        event_id=event_id,
        org_id=test_org.org_id,
        store_id=store1.store_id,
        camera_id=cam1.camera_id,
        event_type="entrance",
        timestamp=timestamp
    )

    # Try to insert same event_id in store 2 - should fail
    with pytest.raises(IntegrityError):
        create_test_event(
            db_session,
            event_id=event_id,  # Same event_id
            org_id=test_org.org_id,
            store_id=store2.store_id,
            camera_id=cam2.camera_id,
            event_type="entrance",
            timestamp=timestamp
        )


def test_event_payload_storage(db_session, test_org, test_store, test_camera_entrance):
    """Test that event payloads are stored correctly."""
    timestamp = datetime.utcnow()

    payload = {
        "zone_id": "electronics",
        "dwell_seconds": 45.2,
        "confidence": 0.95,
        "bbox": [100, 200, 150, 250]
    }

    event = create_test_event(
        db_session,
        event_id="evt-payload-test",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_entrance.camera_id,
        event_type="zone_dwell",
        timestamp=timestamp,
        payload=payload
    )

    # Retrieve and verify payload
    retrieved = db_session.query(Event).filter(Event.event_id == "evt-payload-test").first()
    assert retrieved.payload == payload
    assert retrieved.payload["dwell_seconds"] == 45.2
    assert retrieved.payload["zone_id"] == "electronics"
