#!/usr/bin/env python3
"""
Test script for camera configuration API endpoints.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def login():
    """Login and get JWT token."""
    print("\n1. Testing login...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "demo@example.com", "password": "demo123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ Login successful. Token: {token[:20]}...")
        return token
    else:
        print(f"✗ Login failed: {response.status_code}")
        print(response.text)
        return None

def list_cameras(token):
    """List all cameras for the store."""
    print("\n2. Testing list cameras...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/cameras/", headers=headers)
    if response.status_code == 200:
        cameras = response.json()
        print(f"✓ Found {len(cameras)} cameras")
        for cam in cameras:
            print(f"  - {cam['name']} ({cam['camera_id']}): {len(cam.get('zones', []))} zones")
        return cameras
    else:
        print(f"✗ Failed to list cameras: {response.status_code}")
        print(response.text)
        return []

def create_camera(token):
    """Create a new camera with zones."""
    print("\n3. Testing create camera...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    camera_data = {
        "name": "Test Entrance Camera",
        "rtsp_url": "rtsp://192.168.1.100:554/stream",
        "is_entrance": True,
        "capabilities": ["footfall", "queue"],
        "zones": [
            {
                "zone_id": "zone_entrance_in",
                "name": "Entrance Line In",
                "type": "line",
                "coordinates": [[100, 200], [500, 200]],
                "direction": "in"
            },
            {
                "zone_id": "zone_entrance_out",
                "name": "Entrance Line Out",
                "type": "line",
                "coordinates": [[100, 250], [500, 250]],
                "direction": "out"
            }
        ]
    }

    response = requests.post(
        f"{BASE_URL}/api/cameras/",
        headers=headers,
        json=camera_data
    )

    if response.status_code == 201:
        camera = response.json()
        print(f"✓ Camera created: {camera['camera_id']}")
        print(f"  Name: {camera['name']}")
        print(f"  RTSP: {camera['rtsp_url']}")
        print(f"  Zones: {len(camera.get('zones', []))}")
        return camera
    else:
        print(f"✗ Failed to create camera: {response.status_code}")
        print(response.text)
        return None

def update_camera(token, camera_id):
    """Update camera configuration."""
    print(f"\n4. Testing update camera {camera_id}...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    update_data = {
        "name": "Updated Entrance Camera",
        "zones": [
            {
                "zone_id": "zone_shelf_snacks",
                "name": "Snacks Shelf",
                "type": "polygon",
                "coordinates": [[150, 100], [400, 100], [400, 300], [150, 300]],
                "shelf_category": "snacks"
            }
        ]
    }

    response = requests.put(
        f"{BASE_URL}/api/cameras/{camera_id}",
        headers=headers,
        json=update_data
    )

    if response.status_code == 200:
        camera = response.json()
        print(f"✓ Camera updated")
        print(f"  New name: {camera['name']}")
        print(f"  New zones: {len(camera.get('zones', []))}")
        return camera
    else:
        print(f"✗ Failed to update camera: {response.status_code}")
        print(response.text)
        return None

def get_camera(token, camera_id):
    """Get specific camera details."""
    print(f"\n5. Testing get camera {camera_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/cameras/{camera_id}", headers=headers)

    if response.status_code == 200:
        camera = response.json()
        print(f"✓ Camera retrieved")
        print(f"  Name: {camera['name']}")
        print(f"  Zones: {json.dumps(camera.get('zones', []), indent=2)}")
        return camera
    else:
        print(f"✗ Failed to get camera: {response.status_code}")
        print(response.text)
        return None

def delete_camera(token, camera_id):
    """Delete a camera."""
    print(f"\n6. Testing delete camera {camera_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{BASE_URL}/api/cameras/{camera_id}", headers=headers)

    if response.status_code == 204:
        print(f"✓ Camera deleted")
        return True
    else:
        print(f"✗ Failed to delete camera: {response.status_code}")
        print(response.text)
        return False

def main():
    print("=" * 60)
    print("Camera Configuration API Test")
    print("=" * 60)

    # Login
    token = login()
    if not token:
        return

    # List existing cameras
    cameras = list_cameras(token)

    # Create new camera
    new_camera = create_camera(token)
    if not new_camera:
        return

    camera_id = new_camera["camera_id"]

    # Update camera
    update_camera(token, camera_id)

    # Get camera details
    get_camera(token, camera_id)

    # Delete camera
    delete_camera(token, camera_id)

    # Verify deletion
    list_cameras(token)

    print("\n" + "=" * 60)
    print("✓ All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
