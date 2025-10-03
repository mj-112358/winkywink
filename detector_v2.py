import cv2
import time
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
from ultralytics import YOLO

logger = logging.getLogger(__name__)


def point_near_polygon(point: Tuple[float, float], polygon: List[List[float]], tolerance: int = 5) -> bool:
    x, y = point
    polygon_np = np.array(polygon, dtype=np.int32)
    dist = cv2.pointPolygonTest(polygon_np, (x, y), True)
    return dist >= -tolerance


def line_crossing(prev: Tuple, curr: Tuple, p1: Tuple, p2: Tuple) -> bool:
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return ccw(prev, p1, p2) != ccw(curr, p1, p2) and ccw(prev, curr, p1) != ccw(prev, curr, p2)


def crossing_direction(prev: Tuple, curr: Tuple, p1: Tuple, p2: Tuple) -> str:
    line_vec = (p2[0] - p1[0], p2[1] - p1[1])
    move_vec = (curr[0] - prev[0], curr[1] - prev[1])
    cross = line_vec[0] * move_vec[1] - line_vec[1] * move_vec[0]
    return "in" if cross > 0 else "out"


class PersonSession:
    def __init__(self, track_id: int, camera_id: str):
        self.track_id = track_id
        self.person_key = f"{camera_id}_t{track_id}"
        self.last_seen = time.time()
        self.centroid = (0.0, 0.0)
        self.prev_centroid = (0.0, 0.0)

        self.current_zones = set()
        self.zone_enter_ts = {}

        self.current_shelves = set()
        self.shelf_enter_ts = {}

        self.in_queue = False
        self.queue_enter_ts = None

        self.entrance_crossed = False


