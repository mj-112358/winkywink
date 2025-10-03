#!/usr/bin/env python3
"""
Complete Production seed script - no placeholders.
Creates test org, store, cameras, edge keys, and sample events for end-to-end testing.
"""

import os
import sys
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.database import get_db_session
from src.database.models_production import (
    Organization, StoreExtended, CameraExtended, EdgeKey,
    EntranceEvent, ZoneEvent, ShelfInteraction
)


def seed_database():
    """Seed database with test data."""
    print("🌱 Seeding production database...")

    db = next(get_db_session())

    try:
        # 1. Create test organization
        print("\n1️⃣  Creating organization...")
        org = db.query(Organization).filter_by(slug="demo-retail").first()

        if not org:
            org = Organization(
                name="Demo Retail Co",
                slug="demo-retail",
                is_active=True
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"   ✓ Organization created: {org.id}")
        else:
            print(f"   ✓ Organization exists: {org.id}")

        # 2. Create test store
        print("\n2️⃣  Creating store...")
        store_id = "store_demo_001"
        store = db.query(StoreExtended).filter_by(store_id=store_id).first()

        if not store:
            store = StoreExtended(
                org_id=org.id,
                store_id=store_id,
                name="Demo Store - Downtown",
                timezone="America/New_York",
                is_active=True
            )
            db.add(store)
            db.commit()
            db.refresh(store)
            print(f"   ✓ Store created: {store_id}")
        else:
            print(f"   ✓ Store exists: {store_id}")

        # 3. Create cameras
        print("\n3️⃣  Creating cameras...")

        cameras_config = [
            {
                "camera_id": "cam_entrance_01",
                "name": "Main Entrance Camera",
                "capabilities": ["entrance", "zones"]
            },
            {
                "camera_id": "cam_zone_01",
                "name": "Product Zone Camera",
                "capabilities": ["zones", "shelves"]
            },
            {
                "camera_id": "cam_checkout_01",
                "name": "Checkout Queue Camera",
                "capabilities": ["queue", "zones"]
            }
        ]

        camera_keys = {}

        for cam_config in cameras_config:
            # Create or update camera
            camera = db.query(CameraExtended).filter_by(
                store_id=store_id,
                camera_id=cam_config["camera_id"]
            ).first()

            if not camera:
                camera = CameraExtended(
                    org_id=org.id,
                    store_id=store_id,
                    camera_id=cam_config["camera_id"],
                    name=cam_config["name"],
                    capabilities=cam_config["capabilities"],
                    is_active=True
                )
                db.add(camera)
                db.commit()
                db.refresh(camera)

            # Create edge API key
            existing_key = db.query(EdgeKey).filter_by(
                store_id=store_id,
                camera_id=cam_config["camera_id"],
                is_active=True
            ).first()

            if not existing_key:
                api_key = f"wink_edge_{secrets.token_urlsafe(32)}"
                edge_key = EdgeKey(
                    org_id=org.id,
                    store_id=store_id,
                    camera_id=cam_config["camera_id"],
                    api_key=api_key,
                    is_active=True
                )
                db.add(edge_key)
                db.commit()
                camera_keys[cam_config["camera_id"]] = api_key
            else:
                camera_keys[cam_config["camera_id"]] = existing_key.api_key

            print(f"   ✓ Camera: {cam_config['name']} ({cam_config['camera_id']})")
            print(f"      Capabilities: {', '.join(cam_config['capabilities'])}")
            print(f"      API Key: {camera_keys[cam_config['camera_id']]}")

        # 4. Create sample events for testing
        print("\n4️⃣  Creating sample events...")

        base_time = datetime.utcnow() - timedelta(hours=2)

        # Entrance events
        for i in range(20):
            event_time = base_time + timedelta(minutes=i * 5)
            entrance_event = EntranceEvent(
                org_id=org.id,
                store_id=store_id,
                camera_id="cam_entrance_01",
                person_key=f"person_{i}",
                direction="in" if i % 2 == 0 else "out",
                ts=event_time,
                device_ts=event_time
            )
            db.add(entrance_event)

        print(f"   ✓ Created 20 entrance events")

        # Zone events
        zones = ["electronics", "apparel", "grocery"]
        for i in range(30):
            event_time = base_time + timedelta(minutes=i * 3)
            zone_event = ZoneEvent(
                org_id=org.id,
                store_id=store_id,
                camera_id="cam_zone_01",
                zone_id=zones[i % len(zones)],
                person_key=f"person_{i % 10}",
                enter_ts=event_time,
                exit_ts=event_time + timedelta(seconds=45),
                dwell_seconds=45.0 + (i % 30),
                ts=event_time,
                device_ts=event_time
            )
            db.add(zone_event)

        print(f"   ✓ Created 30 zone events across {len(zones)} zones")

        # Shelf interactions
        shelves = ["shelf_01", "shelf_02", "shelf_03", "shelf_04"]
        for i in range(25):
            event_time = base_time + timedelta(minutes=i * 4)
            shelf_event = ShelfInteraction(
                org_id=org.id,
                store_id=store_id,
                camera_id="cam_zone_01",
                shelf_id=shelves[i % len(shelves)],
                person_key=f"person_{i % 10}",
                dwell_seconds=10.0 + (i % 20),
                ts=event_time,
                device_ts=event_time
            )
            db.add(shelf_event)

        print(f"   ✓ Created 25 shelf interactions across {len(shelves)} shelves")

        db.commit()

        print("\n" + "="*70)
        print("✅ Database seeded successfully!")
        print("="*70)

        # Print summary
        print("\n📋 SUMMARY:")
        print(f"   Org ID: {org.id}")
        print(f"   Store ID: {store_id}")
        print(f"   Cameras: {len(cameras_config)}")
        print(f"   Sample Events: 75 (20 entrance + 30 zone + 25 shelf)")

        print("\n🔑 EDGE API KEYS:")
        for cam_id, api_key in camera_keys.items():
            print(f"   {cam_id}: {api_key}")

        print("\n🧪 TEST COMMANDS:")
        print(f"\n   # Get store list:")
        print(f"   curl http://localhost:8000/api/dashboard/stores")

        print(f"\n   # Get live metrics:")
        print(f"   curl 'http://localhost:8000/api/dashboard/live?store_id={store_id}'")

        print(f"\n   # Get cameras:")
        print(f"   curl 'http://localhost:8000/api/dashboard/cameras?store_id={store_id}'")

        print(f"\n   # Spike detection:")
        print(f"   curl 'http://localhost:8000/api/analytics/spikes?store_id={store_id}&days=7'")

        print("\n" + "="*70 + "\n")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
