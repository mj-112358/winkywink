#!/usr/bin/env python3
"""
Edge Runtime v2 - Production Implementation
- Multi-camera per process (threads)
- Capabilities-aware processing (entrance, zones, shelves, queue)
- Idempotent event_id hashing
- Heartbeats every 10s
- Batch POST to /v1/events/bulk every 2s
- Exponential backoff retries
- Disk buffering when offline (JSONL)
- Integrated YOLOv8 + Norfair tracking
"""

import os
import json
import time
import queue
import hashlib
import logging
import threading
import yaml
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict

import requests
from ultralytics import YOLO

LOG = logging.getLogger("edge")
logging.basicConfig(
    level=os.getenv("EDGE_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configuration from environment
API_BASE = os.getenv("EDGE_API_BASE", "https://api.winkai.in")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")
ORG_ID = os.getenv("ORG_ID", "")
STORE_ID = os.getenv("STORE_ID", "")

BULK_ENDPOINT = f"{API_BASE}/v1/events/bulk"
HEARTBEAT_ENDPOINT = f"{API_BASE}/v1/ingest/heartbeat"

BATCH_SECONDS = float(os.getenv("BATCH_SECONDS", "2.0"))
MAX_BATCH = int(os.getenv("MAX_BATCH", "500"))
BACKOFF_BASE = float(os.getenv("BACKOFF_BASE", "1.5"))
BACKOFF_MAX = float(os.getenv("BACKOFF_MAX", "60"))
BUFFER_DIR = Path(os.getenv("EDGE_BUFFER_DIR", "./buffer"))
BUFFER_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {EDGE_API_KEY}",
    "Content-Type": "application/json"
}


def make_event_id(camera_id: str, track_id: str, ts_iso: str, etype: str, logical_key: str = "") -> str:
    """Generate idempotent event_id using SHA256."""
    h = hashlib.sha256()
    h.update(camera_id.encode())
    h.update(b"|")
    h.update(str(track_id).encode())
    h.update(b"|")
    h.update(ts_iso.encode())
    h.update(b"|")
    h.update(etype.encode())
    if logical_key:
        h.update(b"|")
        h.update(logical_key.encode())
    return h.hexdigest()


def enqueue_jsonl(path: Path, batch: List[Dict[str, Any]]):
    """Append events to JSONL buffer file."""
    with path.open("a", encoding="utf-8") as f:
        for row in batch:
            f.write(json.dumps(row) + "\n")


def drain_jsonl(path: Path, max_rows=5000) -> List[Dict[str, Any]]:
    """Read and drain events from JSONL buffer file."""
    if not path.exists():
        return []
    rows = []
    tmp_path = path.with_suffix(".tmp")
    with path.open("r", encoding="utf-8") as f, tmp_path.open("w", encoding="utf-8") as out:
        for i, line in enumerate(f):
            if i < max_rows:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
            else:
                out.write(line)
    tmp_path.replace(path)
    return rows


def post_with_retry(url: str, payload: Any, headers: Dict[str, str], max_retries=8) -> bool:
    """POST with exponential backoff retry."""
    backoff = 0.5
    for attempt in range(max_retries):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code // 100 == 2:
                return True
            LOG.warning(f"POST {url} -> {r.status_code} {r.text[:200]}")
        except Exception as e:
            LOG.warning(f"POST {url} exception: {e}")
        time.sleep(backoff)
        backoff = min(backoff * BACKOFF_BASE, BACKOFF_MAX)
    return False


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]], tolerance: int = 5) -> bool:
    """Check if point is inside polygon with tolerance."""
    x, y = point
    polygon_np = np.array(polygon, dtype=np.int32)
    dist = cv2.pointPolygonTest(polygon_np, (x, y), True)
    return dist >= -tolerance


def line_crossing(prev: Tuple, curr: Tuple, p1: Tuple, p2: Tuple) -> bool:
    """Check if line segment from prev to curr crosses line from p1 to p2."""
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    return ccw(prev, p1, p2) != ccw(curr, p1, p2) and ccw(prev, curr, p1) != ccw(prev, curr, p2)


def crossing_direction(prev: Tuple, curr: Tuple, p1: Tuple, p2: Tuple) -> str:
    """Determine crossing direction using cross product."""
    line_vec = (p2[0] - p1[0], p2[1] - p1[1])
    move_vec = (curr[0] - prev[0], curr[1] - prev[1])
    cross = line_vec[0] * move_vec[1] - line_vec[1] * move_vec[0]
    return "in" if cross > 0 else "out"


