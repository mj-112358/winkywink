"""
Test statistical spike detection for festival/anomaly identification.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import func, extract

from src.database.models_production import Event
from .conftest import create_test_event


def test_spike_detection_basic(db_session, test_org, test_store, test_camera_entrance):
    """Test basic spike detection using z-score method."""
    base_date = datetime(2025, 1, 1, 0, 0, 0)

    # Normal days: ~100 visitors per day
    normal_days = 14
    for day in range(normal_days):
        daily_count = np.random.randint(95, 105)  # Normal variance
        for i in range(daily_count):
            create_test_event(
                db_session,
                event_id=f"normal-d{day}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(days=day, minutes=i * 10),
                person_key=f"person-d{day}-{i}"
            )

    # Spike day: 200 visitors (double the normal)
    spike_day = 15
    for i in range(200):
        create_test_event(
            db_session,
            event_id=f"spike-d{spike_day}-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=base_date + timedelta(days=spike_day, minutes=i * 5),
            person_key=f"person-spike-{i}"
        )

    # Query daily counts
    from sqlalchemy import func, cast, String

    daily_counts = (
        db_session.query(
            func.date(Event.ts).label('date'),
            func.count(Event.id).label('count')
        )
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance"
        )
        .group_by(func.date(Event.ts))
        .order_by(func.date(Event.ts))
        .all()
    )

    # Calculate z-scores
    counts = [row.count for row in daily_counts]
    mean_count = np.mean(counts)
    std_count = np.std(counts)

    z_scores = [(count - mean_count) / std_count for count in counts]

    # Spike detection threshold: z-score > 2.0
    spike_threshold = 2.0
    spike_detected = any(z > spike_threshold for z in z_scores)

    assert spike_detected
    assert max(z_scores) > spike_threshold
    # The spike day should have z-score > 2
    spike_day_z_score = z_scores[-1]  # Last day
    assert spike_day_z_score > spike_threshold


def test_spike_detection_hourly(db_session, test_org, test_store, test_camera_entrance):
    """Test spike detection at hourly granularity."""
    base_date = datetime(2025, 1, 10, 0, 0, 0)

    # Normal hours: ~10 visitors per hour
    normal_hours = 20
    for hour in range(normal_hours):
        hourly_count = np.random.randint(8, 12)
        for i in range(hourly_count):
            create_test_event(
                db_session,
                event_id=f"hour-{hour}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(hours=hour, minutes=i * 5),
                person_key=f"person-h{hour}-{i}"
            )

    # Spike hour: 30 visitors (3x normal)
    spike_hour = 21
    for i in range(30):
        create_test_event(
            db_session,
            event_id=f"spike-hour-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=base_date + timedelta(hours=spike_hour, minutes=i * 2),
            person_key=f"person-spike-{i}"
        )

    # Query hourly counts
    hourly_counts = (
        db_session.query(
            extract('hour', Event.ts).label('hour'),
            func.count(Event.id).label('count')
        )
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance",
            Event.ts >= base_date,
            Event.ts < base_date + timedelta(days=1)
        )
        .group_by('hour')
        .order_by('hour')
        .all()
    )

    # Calculate z-scores
    counts = [row.count for row in hourly_counts]
    mean_count = np.mean(counts)
    std_count = np.std(counts)

    z_scores = {int(row.hour): (row.count - mean_count) / std_count for row in hourly_counts}

    # Check spike hour has high z-score
    spike_threshold = 2.0
    assert z_scores[spike_hour] > spike_threshold


def test_spike_detection_weekend_vs_weekday(db_session, test_org, test_store, test_camera_entrance):
    """Test that weekend spikes are detected relative to weekday baselines."""
    # Monday-Friday baseline: ~80 visitors per day
    base_date = datetime(2025, 1, 6, 0, 0, 0)  # Monday

    for day in range(5):  # Mon-Fri
        for i in range(80):
            create_test_event(
                db_session,
                event_id=f"weekday-d{day}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(days=day, minutes=i * 10),
                person_key=f"person-weekday-d{day}-{i}"
            )

    # Saturday spike: 150 visitors
    saturday = 5
    for i in range(150):
        create_test_event(
            db_session,
            event_id=f"saturday-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_entrance.camera_id,
            event_type="entrance",
            timestamp=base_date + timedelta(days=saturday, minutes=i * 7),
            person_key=f"person-saturday-{i}"
        )

    # Query daily counts
    daily_counts = (
        db_session.query(
            func.date(Event.ts).label('date'),
            func.count(Event.id).label('count')
        )
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance"
        )
        .group_by(func.date(Event.ts))
        .order_by(func.date(Event.ts))
        .all()
    )

    counts = [row.count for row in daily_counts]
    mean_count = np.mean(counts)
    std_count = np.std(counts)

    # Saturday should be a spike
    saturday_count = counts[-1]
    saturday_z_score = (saturday_count - mean_count) / std_count

    assert saturday_count == 150
    assert saturday_z_score > 2.0  # Significant spike


def test_spike_detection_no_false_positives(db_session, test_org, test_store, test_camera_entrance):
    """Test that normal variance doesn't trigger false spike detection."""
    base_date = datetime(2025, 1, 1, 0, 0, 0)

    # Normal days with typical variance: 95-105 visitors
    for day in range(14):
        daily_count = 95 + (day % 10)  # Gradual variance within normal range
        for i in range(daily_count):
            create_test_event(
                db_session,
                event_id=f"normal-d{day}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(days=day, minutes=i * 10),
                person_key=f"person-d{day}-{i}"
            )

    # Query daily counts
    daily_counts = (
        db_session.query(
            func.date(Event.ts).label('date'),
            func.count(Event.id).label('count')
        )
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance"
        )
        .group_by(func.date(Event.ts))
        .order_by(func.date(Event.ts))
        .all()
    )

    # Calculate z-scores
    counts = [row.count for row in daily_counts]
    mean_count = np.mean(counts)
    std_count = np.std(counts)

    z_scores = [(count - mean_count) / std_count for count in counts]

    # No z-score should exceed spike threshold
    spike_threshold = 2.0
    assert all(abs(z) < spike_threshold for z in z_scores)


