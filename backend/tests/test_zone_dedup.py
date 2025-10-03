"""
Test zone unique visitors deduplication logic.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import func

from src.database.models_production import Event
from .conftest import create_test_event


def test_zone_unique_visitors_single_camera(db_session, test_org, test_store, test_camera_zone):
    """Test unique visitor counting in zones - same person multiple times should count once."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)
    zone_id = "electronics"

    # Person 1 visits electronics zone 5 times
    for i in range(5):
        create_test_event(
            db_session,
            event_id=f"zone-p1-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="zone_dwell",
            timestamp=base_time + timedelta(minutes=i),
            person_key="person-001",
            payload={"zone_id": zone_id, "dwell_seconds": 10.0}
        )

    # Person 2 visits electronics zone 3 times
    for i in range(3):
        create_test_event(
            db_session,
            event_id=f"zone-p2-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="zone_dwell",
            timestamp=base_time + timedelta(minutes=10 + i),
            person_key="person-002",
            payload={"zone_id": zone_id, "dwell_seconds": 15.0}
        )

    # Person 3 visits electronics zone once
    create_test_event(
        db_session,
        event_id="zone-p3-0",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_dwell",
        timestamp=base_time + timedelta(minutes=20),
        person_key="person-003",
        payload={"zone_id": zone_id, "dwell_seconds": 20.0}
    )

    # Query unique visitors to electronics zone
    unique_visitors = (
        db_session.query(func.count(func.distinct(Event.person_key)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "zone_dwell",
            Event.payload["zone_id"].astext == zone_id
        )
        .scalar()
    )

    # Should count 3 unique visitors despite 9 total events
    assert unique_visitors == 3


def test_zone_unique_visitors_multiple_zones(db_session, test_org, test_store, test_camera_zone):
    """Test unique visitor counting across different zones."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Person 1 visits both electronics and toys
    create_test_event(
        db_session,
        event_id="p1-electronics",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_dwell",
        timestamp=base_time,
        person_key="person-001",
        payload={"zone_id": "electronics", "dwell_seconds": 30.0}
    )

    create_test_event(
        db_session,
        event_id="p1-toys",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_dwell",
        timestamp=base_time + timedelta(minutes=5),
        person_key="person-001",
        payload={"zone_id": "toys", "dwell_seconds": 20.0}
    )

    # Person 2 visits only electronics
    create_test_event(
        db_session,
        event_id="p2-electronics",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_dwell",
        timestamp=base_time + timedelta(minutes=10),
        person_key="person-002",
        payload={"zone_id": "electronics", "dwell_seconds": 25.0}
    )

    # Query unique visitors per zone
    electronics_visitors = (
        db_session.query(func.count(func.distinct(Event.person_key)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "zone_dwell",
            Event.payload["zone_id"].astext == "electronics"
        )
        .scalar()
    )

    toys_visitors = (
        db_session.query(func.count(func.distinct(Event.person_key)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "zone_dwell",
            Event.payload["zone_id"].astext == "toys"
        )
        .scalar()
    )

    assert electronics_visitors == 2  # person-001 and person-002
    assert toys_visitors == 1  # only person-001


def test_zone_dedup_across_cameras(db_session, test_org, test_store):
    """Test cross-camera deduplication for zone analytics."""
    from src.database.models_production import Camera

    # Create two cameras covering same zone
    cam1 = Camera(
        camera_id="zone-cam-1",
        store_id=test_store.store_id,
        name="Zone Camera 1",
        is_entrance=False,
        config={"geometry": {"zones": {"electronics": [[0, 0], [100, 0], [100, 100], [0, 100]]}}}
    )
    cam2 = Camera(
        camera_id="zone-cam-2",
        store_id=test_store.store_id,
        name="Zone Camera 2",
        is_entrance=False,
        config={"geometry": {"zones": {"electronics": [[100, 0], [200, 0], [200, 100], [100, 100]]}}}
    )
    db_session.add_all([cam1, cam2])
    db_session.commit()

    base_time = datetime(2025, 1, 10, 10, 0, 0)
    zone_id = "electronics"

    # Same person detected by both cameras (should count as 1 visitor)
    create_test_event(
        db_session,
        event_id="cam1-p1",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=cam1.camera_id,
        event_type="zone_dwell",
        timestamp=base_time,
        person_key="person-001",
        payload={"zone_id": zone_id, "dwell_seconds": 10.0}
    )

    create_test_event(
        db_session,
        event_id="cam2-p1",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=cam2.camera_id,
        event_type="zone_dwell",
        timestamp=base_time + timedelta(seconds=5),
        person_key="person-001",
        payload={"zone_id": zone_id, "dwell_seconds": 15.0}
    )

    # Different person on cam2
    create_test_event(
        db_session,
        event_id="cam2-p2",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=cam2.camera_id,
        event_type="zone_dwell",
        timestamp=base_time + timedelta(minutes=1),
        person_key="person-002",
        payload={"zone_id": zone_id, "dwell_seconds": 20.0}
    )

    # Query unique visitors across all cameras
    unique_visitors = (
        db_session.query(func.count(func.distinct(Event.person_key)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "zone_dwell",
            Event.payload["zone_id"].astext == zone_id
        )
        .scalar()
    )

    # Should count 2 unique visitors despite 3 events
    assert unique_visitors == 2


def test_zone_live_count(db_session, test_org, test_store, test_camera_zone):
    """Test live zone occupancy counting (people currently in zone)."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)
    zone_id = "electronics"

    # Create zone_enter and zone_exit events
    # Person 1 enters and exits
    create_test_event(
        db_session,
        event_id="p1-enter",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_enter",
        timestamp=base_time,
        person_key="person-001",
        payload={"zone_id": zone_id}
    )

    create_test_event(
        db_session,
        event_id="p1-exit",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_exit",
        timestamp=base_time + timedelta(minutes=5),
        person_key="person-001",
        payload={"zone_id": zone_id}
    )

    # Person 2 enters but hasn't exited (still in zone)
    create_test_event(
        db_session,
        event_id="p2-enter",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_enter",
        timestamp=base_time + timedelta(minutes=3),
        person_key="person-002",
        payload={"zone_id": zone_id}
    )

    # Person 3 enters but hasn't exited (still in zone)
    create_test_event(
        db_session,
        event_id="p3-enter",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="zone_enter",
        timestamp=base_time + timedelta(minutes=7),
        person_key="person-003",
        payload={"zone_id": zone_id}
    )

    # Query people currently in zone (entered but not exited)
    from sqlalchemy import and_, exists

    people_in_zone = (
        db_session.query(Event.person_key)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "zone_enter",
            Event.payload["zone_id"].astext == zone_id
        )
        .filter(
            ~exists().where(
                and_(
                    Event.person_key == Event.person_key,
                    Event.type == "zone_exit",
                    Event.payload["zone_id"].astext == zone_id
                )
            )
        )
        .distinct()
        .all()
    )

    # Should show 2 people still in zone (person-002 and person-003)
    person_keys = [p.person_key for p in people_in_zone]
    assert len(person_keys) == 2
    assert "person-002" in person_keys
    assert "person-003" in person_keys
    assert "person-001" not in person_keys  # Exited