class PersonTrack:
    """Track state for a single person."""
    def __init__(self, track_id: int, camera_id: str):
        self.track_id = track_id
        self.camera_id = camera_id
        self.person_id = f"{camera_id}_t{track_id}"
        self.last_seen = time.time()
        self.centroid = (0.0, 0.0)
        self.prev_centroid = (0.0, 0.0)

        self.current_zones: Set[str] = set()
        self.zone_enter_ts: Dict[str, float] = {}

        self.current_shelves: Set[str] = set()
        self.shelf_enter_ts: Dict[str, float] = {}

        self.in_queue = False
        self.queue_id: Optional[str] = None
        self.queue_enter_ts: Optional[float] = None

        self.entrance_crossed = False


class CameraWorker(threading.Thread):
    """Worker thread for processing one camera."""
    def __init__(self, camera_cfg: Dict[str, Any], out_queue: queue.Queue):
        super().__init__(daemon=True)
        self.cfg = camera_cfg
        self.out = out_queue
        self.camera_id = camera_cfg["camera_id"]
        self.capabilities = camera_cfg.get("capabilities", [])
        self.rtsp = camera_cfg.get("rtsp")
        self.geometry = camera_cfg.get("geometry", {})
        self.running = True

        # Initialize YOLO model
        LOG.info(f"[{self.camera_id}] Loading YOLOv8 model...")
        self.model = YOLO("yolov8n.pt")

        # Initialize video capture
        self.cap = cv2.VideoCapture(self.rtsp)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP: {self.rtsp}")

        # Track management
        self.tracks: Dict[int, PersonTrack] = {}

    def run(self):
        """Main detection and tracking loop."""
        LOG.info(f"[{self.camera_id}] Starting worker with capabilities={self.capabilities}")
        last_heartbeat = time.time()

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                LOG.warning(f"[{self.camera_id}] Frame read failed, reconnecting...")
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.rtsp)
                continue

            current_time = time.time()

            # Run YOLO tracking
            results = self.model.track(frame, persist=True, classes=[0], verbose=False)

            if results and results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes
                ids = boxes.id.cpu().numpy().astype(int)
                xyxy = boxes.xyxy.cpu().numpy()

                for i, track_id in enumerate(ids):
                    x1, y1, x2, y2 = xyxy[i]
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

                    if track_id not in self.tracks:
                        self.tracks[track_id] = PersonTrack(track_id, self.camera_id)

                    track = self.tracks[track_id]
                    track.prev_centroid = track.centroid
                    track.centroid = (cx, cy)
                    track.last_seen = current_time

                    # Process capabilities
                    self.process_capabilities(track, current_time)

            # Cleanup old tracks
            self.cleanup_old_tracks(current_time, max_age=10.0)

            time.sleep(0.05)  # ~20 FPS processing

    def process_capabilities(self, track: PersonTrack, current_time: float):
        """Process events based on camera capabilities."""
        ts_iso = datetime.fromtimestamp(current_time, timezone.utc).isoformat()

        if "entrance" in self.capabilities:
            self.process_entrance(track, current_time, ts_iso)
        if "zones" in self.capabilities:
            self.process_zones(track, current_time, ts_iso)
        if "shelves" in self.capabilities:
            self.process_shelves(track, current_time, ts_iso)
        if "queue" in self.capabilities:
            self.process_queue(track, current_time, ts_iso)

    def process_entrance(self, track: PersonTrack, current_time: float, ts_iso: str):
        """Process entrance line crossings."""
        entrance_line = self.geometry.get("entrance")
        if not entrance_line or len(entrance_line) < 2:
            return

        if not track.entrance_crossed:
            p1, p2 = entrance_line[0], entrance_line[1]
            if line_crossing(track.prev_centroid, track.centroid, p1, p2):
                direction = crossing_direction(track.prev_centroid, track.centroid, p1, p2)
                track.entrance_crossed = True

                event_id = make_event_id(self.camera_id, str(track.track_id), ts_iso, "entrance", direction)
                self.out.put({
                    "event_id": event_id,
                    "org_id": ORG_ID,
                    "store_id": STORE_ID,
                    "camera_id": self.camera_id,
                    "type": "entrance",
                    "ts": ts_iso,
                    "payload": {"direction": direction, "person_id": track.person_id}
                })
                LOG.debug(f"[{self.camera_id}] Entrance: {track.person_id} {direction}")

    def process_zones(self, track: PersonTrack, current_time: float, ts_iso: str):
        """Process zone entry/exit with dwell time."""
        zones = self.geometry.get("zones", {})
        if not zones:
            return

        current_zones = set()
        for zone_id, polygon in zones.items():
            if point_in_polygon(track.centroid, polygon, tolerance=5):
                current_zones.add(zone_id)

        # New zone entries
        new_zones = current_zones - track.current_zones
        for zone_id in new_zones:
            track.zone_enter_ts[zone_id] = current_time

        # Zone exits with dwell
        left_zones = track.current_zones - current_zones
        for zone_id in left_zones:
            if zone_id in track.zone_enter_ts:
                enter_ts = track.zone_enter_ts[zone_id]
                dwell_sec = current_time - enter_ts
                if dwell_sec >= 4.0:  # Minimum dwell threshold
                    event_id = make_event_id(self.camera_id, str(track.track_id), ts_iso, "zone_dwell", zone_id)
                    self.out.put({
                        "event_id": event_id,
                        "org_id": ORG_ID,
                        "store_id": STORE_ID,
                        "camera_id": self.camera_id,
                        "type": "zone_dwell",
                        "ts": ts_iso,
                        "payload": {
                            "logical_zone": zone_id,
                            "dwell_seconds": round(dwell_sec, 2),
                            "person_id": track.person_id
                        }
                    })
                del track.zone_enter_ts[zone_id]

        track.current_zones = current_zones

    def process_shelves(self, track: PersonTrack, current_time: float, ts_iso: str):
        """Process shelf interactions with dwell time."""
        shelves = self.geometry.get("shelves", {})
        if not shelves:
            return

        current_shelves = set()
        for shelf_id, polygon in shelves.items():
            if point_in_polygon(track.centroid, polygon, tolerance=5):
                current_shelves.add(shelf_id)

        # New shelf interactions
        new_shelves = current_shelves - track.current_shelves
        for shelf_id in new_shelves:
            track.shelf_enter_ts[shelf_id] = current_time

        # Shelf interaction end
        left_shelves = track.current_shelves - current_shelves
        for shelf_id in left_shelves:
            if shelf_id in track.shelf_enter_ts:
                enter_ts = track.shelf_enter_ts[shelf_id]
                dwell_sec = current_time - enter_ts
                if dwell_sec >= 4.0:  # Minimum interaction threshold
                    event_id = make_event_id(self.camera_id, str(track.track_id), ts_iso, "shelf_interaction", shelf_id)
                    self.out.put({
                        "event_id": event_id,
                        "org_id": ORG_ID,
                        "store_id": STORE_ID,
                        "camera_id": self.camera_id,
                        "type": "shelf_interaction",
                        "ts": ts_iso,
                        "payload": {
                            "logical_shelf": shelf_id,
                            "action": "touch",
                            "dwell_seconds": round(dwell_sec, 2),
                            "person_id": track.person_id
                        }
                    })
                del track.shelf_enter_ts[shelf_id]

        track.current_shelves = current_shelves

    def process_queue(self, track: PersonTrack, current_time: float, ts_iso: str):
        """Process queue presence with wait time."""
        queue_polygons = self.geometry.get("queue", {})
        if not queue_polygons:
            return

        # Find which queue the person is in (if any)
        in_any_queue = False
        current_queue_id = None

        for queue_id, polygon in queue_polygons.items():
            if point_in_polygon(track.centroid, polygon, tolerance=5):
                in_any_queue = True
                current_queue_id = queue_id
                break

        # Queue entry
        if in_any_queue and not track.in_queue:
            track.in_queue = True
            track.queue_id = current_queue_id
            track.queue_enter_ts = current_time

        # Queue exit
        elif not in_any_queue and track.in_queue:
            if track.queue_enter_ts and track.queue_id:
                wait_sec = current_time - track.queue_enter_ts
                event_id = make_event_id(self.camera_id, str(track.track_id), ts_iso, "queue_presence", track.queue_id)
                self.out.put({
                    "event_id": event_id,
                    "org_id": ORG_ID,
                    "store_id": STORE_ID,
                    "camera_id": self.camera_id,
                    "type": "queue_presence",
                    "ts": ts_iso,
                    "payload": {
                        "queue": track.queue_id,
                        "wait_seconds": round(wait_sec, 2),
                        "person_id": track.person_id
                    }
                })
            track.in_queue = False
            track.queue_id = None
            track.queue_enter_ts = None

    def cleanup_old_tracks(self, current_time: float, max_age: float):
        """Remove tracks that haven't been seen recently."""
        to_remove = [tid for tid, track in self.tracks.items() if current_time - track.last_seen > max_age]
        for tid in to_remove:
            del self.tracks[tid]