def test_spike_detection_multi_day_event(db_session, test_org, test_store, test_camera_entrance):
    """Test detection of multi-day spikes (e.g., holiday weekend)."""
    base_date = datetime(2025, 1, 1, 0, 0, 0)

    # Normal days: ~100 visitors
    for day in range(10):
        for i in range(100):
            create_test_event(
                db_session,
                event_id=f"normal-d{day}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(days=day, minutes=i * 10),
                person_key=f"person-d{day}-{i}"
            )

    # Multi-day spike: Days 11, 12, 13 (holiday weekend)
    spike_days = [11, 12, 13]
    spike_counts = [180, 200, 190]

    for day, count in zip(spike_days, spike_counts):
        for i in range(count):
            create_test_event(
                db_session,
                event_id=f"spike-d{day}-{i}",
                org_id=test_org.org_id,
                store_id=test_store.store_id,
                camera_id=test_camera_entrance.camera_id,
                event_type="entrance",
                timestamp=base_date + timedelta(days=day, minutes=i * 5),
                person_key=f"person-spike-d{day}-{i}"
            )

    # Query daily counts
    daily_counts = (
        db_session.query(
            func.date(Event.ts).label('date'),
            func.count(Event.id).label('count')
        )
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "entrance"
        )
        .group_by(func.date(Event.ts))
        .order_by(func.date(Event.ts))
        .all()
    )

    counts = [row.count for row in daily_counts]
    mean_count = np.mean(counts)
    std_count = np.std(counts)

    z_scores = [(count - mean_count) / std_count for count in counts]

    # All three spike days should be detected
    spike_threshold = 2.0
    spike_day_z_scores = z_scores[-3:]  # Last 3 days

    assert all(z > spike_threshold for z in spike_day_z_scores)
    assert len([z for z in z_scores if z > spike_threshold]) == 3
