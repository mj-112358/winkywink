"""
Pytest configuration and fixtures for WINK Retail Analytics tests.
"""

import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models_production import Base, Org, Store, Camera, EdgeKey, Event, Aggregation


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_org(db_session):
    """Create a test organization."""
    org = Org(org_id="test-org-001", name="Test Organization")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_store(db_session, test_org):
    """Create a test store."""
    store = Store(
        store_id="test-store-001",
        org_id=test_org.org_id,
        name="Test Store",
        timezone="UTC"
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return store


@pytest.fixture
def test_camera_entrance(db_session, test_store):
    """Create a test entrance camera."""
    camera = Camera(
        camera_id="test-cam-entrance",
        store_id=test_store.store_id,
        name="Entrance Camera",
        is_entrance=True,
        capabilities=["person_detection", "entrance_counting"],
        config={"rtsp_url": "rtsp://test:554/entrance"}
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)
    return camera


@pytest.fixture
def test_camera_zone(db_session, test_store):
    """Create a test zone camera."""
    camera = Camera(
        camera_id="test-cam-zone-01",
        store_id=test_store.store_id,
        name="Zone Camera 1",
        is_entrance=False,
        capabilities=["person_detection", "zone_tracking"],
        config={
            "rtsp_url": "rtsp://test:554/zone1",
            "geometry": {
                "zones": {
                    "electronics": [[100, 100], [200, 100], [200, 200], [100, 200]],
                    "toys": [[300, 100], [400, 100], [400, 200], [300, 200]]
                }
            }
        }
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)
    return camera


@pytest.fixture
def test_edge_key(db_session, test_org, test_store, test_camera_entrance):
    """Create a test edge key."""
    edge_key = EdgeKey(
        token="test-edge-token-12345",
        org_id=test_org.org_id,
        store_id=test_store.store_id,
        camera_id=test_camera_entrance.camera_id,
        active=True
    )
    db_session.add(edge_key)
    db_session.commit()
    db_session.refresh(edge_key)
    return edge_key


def create_test_event(
    db_session,
    event_id: str,
    org_id: str,
    store_id: str,
    camera_id: str,
    event_type: str,
    timestamp: datetime,
    person_key: str = None,
    payload: dict = None
):
    """Helper to create a test event."""
    event = Event(
        event_id=event_id,
        org_id=org_id,
        store_id=store_id,
        camera_id=camera_id,
        person_key=person_key,
        type=event_type,
        ts=timestamp,
        payload=payload or {}
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event
