"""
Test footfall counting logic - only from entrance cameras.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import func

from src.database.models_production import Event, Camera
from .conftest import create_test_event


def test_footfall_only_entrance_cameras(db_session, test_org, test_store, test_camera_entrance, test_camera_zone):
    """Test that footfall only counts events from cameras with is_entrance=True."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Create entrance events from entrance camera
    for i in range(5):
        create_test_event(
            db_session,
            event_id=f"entrance-evt-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-{i}"
        )

    # Create entrance events from zone camera (should NOT count)
    for i in range(3):
        create_test_event(
            db_session,
            event_id=f"zone-evt-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="entrance",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-zone-{i}"
        )

    # Query footfall from entrance cameras only
    footfall_count = (
        db_session.query(func.count(Event.id))
        .join(Camera, Event.camera_id == Camera.camera_id)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance",
            Camera.is_entrance == True
        )
        .scalar()
    )

    # Should only count the 5 events from entrance camera
    assert footfall_count == 5


def test_footfall_by_hour(db_session, test_org, test_store, test_camera_entrance):
    """Test footfall aggregation by hour."""
    base_date = datetime(2025, 1, 10, 0, 0, 0)

    # Create events across different hours
    hourly_counts = {
        9: 10,   # 9 AM: 10 visitors
        10: 15,  # 10 AM: 15 visitors
        11: 20,  # 11 AM: 20 visitors (peak)
        12: 18,  # 12 PM: 18 visitors
        14: 5,   # 2 PM: 5 visitors
    }

    event_counter = 0
    for hour, count in hourly_counts.items():
        for i in range(count):
            create_test_event(
                db_session,
                event_id=f"footfall-h{hour}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(hours=hour, minutes=i),
                person_key=f"person-{event_counter}"
            )
            event_counter += 1

    # Query footfall by hour
    from sqlalchemy import extract
    hourly_result = (
        db_session.query(
            extract('hour', Event.ts).label('hour'),
            func.count(Event.id).label('count')
        )
        .join(Camera, Event.camera_id == Camera.camera_id)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance",
            Camera.is_entrance == True
        )
        .group_by('hour')
        .order_by('hour')
        .all()
    )

    # Verify hourly counts
    result_dict = {int(row.hour): row.count for row in hourly_result}
    assert result_dict[9] == 10
    assert result_dict[10] == 15
    assert result_dict[11] == 20  # Peak hour
    assert result_dict[12] == 18
    assert result_dict[14] == 5

    # Verify peak hour
    peak_hour = max(result_dict.items(), key=lambda x: x[1])
    assert peak_hour[0] == 11
    assert peak_hour[1] == 20


def test_footfall_date_range_filter(db_session, test_org, test_store, test_camera_entrance):
    """Test footfall filtering by date range."""
    # Events on Jan 10
    for i in range(10):
        create_test_event(
            db_session,
            event_id=f"jan10-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=datetime(2025, 1, 10, 10, i, 0),
            person_key=f"person-10-{i}"
        )

    # Events on Jan 11
    for i in range(15):
        create_test_event(
            db_session,
            event_id=f"jan11-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=datetime(2025, 1, 11, 10, i, 0),
            person_key=f"person-11-{i}"
        )

    # Query Jan 10 only
    jan10_start = datetime(2025, 1, 10, 0, 0, 0)
    jan10_end = datetime(2025, 1, 10, 23, 59, 59)

    jan10_count = (
        db_session.query(func.count(Event.id))
        .join(Camera, Event.camera_id == Camera.camera_id)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance",
            Camera.is_entrance == True,
            Event.ts >= jan10_start,
            Event.ts <= jan10_end
        )
        .scalar()
    )

    assert jan10_count == 10


def test_footfall_multi_entrance_cameras(db_session, test_org, test_store):
    """Test footfall counting across multiple entrance cameras."""
    from src.database.models_production import Camera

    # Create multiple entrance cameras
    cam1 = Camera(camera_id="entrance-1", store_id=test_store.store_id, name="Main Entrance", is_entrance=True)
    cam2 = Camera(camera_id="entrance-2", store_id=test_store.store_id, name="Side Entrance", is_entrance=True)
    db_session.add_all([cam1, cam2])
    db_session.commit()

    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Events from camera 1
    for i in range(7):
        create_test_event(
            db_session,
            event_id=f"cam1-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=cam1.camera_id,
            event_type="entrance",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-cam1-{i}"
        )

    # Events from camera 2
    for i in range(5):
        create_test_event(
            db_session,
            event_id=f"cam2-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=cam2.camera_id,
            event_type="entrance",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-cam2-{i}"
        )

    # Total footfall should be sum of both cameras
    total_footfall = (
        db_session.query(func.count(Event.id))
        .join(Camera, Event.camera_id == Camera.camera_id)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance",
            Camera.is_entrance == True
        )
        .scalar()
    )

    assert total_footfall == 12