class EventFlusher(threading.Thread):
    """Thread for batching and flushing events to backend."""
    def __init__(self, out_queue: queue.Queue):
        super().__init__(daemon=True)
        self.q = out_queue
        self.running = True
        self.buffer_path = BUFFER_DIR / "event_buffer.jsonl"

    def run(self):
        buf: List[Dict[str, Any]] = []
        last_flush = time.monotonic()

        while self.running:
            try:
                item = self.q.get(timeout=0.25)
                buf.append(item)
            except queue.Empty:
                pass

            # Flush when batch size or time threshold reached
            if (time.monotonic() - last_flush > BATCH_SECONDS) or (len(buf) >= MAX_BATCH):
                if buf:
                    payload = {"events": buf[:MAX_BATCH]}
                    ok = post_with_retry(BULK_ENDPOINT, payload, HEADERS, max_retries=4)
                    if not ok:
                        LOG.warning(f"Failed to send batch, buffering {len(buf[:MAX_BATCH])} events to disk")
                        enqueue_jsonl(self.buffer_path, buf[:MAX_BATCH])
                    else:
                        LOG.info(f"Successfully sent batch of {len(buf[:MAX_BATCH])} events")
                    buf = buf[MAX_BATCH:]
                    last_flush = time.monotonic()

            # Try to drain disk buffer opportunistically
            pending = drain_jsonl(self.buffer_path, max_rows=2000)
            if pending:
                LOG.info(f"Attempting to flush {len(pending)} buffered events from disk")
                ok = post_with_retry(BULK_ENDPOINT, {"events": pending}, HEADERS, max_retries=4)
                if not ok:
                    LOG.warning(f"Failed to flush buffered events, re-queueing")
                    enqueue_jsonl(self.buffer_path, pending)
                else:
                    LOG.info(f"Successfully flushed {len(pending)} buffered events")


