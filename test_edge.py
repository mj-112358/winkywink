#!/usr/bin/env python3
"""
Test script for edge collector system.
Validates API connectivity, event generation, and backend integration.
"""

import sys
import yaml
import json
import time
from datetime import datetime, timezone

from edge_client_v2 import EdgeClient


def test_api_connectivity(config: dict):
    """Test basic API connectivity and authentication."""
    print("🔗 Testing API connectivity...")

    client = EdgeClient(
        api_base=config['api_base'],
        api_key=config['api_key'],
        org_id=config['org_id'],
        store_id=config['store_id'],
        camera_id=config['cameras'][0]['camera_id']
    )

    # Test heartbeat
    print("  📡 Sending heartbeat...")
    success = client.send_heartbeat({
        "test": True,
        "fps": 30,
        "active_tracks": 0
    })

    if success:
        print("  ✅ Heartbeat successful")
    else:
        print("  ❌ Heartbeat failed")
        return False

    return True


def test_event_ingestion(config: dict):
    """Test event ingestion with sample events."""
    print("\n📤 Testing event ingestion...")

    client = EdgeClient(
        api_base=config['api_base'],
        api_key=config['api_key'],
        org_id=config['org_id'],
        store_id=config['store_id'],
        camera_id=config['cameras'][0]['camera_id']
    )

    # Sample events covering all types
    sample_events = []

    # Entrance event
    sample_events.append({
        "type": "entrance",
        "ts": datetime.now(timezone.utc).isoformat(),
        "direction": "in",
        "person_key": "test_track_1"
    })

    # Zone event (if zones configured)
    if 'zones' in config['cameras'][0]:
        zone_id = list(config['cameras'][0]['zones'].keys())[0]
        now = datetime.now(timezone.utc)
        sample_events.append({
            "type": "zone",
            "ts": now.isoformat(),
            "zone_id": zone_id,
            "enter_ts": (now).isoformat(),
            "exit_ts": now.isoformat(),
            "dwell_seconds": 45.5,
            "person_key": "test_track_1"
        })

    # Shelf event (if shelves configured)
    if 'shelves' in config['cameras'][0]:
        shelf_id = list(config['cameras'][0]['shelves'].keys())[0]
        sample_events.append({
            "type": "shelf",
            "ts": datetime.now(timezone.utc).isoformat(),
            "shelf_id": shelf_id,
            "dwell_seconds": 12.3,
            "person_key": "test_track_1"
        })

    # Queue event (if queue configured)
    if 'queue' in config['cameras'][0]:
        now = datetime.now(timezone.utc)
        sample_events.append({
            "type": "queue",
            "ts": now.isoformat(),
            "queue_id": "checkout",
            "enter_ts": now.isoformat(),
            "exit_ts": now.isoformat(),
            "wait_seconds": 120.0,
            "person_key": "test_track_1"
        })

    print(f"  📊 Sending {len(sample_events)} test events...")
    success = client.send_events(sample_events)

    if success:
        print("  ✅ Events sent successfully")
        print(f"\n  Event types sent:")
        for event in sample_events:
            print(f"    - {event['type']}")
    else:
        print("  ❌ Event sending failed")
        return False

    return True


def test_buffer_resilience(config: dict):
    """Test offline buffering."""
    print("\n💾 Testing offline buffering...")

    client = EdgeClient(
        api_base="http://invalid.url.test",  # Intentionally wrong
        api_key=config['api_key'],
        org_id=config['org_id'],
        store_id=config['store_id'],
        camera_id="test_buffer_cam"
    )

    # This should fail and buffer
    sample_event = [{
        "type": "entrance",
        "ts": datetime.now(timezone.utc).isoformat(),
        "direction": "in",
        "person_key": "test_buffer_track"
    }]

    print("  🔌 Simulating offline mode...")
    client.send_events(sample_event)

    # Check buffer file exists
    import os
    buffer_file = client.buffer_file
    if os.path.exists(buffer_file):
        with open(buffer_file, 'r') as f:
            buffered = len(f.readlines())
        print(f"  ✅ Event buffered to disk ({buffered} events)")
        os.remove(buffer_file)
        return True
    else:
        print("  ❌ Buffer file not created")
        return False


def test_geometry_scaling():
    """Test polygon scaling."""
    print("\n📐 Testing polygon scaling...")

    from utils.geometry import scale_polygons, point_in_polygon

    # Test polygon
    polygons = {
        "zones": {
            "test_zone": [[100, 100], [200, 100], [200, 200], [100, 200]]
        }
    }

    screenshot_size = (1920, 1080)
    frame_size = (960, 540)

    scaled = scale_polygons(polygons, screenshot_size, frame_size)

    expected = [[50, 50], [100, 50], [100, 100], [50, 100]]
    actual = scaled["zones"]["test_zone"]

    if actual == expected:
        print("  ✅ Polygon scaling correct")
    else:
        print(f"  ❌ Polygon scaling incorrect: {actual} != {expected}")
        return False

    # Test point in polygon
    if point_in_polygon((75, 75), actual):
        print("  ✅ Point-in-polygon check correct")
    else:
        print("  ❌ Point-in-polygon check failed")
        return False

    return True


def validate_config(config_path: str):
    """Validate config file."""
    print("📋 Validating configuration...")

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        required = ['api_base', 'api_key', 'org_id', 'store_id', 'cameras']
        for field in required:
            if field not in config:
                print(f"  ❌ Missing required field: {field}")
                return None

        if not config['cameras']:
            print("  ❌ No cameras configured")
            return None

        print(f"  ✅ Config valid")
        print(f"     API: {config['api_base']}")
        print(f"     Store: {config['store_id']}")
        print(f"     Cameras: {len(config['cameras'])}")

        return config

    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return None


def main():
    """Run all tests."""
    if len(sys.argv) < 2:
        config_path = "config.yaml"
    else:
        config_path = sys.argv[1]

    print("="*70)
    print("🧪 WINK EDGE COLLECTOR TEST SUITE")
    print("="*70)

    # Validate config
    config = validate_config(config_path)
    if not config:
        sys.exit(1)

    # Test geometry
    if not test_geometry_scaling():
        print("\n❌ Geometry tests failed")
        sys.exit(1)

    # Test buffer
    if not test_buffer_resilience(config):
        print("\n❌ Buffer tests failed")
        sys.exit(1)

    # Test API
    if not test_api_connectivity(config):
        print("\n❌ API connectivity tests failed")
        sys.exit(1)

    # Test events
    if not test_event_ingestion(config):
        print("\n❌ Event ingestion tests failed")
        sys.exit(1)

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    print("\nReady for production deployment!")
    print("Run: docker-compose -f docker-compose.v2.yml up -d")


if __name__ == "__main__":
    main()
