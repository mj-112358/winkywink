"""
Test promotion effectiveness analysis with baseline comparison.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import func

from src.database.models_production import Event
from .conftest import create_test_event


def test_promo_uplift_calculation(db_session, test_org, test_store, test_camera_zone):
    """Test promotion uplift calculation with baseline comparison."""
    # Baseline period: Jan 1-7 (no promotion)
    baseline_start = datetime(2025, 1, 1, 0, 0, 0)
    shelf_id = "shelf-snacks-01"

    # Baseline: 20 interactions over 7 days
    for i in range(20):
        create_test_event(
            db_session,
            event_id=f"baseline-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=baseline_start + timedelta(hours=i * 8),
            person_key=f"person-base-{i}",
            payload={"shelf_id": shelf_id, "dwell_seconds": 10.0}
        )

    # Promo period: Jan 8-14 (with promotion)
    promo_start = datetime(2025, 1, 8, 0, 0, 0)

    # Promo: 35 interactions over 7 days (75% uplift)
    for i in range(35):
        create_test_event(
            db_session,
            event_id=f"promo-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=promo_start + timedelta(hours=i * 5),
            person_key=f"person-promo-{i}",
            payload={"shelf_id": shelf_id, "dwell_seconds": 12.0}
        )

    # Query baseline metrics
    baseline_end = datetime(2025, 1, 7, 23, 59, 59)
    baseline_count = (
        db_session.query(func.count(Event.id))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= baseline_start,
            Event.ts <= baseline_end
        )
        .scalar()
    )

    # Query promo metrics
    promo_end = datetime(2025, 1, 14, 23, 59, 59)
    promo_count = (
        db_session.query(func.count(Event.id))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= promo_start,
            Event.ts <= promo_end
        )
        .scalar()
    )

    # Calculate uplift
    uplift_pct = ((promo_count - baseline_count) / baseline_count) * 100

    assert baseline_count == 20
    assert promo_count == 35
    assert uplift_pct == pytest.approx(75.0, rel=0.01)


def test_promo_dwell_time_increase(db_session, test_org, test_store, test_camera_zone):
    """Test promotion impact on dwell time."""
    shelf_id = "shelf-electronics-tv"

    # Baseline dwell times (shorter)
    baseline_start = datetime(2025, 1, 1, 10, 0, 0)
    baseline_dwells = [8.0, 10.0, 12.0, 9.0, 11.0]

    for i, dwell in enumerate(baseline_dwells):
        create_test_event(
            db_session,
            event_id=f"baseline-dwell-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=baseline_start + timedelta(hours=i),
            person_key=f"person-base-{i}",
            payload={"shelf_id": shelf_id, "dwell_seconds": dwell}
        )

    # Promo dwell times (longer - promotion attracts more attention)
    promo_start = datetime(2025, 1, 8, 10, 0, 0)
    promo_dwells = [15.0, 18.0, 20.0, 17.0, 22.0]

    for i, dwell in enumerate(promo_dwells):
        create_test_event(
            db_session,
            event_id=f"promo-dwell-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=promo_start + timedelta(hours=i),
            person_key=f"person-promo-{i}",
            payload={"shelf_id": shelf_id, "dwell_seconds": dwell}
        )

    # Query baseline avg dwell
    from sqlalchemy import cast, Float

    baseline_end = datetime(2025, 1, 7, 23, 59, 59)
    baseline_avg_dwell = (
        db_session.query(func.avg(cast(Event.payload["dwell_seconds"].astext, Float)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= baseline_start,
            Event.ts <= baseline_end
        )
        .scalar()
    )

    # Query promo avg dwell
    promo_end = datetime(2025, 1, 14, 23, 59, 59)
    promo_avg_dwell = (
        db_session.query(func.avg(cast(Event.payload["dwell_seconds"].astext, Float)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= promo_start,
            Event.ts <= promo_end
        )
        .scalar()
    )

    assert baseline_avg_dwell == pytest.approx(10.0, rel=0.01)  # Mean of [8, 10, 12, 9, 11]
    assert promo_avg_dwell == pytest.approx(18.4, rel=0.01)  # Mean of [15, 18, 20, 17, 22]
    assert promo_avg_dwell > baseline_avg_dwell


def test_promo_unique_visitors_comparison(db_session, test_org, test_store, test_camera_zone):
    """Test unique visitor count during promo vs baseline."""
    shelf_id = "shelf-clothing-01"

    # Baseline: 10 unique visitors
    baseline_start = datetime(2025, 1, 1, 10, 0, 0)
    for i in range(10):
        create_test_event(
            db_session,
            event_id=f"baseline-visitor-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=baseline_start + timedelta(hours=i),
            person_key=f"person-{i}",  # Unique visitors
            payload={"shelf_id": shelf_id, "dwell_seconds": 10.0}
        )

    # Promo: 18 unique visitors (80% increase)
    promo_start = datetime(2025, 1, 8, 10, 0, 0)
    for i in range(18):
        create_test_event(
            db_session,
            event_id=f"promo-visitor-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=promo_start + timedelta(hours=i),
            person_key=f"person-promo-{i}",  # Unique visitors
            payload={"shelf_id": shelf_id, "dwell_seconds": 12.0}
        )

    # Query baseline unique visitors
    baseline_end = datetime(2025, 1, 7, 23, 59, 59)
    baseline_unique = (
        db_session.query(func.count(func.distinct(Event.person_key)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= baseline_start,
            Event.ts <= baseline_end
        )
        .scalar()
    )

    # Query promo unique visitors
    promo_end = datetime(2025, 1, 14, 23, 59, 59)
    promo_unique = (
        db_session.query(func.count(func.distinct(Event.person_key)))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= promo_start,
            Event.ts <= promo_end
        )
        .scalar()
    )

    assert baseline_unique == 10
    assert promo_unique == 18

    uplift_pct = ((promo_unique - baseline_unique) / baseline_unique) * 100
    assert uplift_pct == pytest.approx(80.0, rel=0.01)


def test_promo_negative_impact(db_session, test_org, test_store, test_camera_zone):
    """Test detection of promotions that performed worse than baseline."""
    shelf_id = "shelf-test-negative"

    # Baseline: 30 interactions
    baseline_start = datetime(2025, 1, 1, 10, 0, 0)
    for i in range(30):
        create_test_event(
            db_session,
            event_id=f"baseline-neg-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=baseline_start + timedelta(hours=i),
            person_key=f"person-base-{i}",
            payload={"shelf_id": shelf_id, "dwell_seconds": 10.0}
        )

    # Promo: 20 interactions (worse performance)
    promo_start = datetime(2025, 1, 8, 10, 0, 0)
    for i in range(20):
        create_test_event(
            db_session,
            event_id=f"promo-neg-{i}",
            org_id=test_org.org_id,
            store_id=test_store.store_id,
            camera_id=test_camera_zone.camera_id,
            event_type="shelf_interaction",
            timestamp=promo_start + timedelta(hours=i),
            person_key=f"person-promo-{i}",
            payload={"shelf_id": shelf_id, "dwell_seconds": 8.0}
        )

    # Query baseline
    baseline_end = datetime(2025, 1, 7, 23, 59, 59)
    baseline_count = (
        db_session.query(func.count(Event.id))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= baseline_start,
            Event.ts <= baseline_end
        )
        .scalar()
    )

    # Query promo
    promo_end = datetime(2025, 1, 14, 23, 59, 59)
    promo_count = (
        db_session.query(func.count(Event.id))
        .filter(
            Event.store_id == test_store.store_id,
            Event.type == "shelf_interaction",
            Event.payload["shelf_id"].astext == shelf_id,
            Event.ts >= promo_start,
            Event.ts <= promo_end
        )
        .scalar()
    )

    # Calculate uplift (should be negative)
    uplift_pct = ((promo_count - baseline_count) / baseline_count) * 100

    assert baseline_count == 30
    assert promo_count == 20
    assert uplift_pct == pytest.approx(-33.33, rel=0.01)  # Negative uplift
