"""
Edge runtime for YOLO-based person detection and zone analytics.
Runs on store laptop, sends events to cloud API.
"""
import cv2
import yaml
import requests
import time
from datetime import datetime
from ultralytics import YOLO
import numpy as np
from collections import defaultdict
import uuid


class EdgeRuntime:
    def __init__(self, config_path="config.yaml"):
        """Initialize edge runtime."""
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.api_url = self.config['api_url']
        self.edge_key = self.config['edge_key']
        self.cameras = self.config['cameras']

        # Load YOLO model
        print("Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')  # Lightweight model
        print("YOLO model loaded")

        # Person tracking
        self.person_tracks = defaultdict(lambda: {
            'last_seen': None,
            'zone_entries': set(),
            'dwell_start': None
        })

        # Heartbeat interval
        self.last_heartbeat = 0
        self.heartbeat_interval = 60  # seconds

    def point_in_polygon(self, point, polygon):
        """Check if point is inside polygon."""
        x, y = point
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def crosses_line(self, prev_point, curr_point, line):
        """Check if movement crossed a line."""
        # Simple line crossing detection
        (x1, y1), (x2, y2) = line
        (px, py) = prev_point
        (cx, cy) = curr_point

        # Check if points are on opposite sides of the line
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign(prev_point, (x1, y1), (x2, y2))
        d2 = sign(curr_point, (x1, y1), (x2, y2))

        return (d1 * d2) < 0

    def send_events(self, events):
        """Send events to cloud API."""
        if not events:
            return

        try:
            response = requests.post(
                f"{self.api_url}/api/ingest/events",
                headers={"X-EDGE-KEY": self.edge_key},
                json={"events": events},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Sent {result['inserted']} events ({result['duplicates']} duplicates)")
            else:
                print(f"✗ Failed to send events: {response.status_code}")

        except Exception as e:
            print(f"✗ Error sending events: {e}")

    def send_heartbeat(self):
        """Send heartbeat to cloud API."""
        try:
            response = requests.post(
                f"{self.api_url}/api/ingest/heartbeat",
                headers={"X-EDGE-KEY": self.edge_key},
                timeout=10
            )

            if response.status_code == 200:
                print("♥ Heartbeat sent")
            else:
                print(f"✗ Heartbeat failed: {response.status_code}")

        except Exception as e:
            print(f"✗ Error sending heartbeat: {e}")

    def process_camera(self, camera_config):
        """Process a single camera stream."""
        camera_id = camera_config['camera_id']
        rtsp_url = camera_config['rtsp_url']
        zones = camera_config.get('zones', [])

        print(f"\n📹 Processing camera: {camera_config['name']} ({camera_id})")
        print(f"   RTSP: {rtsp_url}")

        # Open RTSP stream
        cap = cv2.VideoCapture(rtsp_url)

        if not cap.isOpened():
            print(f"✗ Failed to open RTSP stream: {rtsp_url}")
            return

        frame_count = 0
        events_batch = []

        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"✗ Failed to read frame from {camera_id}")
                break

            frame_count += 1

            # Process every 5th frame to reduce load
            if frame_count % 5 != 0:
                continue

            # Run YOLO detection
            results = self.model(frame, verbose=False)

            # Filter for persons (class 0 in COCO)
            persons = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    if int(box.cls[0]) == 0:  # Person class
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                        persons.append({
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'center': center,
                            'confidence': float(box.conf[0])
                        })

            # Process zones
            now = datetime.utcnow()
            for person in persons:
                person_key = f"person_{person['center'][0]}_{person['center'][1]}"

                for zone in zones:
                    zone_id = zone['zone_id']
                    zone_type = zone['type']

                    if zone_type == 'line':
                        # Footfall line crossing
                        prev_center = self.person_tracks[person_key].get('center')
                        if prev_center:
                            line_coords = [(zone['coordinates'][0][0], zone['coordinates'][0][1]),
                                         (zone['coordinates'][1][0], zone['coordinates'][1][1])]

                            if self.crosses_line(prev_center, person['center'], line_coords):
                                direction = zone.get('direction', 'unknown')
                                event_type = f"footfall_{direction}"

                                event = {
                                    "event_id": f"{camera_id}_{zone_id}_{person_key}_{int(now.timestamp())}",
                                    "camera_id": camera_id,
                                    "person_key": person_key,
                                    "type": event_type,
                                    "ts": now.isoformat(),
                                    "payload": {
                                        "zone_id": zone_id,
                                        "direction": direction
                                    }
                                }
                                events_batch.append(event)
                                print(f"  → {event_type} in {zone['name']}")

                    elif zone_type == 'polygon':
                        # Polygon zone (shelf interaction, dwell)
                        polygon = [(c[0], c[1]) for c in zone['coordinates']]

                        if self.point_in_polygon(person['center'], polygon):
                            # Check if first entry
                            if zone_id not in self.person_tracks[person_key]['zone_entries']:
                                self.person_tracks[person_key]['zone_entries'].add(zone_id)

                                # Shelf interaction event
                                if zone.get('shelf_category'):
                                    event = {
                                        "event_id": f"{camera_id}_{zone_id}_{person_key}_{int(now.timestamp())}",
                                        "camera_id": camera_id,
                                        "person_key": person_key,
                                        "type": "shelf_interaction",
                                        "ts": now.isoformat(),
                                        "payload": {
                                            "zone_id": zone_id,
                                            "shelf_category": zone['shelf_category']
                                        }
                                    }
                                    events_batch.append(event)
                                    print(f"  → shelf_interaction in {zone['name']}")

                                # Start dwell timer
                                self.person_tracks[person_key]['dwell_start'] = now

                # Update tracking
                self.person_tracks[person_key]['center'] = person['center']
                self.person_tracks[person_key]['last_seen'] = now

            # Send events batch every 10 seconds
            if len(events_batch) >= 10 or (frame_count % 50 == 0 and events_batch):
                self.send_events(events_batch)
                events_batch = []

            # Send heartbeat every minute
            if time.time() - self.last_heartbeat > self.heartbeat_interval:
                self.send_heartbeat()
                self.last_heartbeat = time.time()

            # Clean up old tracks
            cutoff = now.timestamp() - 10  # Remove tracks older than 10 seconds
            for key in list(self.person_tracks.keys()):
                if self.person_tracks[key]['last_seen'].timestamp() < cutoff:
                    del self.person_tracks[key]

        cap.release()

    def run(self):
        """Run edge runtime for all cameras."""
        print("=" * 60)
        print("  WINK EDGE RUNTIME")
        print("=" * 60)
        print(f"API URL: {self.api_url}")
        print(f"Cameras: {len(self.cameras)}")
        print("=" * 60)

        # Send initial heartbeat
        self.send_heartbeat()
        self.last_heartbeat = time.time()

        # Process each camera (in production, use threading for multiple cameras)
        for camera in self.cameras:
            try:
                self.process_camera(camera)
            except KeyboardInterrupt:
                print("\n\nShutting down...")
                break
            except Exception as e:
                print(f"✗ Error processing camera {camera['camera_id']}: {e}")
                time.sleep(5)  # Wait before retry


if __name__ == "__main__":
    runtime = EdgeRuntime()
    runtime.run()