class Detector:
    def __init__(self, rtsp_url: str, config: Dict, edge_client):
        self.rtsp_url = rtsp_url
        self.camera_id = config["id"]
        self.capabilities = config.get("capabilities", [])
        self.geometry = config.get("geometry", {})
        self.client = edge_client

        logger.info(f"Loading YOLOv8 for {self.camera_id}")
        self.model = YOLO("yolov8n.pt")

        self.cap = cv2.VideoCapture(rtsp_url)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP: {rtsp_url}")

        self.sessions: Dict[int, PersonSession] = {}
        self.next_track_id = 1
        self.event_batch = []

        logger.info(f"Detector ready: {self.camera_id} with {self.capabilities}")

    def run(self):
        logger.info(f"Starting detector for {self.camera_id}")
        last_heartbeat = time.time()

        while True:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Frame read failed, reconnecting...")
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.rtsp_url)
                continue

            current_time = time.time()

            results = self.model.track(frame, persist=True, classes=[0], verbose=False)
            if results and results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes
                ids = boxes.id.cpu().numpy().astype(int)
                xyxy = boxes.xyxy.cpu().numpy()

                for i, track_id in enumerate(ids):
                    x1, y1, x2, y2 = xyxy[i]
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

                    if track_id not in self.sessions:
                        self.sessions[track_id] = PersonSession(track_id, self.camera_id)

                    sess = self.sessions[track_id]
                    sess.prev_centroid = sess.centroid
                    sess.centroid = (cx, cy)
                    sess.last_seen = current_time

                    self.process_capabilities(sess, current_time)

            self.cleanup_old_sessions(current_time, max_age=10.0)

            if len(self.event_batch) >= 10 or (current_time - last_heartbeat) > 5:
                self.flush_events()

            if (current_time - last_heartbeat) > 30:
                self.client.heartbeat()
                last_heartbeat = current_time

            time.sleep(0.05)

    def process_capabilities(self, sess: PersonSession, current_time: float):
        if "entrance" in self.capabilities:
            self.process_entrance(sess, current_time)
        if "zones" in self.capabilities:
            self.process_zones(sess, current_time)
        if "shelves" in self.capabilities:
            self.process_shelves(sess, current_time)
        if "queue" in self.capabilities:
            self.process_queue(sess, current_time)

    def process_entrance(self, sess: PersonSession, current_time: float):
        entrance_line = self.geometry.get("entrance")
        if not entrance_line or len(entrance_line) < 2:
            return

        if not sess.entrance_crossed:
            p1, p2 = entrance_line[0], entrance_line[1]
            if line_crossing(sess.prev_centroid, sess.centroid, p1, p2):
                direction = crossing_direction(sess.prev_centroid, sess.centroid, p1, p2)
                sess.entrance_crossed = True

                event = {
                    "type": "entrance",
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "person_key": sess.person_key,
                    "payload": {"direction": direction}
                }
                self.event_batch.append(event)
                logger.debug(f"Entrance: {sess.person_key} {direction}")

    def process_zones(self, sess: PersonSession, current_time: float):
        zones = self.geometry.get("zones", {})
        if not zones:
            return

        current_zones = set()
        for zone_id, polygon in zones.items():
            if point_near_polygon(sess.centroid, polygon, tolerance=5):
                current_zones.add(zone_id)

        new_zones = current_zones - sess.current_zones
        for zone_id in new_zones:
            sess.zone_enter_ts[zone_id] = current_time
            event = {
                "type": "zone",
                "ts": datetime.utcnow().isoformat() + "Z",
                "person_key": sess.person_key,
                "payload": {"zone_id": zone_id, "state": "enter"}
            }
            self.event_batch.append(event)

        left_zones = sess.current_zones - current_zones
        for zone_id in left_zones:
            if zone_id in sess.zone_enter_ts:
                enter_ts = sess.zone_enter_ts[zone_id]
                dwell_sec = current_time - enter_ts
                if dwell_sec >= 4.0:
                    event = {
                        "type": "zone",
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "person_key": sess.person_key,
                        "payload": {"zone_id": zone_id, "state": "exit", "dwell_sec": round(dwell_sec, 2)}
                    }
                    self.event_batch.append(event)
                del sess.zone_enter_ts[zone_id]

        sess.current_zones = current_zones

    def process_shelves(self, sess: PersonSession, current_time: float):
        shelves = self.geometry.get("shelves", {})
        if not shelves:
            return

        current_shelves = set()
        for shelf_id, polygon in shelves.items():
            if point_near_polygon(sess.centroid, polygon, tolerance=5):
                current_shelves.add(shelf_id)

        new_shelves = current_shelves - sess.current_shelves
        for shelf_id in new_shelves:
            sess.shelf_enter_ts[shelf_id] = current_time

        left_shelves = sess.current_shelves - current_shelves
        for shelf_id in left_shelves:
            if shelf_id in sess.shelf_enter_ts:
                enter_ts = sess.shelf_enter_ts[shelf_id]
                dwell_sec = current_time - enter_ts
                if dwell_sec >= 4.0:
                    event = {
                        "type": "shelf",
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "person_key": sess.person_key,
                        "payload": {"shelf_id": shelf_id, "state": "dwell", "dwell_sec": round(dwell_sec, 2)}
                    }
                    self.event_batch.append(event)
                del sess.shelf_enter_ts[shelf_id]

        sess.current_shelves = current_shelves

    def process_queue(self, sess: PersonSession, current_time: float):
        queue_polygons = self.geometry.get("queue", {})
        if not queue_polygons:
            return

        for queue_id, polygon in queue_polygons.items():
            in_queue = point_near_polygon(sess.centroid, polygon, tolerance=5)

            if in_queue and not sess.in_queue:
                sess.in_queue = True
                sess.queue_enter_ts = current_time
                event = {
                    "type": "queue",
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "person_key": sess.person_key,
                    "payload": {"queue_id": queue_id, "state": "enter"}
                }
                self.event_batch.append(event)

            elif not in_queue and sess.in_queue:
                if sess.queue_enter_ts:
                    dwell_sec = current_time - sess.queue_enter_ts
                    event = {
                        "type": "queue",
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "person_key": sess.person_key,
                        "payload": {"queue_id": queue_id, "state": "leave", "dwell_sec": round(dwell_sec, 2)}
                    }
                    self.event_batch.append(event)
                sess.in_queue = False
                sess.queue_enter_ts = None

    def flush_events(self):
        if self.event_batch:
            self.client.send_events(self.event_batch)
            self.event_batch = []

    def cleanup_old_sessions(self, current_time: float, max_age: float):
        to_remove = [tid for tid, sess in self.sessions.items() if current_time - sess.last_seen > max_age]
        for tid in to_remove:
            del self.sessions[tid]
