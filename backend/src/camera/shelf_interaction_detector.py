"""
Enhanced shelf interaction detection using bbox overlap and duration thresholds.
Prevents overcounting by requiring meaningful interaction duration.
"""

import time
import math
import json
from typing import Dict, List, Tuple, Any, Optional
from ..database.db_manager import db
from ..core.store_scope import current_store_id

def calculate_bbox_polygon_overlap_ratio(bbox: Tuple[float, float, float, float],
                                        polygon: List[Tuple[float, float]]) -> float:
    """
    Calculate the overlap ratio between bounding box and polygon.
    Returns the percentage of bbox area that overlaps with the polygon.
    """
    x1, y1, x2, y2 = bbox
    bbox_area = (x2 - x1) * (y2 - y1)

    if bbox_area <= 0:
        return 0.0

    # Simple approximation: check how many bbox corner/edge points are inside polygon
    # For production, use proper polygon clipping algorithms like Sutherland-Hodgman

    # Sample points within bounding box
    sample_points = []
    steps = 5  # 5x5 grid sampling
    for i in range(steps):
        for j in range(steps):
            px = x1 + (x2 - x1) * i / (steps - 1)
            py = y1 + (y2 - y1) * j / (steps - 1)
            sample_points.append((px, py))

    # Count points inside polygon
    inside_count = 0
    for point in sample_points:
        if point_in_polygon(point[0], point[1], polygon):
            inside_count += 1

    overlap_ratio = inside_count / len(sample_points)
    return overlap_ratio

def point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    """Point-in-polygon test using ray casting algorithm."""
    if len(polygon) < 3:
        return False

    inside = False
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside

    return inside

def calculate_centroid_to_polygon_distance(centroid: Tuple[float, float],
                                         polygon: List[Tuple[float, float]]) -> float:
    """Calculate minimum distance from centroid to polygon edge."""
    if not polygon:
        return float('inf')

    cx, cy = centroid
    min_distance = float('inf')

    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]

        # Distance to line segment
        dist = distance_point_to_line_segment((cx, cy), p1, p2)
        min_distance = min(min_distance, dist)

    return min_distance

def distance_point_to_line_segment(point: Tuple[float, float],
                                 line_start: Tuple[float, float],
                                 line_end: Tuple[float, float]) -> float:
    """Calculate distance from point to line segment."""
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end

    # Line segment length squared
    segment_length_sq = (x2 - x1)**2 + (y2 - y1)**2

    if segment_length_sq == 0:
        # Line segment is a point
        return math.sqrt((px - x1)**2 + (py - y1)**2)

    # Parameter t represents position along line segment
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / segment_length_sq))

    # Closest point on line segment
    closest_x = x1 + t * (x2 - x1)
    closest_y = y1 + t * (y2 - y1)

    # Distance from point to closest point on segment
    return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

