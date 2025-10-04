"""
Minimal seed data for production system.
Creates:
- org_1
- store_7821e931
- demo user (demo@example.com / demo123)
- edge key
- 2 cameras with zones in config JSONB
"""
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import os

from src.database.models_production import Base, Org, Store, User, EdgeKey, Camera

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database URL from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/wink")

def seed_minimal():
    """Seed minimal production data."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create org
        org = Org(
            org_id="org_1",
            name="Demo Organization"
        )
        session.add(org)

        # Create store
        store = Store(
            store_id="store_7821e931",
            org_id="org_1",
            name="Downtown Store",
            timezone="America/New_York"
        )
        session.add(store)

        # Create demo user
        user = User(
            user_id="user_demo",
            org_id="org_1",
            store_id="store_7821e931",
            email="demo@example.com",
            password_hash=pwd_context.hash("demo123")
        )
        session.add(user)

        # Create edge key
        edge_key = EdgeKey(
            key="edge_7821e931_secret_key",
            org_id="org_1",
            store_id="store_7821e931",
            active=True
        )
        session.add(edge_key)

        # Create Camera 1 with zones
        camera1 = Camera(
            camera_id="cam_entrance_001",
            store_id="store_7821e931",
            name="Entrance Camera",
            is_entrance=True,
            rtsp_url="rtsp://192.168.1.101:554/stream",
            capabilities=["footfall", "dwell"],
            config={
                "zones": [
                    {
                        "zone_id": "zone_entrance_in",
                        "name": "Entrance In",
                        "type": "line",
                        "coordinates": [[100, 200], [500, 200]],
                        "direction": "in"
                    },
                    {
                        "zone_id": "zone_entrance_out",
                        "name": "Entrance Out",
                        "type": "line",
                        "coordinates": [[100, 300], [500, 300]],
                        "direction": "out"
                    }
                ]
            },
            is_active=True
        )
        session.add(camera1)

        # Create Camera 2 with zones
        camera2 = Camera(
            camera_id="cam_aisle_001",
            store_id="store_7821e931",
            name="Aisle 1 Camera",
            is_entrance=False,
            rtsp_url="rtsp://192.168.1.102:554/stream",
            capabilities=["shelf_interaction", "dwell"],
            config={
                "zones": [
                    {
                        "zone_id": "zone_shelf_snacks",
                        "name": "Snacks Shelf",
                        "type": "polygon",
                        "coordinates": [[150, 100], [400, 100], [400, 300], [150, 300]],
                        "shelf_category": "snacks"
                    },
                    {
                        "zone_id": "zone_shelf_beverages",
                        "name": "Beverages Shelf",
                        "type": "polygon",
                        "coordinates": [[450, 100], [700, 100], [700, 300], [450, 300]],
                        "shelf_category": "beverages"
                    },
                    {
                        "zone_id": "zone_aisle1_dwell",
                        "name": "Aisle 1 Dwell Zone",
                        "type": "polygon",
                        "coordinates": [[100, 50], [750, 50], [750, 350], [100, 350]]
                    }
                ]
            },
            is_active=True
        )
        session.add(camera2)

        session.commit()
        print("✓ Minimal seed data created successfully")
        print(f"  - Org: org_1")
        print(f"  - Store: store_7821e931")
        print(f"  - User: demo@example.com / demo123")
        print(f"  - Edge Key: edge_7821e931_secret_key")
        print(f"  - Cameras: cam_entrance_001, cam_aisle_001")

    except Exception as e:
        session.rollback()
        print(f"✗ Error seeding data: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Seeding minimal production data...")
    seed_minimal()
