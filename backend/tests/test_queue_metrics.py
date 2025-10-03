"""
Test queue wait time aggregation including P90 metrics.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import func

from src.database.models_production import Event
from .conftest import create_test_event


def test_queue_wait_time_basic(db_session, test_org, test_store, test_camera_zone):
    """Test basic queue wait time calculation."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    wait_times = [10.0, 15.0, 20.0, 25.0, 30.0]  # seconds

    for i, wait_time in enumerate(wait_times):
        create_test_event(
            db_session,
            event_id=f"queue-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="queue_presence",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-{i}",
            payload={"queue_id": "checkout-1", "wait_seconds": wait_time}
        )

    # Query wait times
    result = (
        db_session.query(Event.payload["wait_seconds"].astext.cast(db_session.bind.dialect.NUMERIC))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "queue_presence",
            Event.payload["queue_id"].astext == "checkout-1"
        )
        .all()
    )

    wait_values = [float(row[0]) for row in result]

    # Calculate metrics
    avg_wait = np.mean(wait_values)
    p90_wait = np.percentile(wait_values, 90)

    assert avg_wait == 20.0  # Mean of [10, 15, 20, 25, 30]
    assert p90_wait == 29.0  # 90th percentile


def test_queue_p90_calculation(db_session, test_org, test_store, test_camera_zone):
    """Test P90 queue wait time calculation with realistic data."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Simulate queue wait times with varied distribution
    wait_times = [
        5.0, 8.0, 10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0, 28.0,  # Normal waits
        30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 70.0, 80.0, 90.0  # Longer waits
    ]

    for i, wait_time in enumerate(wait_times):
        create_test_event(
            db_session,
            event_id=f"queue-p90-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="queue_presence",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-{i}",
            payload={"queue_id": "checkout-main", "wait_seconds": wait_time}
        )

    # Query and calculate P90
    result = (
        db_session.query(Event.payload["wait_seconds"].astext.cast(db_session.bind.dialect.NUMERIC))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "queue_presence",
            Event.payload["queue_id"].astext == "checkout-main"
        )
        .all()
    )

    wait_values = [float(row[0]) for row in result]

    avg_wait = np.mean(wait_values)
    p90_wait = np.percentile(wait_values, 90)

    assert len(wait_values) == 20
    assert avg_wait == pytest.approx(33.75, rel=0.01)  # Mean
    assert p90_wait == pytest.approx(81.0, rel=0.1)  # 90th percentile


def test_queue_metrics_multiple_queues(db_session, test_org, test_store, test_camera_zone):
    """Test queue metrics calculation for multiple queues."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Queue 1: Fast checkout (shorter waits)
    for i in range(10):
        create_test_event(
            db_session,
            event_id=f"queue1-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="queue_presence",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-q1-{i}",
            payload={"queue_id": "express-checkout", "wait_seconds": float(5 + i)}
        )

    # Queue 2: Regular checkout (longer waits)
    for i in range(10):
        create_test_event(
            db_session,
            event_id=f"queue2-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="queue_presence",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-q2-{i}",
            payload={"queue_id": "regular-checkout", "wait_seconds": float(20 + i * 2)}
        )

    # Query metrics for express checkout
    express_result = (
        db_session.query(Event.payload["wait_seconds"].astext.cast(db_session.bind.dialect.NUMERIC))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "queue_presence",
            Event.payload["queue_id"].astext == "express-checkout"
        )
        .all()
    )

    express_waits = [float(row[0]) for row in express_result]
    express_avg = np.mean(express_waits)
    express_p90 = np.percentile(express_waits, 90)

    # Query metrics for regular checkout
    regular_result = (
        db_session.query(Event.payload["wait_seconds"].astext.cast(db_session.bind.dialect.NUMERIC))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "queue_presence",
            Event.payload["queue_id"].astext == "regular-checkout"
        )
        .all()
    )

    regular_waits = [float(row[0]) for row in regular_result]
    regular_avg = np.mean(regular_waits)
    regular_p90 = np.percentile(regular_waits, 90)

    # Express should be faster
    assert express_avg < regular_avg
    assert express_p90 < regular_p90


def test_queue_length_tracking(db_session, test_org, test_store, test_camera_zone):
    """Test tracking live queue length (people currently in queue)."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Person enters queue
    create_test_event(
        db_session,
        event_id="q-enter-1",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="queue_enter",
        timestamp=base_time,
        person_key="person-001",
        payload={"queue_id": "checkout-1"}
    )

    create_test_event(
        db_session,
        event_id="q-enter-2",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="queue_enter",
        timestamp=base_time + timedelta(seconds=30),
        person_key="person-002",
        payload={"queue_id": "checkout-1"}
    )

    create_test_event(
        db_session,
        event_id="q-enter-3",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="queue_enter",
        timestamp=base_time + timedelta(seconds=60),
        person_key="person-003",
        payload={"queue_id": "checkout-1"}
    )

    # Person 1 exits
    create_test_event(
        db_session,
        event_id="q-exit-1",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_zone.camera_id,
        event_type="queue_exit",
        timestamp=base_time + timedelta(minutes=2),
        person_key="person-001",
        payload={"queue_id": "checkout-1", "wait_seconds": 120.0}
    )

    # Query current queue length (people who entered but haven't exited)
    from sqlalchemy import and_, exists

    current_in_queue = (
        db_session.query(Event.person_key)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "queue_enter",
            Event.payload["queue_id"].astext == "checkout-1"
        )
        .filter(
            ~exists().where(
                and_(
                    Event.person_key == Event.person_key,
                    Event.type == "queue_exit",
                    Event.payload["queue_id"].astext == "checkout-1"
                )
            )
        )
        .distinct()
        .count()
    )

    # Should be 2 people still in queue (person-002 and person-003)
    assert current_in_queue == 2


def test_queue_wait_time_with_nulls(db_session, test_org, test_store, test_camera_zone):
    """Test queue metrics handle null wait times correctly."""
    base_time = datetime(2025, 1, 10, 10, 0, 0)

    # Some events with wait times
    for i in range(5):
        create_test_event(
            db_session,
            event_id=f"queue-valid-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="queue_presence",
            timestamp=base_time + timedelta(minutes=i),
            person_key=f"person-{i}",
            payload={"queue_id": "checkout-1", "wait_seconds": float(10 + i * 5)}
        )

    # Some events without wait_seconds (people still in queue)
    for i in range(3):
        create_test_event(
            db_session,
            event_id=f"queue-null-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="queue_presence",
            timestamp=base_time + timedelta(minutes=10 + i),
            person_key=f"person-null-{i}",
            payload={"queue_id": "checkout-1"}  # No wait_seconds
        )

    # Query only events with valid wait_seconds
    result = (
        db_session.query(Event.payload["wait_seconds"].astext)
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "queue_presence",
            Event.payload["queue_id"].astext == "checkout-1",
            Event.payload.has_key("wait_seconds")
        )
        .all()
    )

    wait_values = [float(row[0]) for row in result if row[0] is not None]

    # Should only include the 5 events with valid wait times
    assert len(wait_values) == 5
    assert np.mean(wait_values) == 20.0  # Mean of [10, 15, 20, 25, 30]