class EnhancedShelfInteractionDetector:
    """
    Advanced shelf interaction detection with proper overlap calculation
    and duration thresholds to prevent overcounting.
    """

    def __init__(self, camera_id: int):
        self.camera_id = camera_id

        # Configuration thresholds
        self.bbox_overlap_threshold = 0.15      # 15% bbox overlap required
        self.proximity_threshold = 50           # 50 pixels proximity threshold
        self.min_interaction_duration = 2.0    # 2 seconds minimum interaction
        self.max_interaction_gap = 1.0         # 1 second gap allowed in interaction

        # Tracking active interactions
        self.active_interactions = {}           # track_id -> interaction_data
        self.completed_interactions = []        # List of completed interactions per hour

    def detect_shelf_interaction(self, track_id: int, bbox: Tuple[float, float, float, float],
                               centroid: Tuple[float, float], shelf_zones: List[Dict],
                               timestamp: float) -> bool:
        """
        Detect if person is interacting with shelf using bbox overlap + proximity.

        Args:
            track_id: Person track ID
            bbox: Bounding box (x1, y1, x2, y2)
            centroid: Person centroid (cx, cy)
            shelf_zones: List of shelf zone polygons with metadata
            timestamp: Current timestamp

        Returns:
            bool: True if interaction is detected
        """
        interaction_detected = False
        interacting_shelf = None

        for shelf_zone in shelf_zones:
            if shelf_zone.get("ztype") != "shelf":
                continue

            shelf_polygon = shelf_zone.get("poly", [])
            shelf_name = shelf_zone.get("name", "unknown_shelf")

            # Method 1: Check bbox overlap with shelf polygon
            overlap_ratio = calculate_bbox_polygon_overlap_ratio(bbox, shelf_polygon)

            # Method 2: Check centroid proximity to shelf
            distance_to_shelf = calculate_centroid_to_polygon_distance(centroid, shelf_polygon)

            # Interaction criteria: Either significant bbox overlap OR close proximity
            if overlap_ratio >= self.bbox_overlap_threshold or distance_to_shelf <= self.proximity_threshold:
                interaction_detected = True
                interacting_shelf = shelf_zone
                break

        # Update interaction tracking
        self._update_interaction_state(track_id, interaction_detected, interacting_shelf, timestamp)

        return interaction_detected

    def _update_interaction_state(self, track_id: int, is_interacting: bool,
                                shelf_zone: Optional[Dict], timestamp: float):
        """Update the interaction state for a person track."""

        if is_interacting and shelf_zone:
            # Starting or continuing interaction
            if track_id not in self.active_interactions:
                # New interaction started
                self.active_interactions[track_id] = {
                    'shelf_name': shelf_zone['name'],
                    'shelf_type': shelf_zone.get('ztype', 'shelf'),
                    'start_time': timestamp,
                    'last_seen': timestamp,
                    'total_duration': 0.0,
                    'gap_start': None
                }
            else:
                # Continuing interaction
                interaction = self.active_interactions[track_id]

                # Check if same shelf
                if interaction['shelf_name'] == shelf_zone['name']:
                    # Same shelf, update timing
                    if interaction['gap_start'] is not None:
                        # Was in a gap, now resumed
                        gap_duration = timestamp - interaction['gap_start']
                        if gap_duration <= self.max_interaction_gap:
                            # Gap was short enough, continue same interaction
                            interaction['gap_start'] = None
                        else:
                            # Gap too long, end previous and start new
                            self._finalize_interaction(track_id, interaction['gap_start'])
                            self.active_interactions[track_id] = {
                                'shelf_name': shelf_zone['name'],
                                'shelf_type': shelf_zone.get('ztype', 'shelf'),
                                'start_time': timestamp,
                                'last_seen': timestamp,
                                'total_duration': 0.0,
                                'gap_start': None
                            }
                    else:
                        # Continuous interaction
                        interaction['last_seen'] = timestamp
                        interaction['total_duration'] = timestamp - interaction['start_time']
                else:
                    # Different shelf, end previous and start new
                    self._finalize_interaction(track_id, timestamp)
                    self.active_interactions[track_id] = {
                        'shelf_name': shelf_zone['name'],
                        'shelf_type': shelf_zone.get('ztype', 'shelf'),
                        'start_time': timestamp,
                        'last_seen': timestamp,
                        'total_duration': 0.0,
                        'gap_start': None
                    }

        else:
            # Not interacting anymore
            if track_id in self.active_interactions:
                interaction = self.active_interactions[track_id]
                if interaction['gap_start'] is None:
                    # Start gap timer
                    interaction['gap_start'] = timestamp
                else:
                    # Continue gap
                    gap_duration = timestamp - interaction['gap_start']
                    if gap_duration > self.max_interaction_gap:
                        # Gap too long, finalize interaction
                        self._finalize_interaction(track_id, interaction['gap_start'])

    def _finalize_interaction(self, track_id: int, end_time: float):
        """Finalize and log a completed interaction."""
        if track_id not in self.active_interactions:
            return

        interaction = self.active_interactions[track_id]
        total_duration = end_time - interaction['start_time']

        # Only log interactions that meet minimum duration
        if total_duration >= self.min_interaction_duration:
            completed_interaction = {
                'track_id': track_id,
                'shelf_name': interaction['shelf_name'],
                'shelf_type': interaction['shelf_type'],
                'start_time': interaction['start_time'],
                'end_time': end_time,
                'duration': total_duration,
                'timestamp': time.time()
            }

            self.completed_interactions.append(completed_interaction)
            self._log_interaction_to_database(completed_interaction)

        # Remove from active interactions
        del self.active_interactions[track_id]

    def _log_interaction_to_database(self, interaction: Dict):
        """Log meaningful interaction to database."""
        try:
            store_id = current_store_id()

            with db.transaction() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO shelf_interactions
                    (store_id, camera_id, track_id, shelf_name, shelf_type,
                     start_time, end_time, duration, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    store_id, self.camera_id, interaction['track_id'],
                    interaction['shelf_name'], interaction['shelf_type'],
                    interaction['start_time'], interaction['end_time'],
                    interaction['duration'], interaction['timestamp']
                ))
                conn.commit()

        except Exception as e:
            print(f"Failed to log shelf interaction: {e}")

    def cleanup_expired_interactions(self, current_time: float):
        """Clean up interactions for tracks that have disappeared."""
        expired_tracks = []

        for track_id, interaction in self.active_interactions.items():
            time_since_last_seen = current_time - interaction['last_seen']
            if time_since_last_seen > 30:  # 30 second timeout
                expired_tracks.append(track_id)

        for track_id in expired_tracks:
            self._finalize_interaction(track_id, current_time)

    def get_hourly_interaction_count(self) -> int:
        """Get count of completed interactions in current hour."""
        return len(self.completed_interactions)

    def reset_hourly_metrics(self):
        """Reset interaction counters for new hour."""
        self.completed_interactions = []

# Global interaction detector instances
interaction_detectors = {}  # camera_id -> detector

def get_interaction_detector(camera_id: int) -> EnhancedShelfInteractionDetector:
    """Get or create interaction detector for camera."""
    if camera_id not in interaction_detectors:
        interaction_detectors[camera_id] = EnhancedShelfInteractionDetector(camera_id)
    return interaction_detectors[camera_id]