class Heartbeat(threading.Thread):
    """Thread for sending periodic heartbeats."""
    def __init__(self, camera_ids: List[str]):
        super().__init__(daemon=True)
        self.camera_ids = camera_ids
        self.running = True

    def run(self):
        while self.running:
            now = datetime.now(timezone.utc).isoformat()
            hb = {
                "org_id": ORG_ID,
                "store_id": STORE_ID,
                "camera_ids": self.camera_ids,
                "ts": now
            }
            ok = post_with_retry(HEARTBEAT_ENDPOINT, hb, HEADERS, max_retries=2)
            if ok:
                LOG.debug(f"Heartbeat sent for {len(self.camera_ids)} cameras")
            else:
                LOG.warning(f"Heartbeat failed")
            time.sleep(10)


def main(config: Dict[str, Any]):
    """Main entry point."""
    cam_confs = config["cameras"]
    out_q: queue.Queue = queue.Queue(maxsize=10000)

    # Start flusher and heartbeat threads
    flusher = EventFlusher(out_q)
    flusher.start()

    hb = Heartbeat([c["camera_id"] for c in cam_confs])
    hb.start()

    # Start camera workers
    workers = []
    for cam in cam_confs:
        try:
            w = CameraWorker(cam, out_q)
            workers.append(w)
            w.start()
            LOG.info(f"Started worker for camera {cam['camera_id']}")
        except Exception as e:
            LOG.error(f"Failed to start worker for camera {cam['camera_id']}: {e}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.info("Shutdown requested")
        for w in workers:
            w.running = False
        flusher.running = False
        hb.running = False


if __name__ == "__main__":
    import sys

    # Load configuration from YAML file
    config_path = sys.argv[1] if len(sys.argv) > 1 else "edge_config.yaml"

    if not Path(config_path).exists():
        LOG.error(f"Config file not found: {config_path}")
        print(f"\nExample {config_path}:\n")
        print("""
cameras:
  - camera_id: cam-entrance-1
    capabilities: [entrance]
    rtsp: rtsp://admin:password@192.168.1.100:554/stream1
    geometry:
      entrance: [[100, 500], [1800, 500]]

  - camera_id: cam-queue-1
    capabilities: [queue]
    rtsp: rtsp://admin:password@192.168.1.101:554/stream1
    geometry:
      queue:
        checkout: [[500, 300], [700, 300], [700, 500], [500, 500]]

  - camera_id: cam-zones-1
    capabilities: [zones, shelves]
    rtsp: rtsp://admin:password@192.168.1.102:554/stream1
    geometry:
      zones:
        zone_1: [[200, 200], [400, 200], [400, 400], [200, 400]]
        zone_2: [[600, 200], [800, 200], [800, 400], [600, 400]]
      shelves:
        shelf_1: [[100, 600], [300, 600], [300, 800], [100, 800]]
        """)
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    main(config)
