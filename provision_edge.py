#!/usr/bin/env python3
"""
Edge provisioning script.
Creates config.yaml with store/camera IDs and API keys from backend.
"""

import sys
import yaml
import requests
from typing import Dict, List


def provision_store(
    admin_url: str,
    admin_token: str,
    org_id: str,
    store_id: str,
    cameras: List[Dict]
) -> str:
    """
    Provision edge keys for a store and generate config.yaml.

    Args:
        admin_url: Backend admin API URL
        admin_token: Admin authentication token
        org_id: Organization UUID
        store_id: Store identifier
        cameras: List of camera configs with camera_id, rtsp, capabilities, polygons

    Returns:
        Path to generated config.yaml
    """

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }

    print("🔑 Provisioning edge keys from backend...")
    print(f"   Admin API: {admin_url}")
    print(f"   Store: {store_id}")
    print(f"   Cameras: {len(cameras)}")

    # Create edge keys for each camera
    camera_configs = []

    for cam in cameras:
        print(f"\n📷 Creating edge key for {cam['camera_id']}...")

        # Create edge key via backend admin API
        response = requests.post(
            f"{admin_url}/api/admin/edge-keys",
            headers=headers,
            json={
                "org_id": org_id,
                "store_id": store_id,
                "camera_id": cam["camera_id"]
            }
        )

        if response.status_code != 200:
            print(f"❌ Failed to create edge key: {response.text}")
            continue

        result = response.json()
        api_key = result["api_key"]

        print(f"✅ Created edge key: {api_key[:20]}...")

        # Build camera config
        camera_config = {
            "camera_id": cam["camera_id"],
            "rtsp": cam["rtsp"],
            "capabilities": cam.get("capabilities", []),
            "screenshot_size": cam.get("screenshot_size", [1920, 1080])
        }

        # Add polygons based on capabilities
        if "entrance" in cam.get("capabilities", []):
            camera_config["entrance_line"] = cam.get("entrance_line", [])

        if "zones" in cam.get("capabilities", []):
            camera_config["zones"] = cam.get("zones", {})

        if "shelves" in cam.get("capabilities", []):
            camera_config["shelves"] = cam.get("shelves", {})

        if "queue" in cam.get("capabilities", []):
            camera_config["queue"] = cam.get("queue", [])

        camera_configs.append(camera_config)

    # Generate config.yaml
    # Note: All cameras share the same API key (resolved to org/store/camera by backend)
    # Or each camera gets its own key - depends on backend design
    # Here we use the first camera's key as default
    if not camera_configs:
        print("❌ No cameras configured")
        return None

    # For multi-camera, backend resolves camera_id from the API key
    # So we need to get the first key or a store-level key
    # Assuming backend provides store-level key:
    print(f"\n📝 Getting store-level API key...")

    # If backend doesn't have store-level keys, use first camera's key
    # and ensure backend auth resolves camera_id from request payload
    first_key = api_key  # Use last created key

    config = {
        "api_base": admin_url.replace("/api/admin", ""),
        "api_key": first_key,
        "org_id": org_id,
        "store_id": store_id,
        "cameras": camera_configs
    }

    # Write config.yaml
    config_path = "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Generated {config_path}")
    print("\n📋 Configuration Summary:")
    print(f"   API Base: {config['api_base']}")
    print(f"   Store ID: {store_id}")
    print(f"   Cameras: {len(camera_configs)}")
    for cam in camera_configs:
        print(f"      - {cam['camera_id']}: {', '.join(cam['capabilities'])}")

    return config_path


def main():
    """Example usage."""
    if len(sys.argv) < 4:
        print("""
Usage: python provision_edge.py <admin_url> <admin_token> <org_id> <store_id>

Example:
    python provision_edge.py \\
        https://api.winkai.in \\
        admin_token_here \\
        org_uuid_here \\
        store_demo_001

This will:
1. Create edge API keys for each camera via /api/admin/edge-keys
2. Generate config.yaml with all cameras configured
3. You can then run: docker-compose -f docker-compose.v2.yml up -d
        """)
        sys.exit(1)

    admin_url = sys.argv[1]
    admin_token = sys.argv[2]
    org_id = sys.argv[3]
    store_id = sys.argv[4]

    # Example camera configuration
    cameras = [
        {
            "camera_id": "cam_entrance_01",
            "rtsp": "rtsp://user:pass@192.168.1.10:554/stream1",
            "capabilities": ["entrance"],
            "screenshot_size": [2872, 1570],
            "entrance_line": [[1769, 737], [2173, 945]]
        },
        {
            "camera_id": "cam_zone_01",
            "rtsp": "rtsp://user:pass@192.168.1.11:554/stream1",
            "capabilities": ["zones", "shelves"],
            "screenshot_size": [2872, 1570],
            "zones": {
                "electronics": [[476, 1312], [891, 1106], [1089, 1436], [631, 1492]],
                "apparel": [[1644, 742], [2168, 1027], [1931, 1302], [1565, 1027]]
            },
            "shelves": {
                "shelf_01": [[382, 418], [611, 322], [820, 1014], [509, 1177]]
            }
        }
    ]

    config_path = provision_store(admin_url, admin_token, org_id, store_id, cameras)

    if config_path:
        print(f"\n🚀 Ready to deploy!")
        print(f"   Run: docker-compose -f docker-compose.v2.yml up -d")


if __name__ == "__main__":
    main()
