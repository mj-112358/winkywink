"""
Geometry utilities for polygon scaling and coordinate transformations.
Handles conversion from screenshot coordinates to RTSP frame coordinates.
"""

from typing import List, Tuple, Dict, Any
import math


def scale_point(point: Tuple[float, float], from_size: Tuple[int, int], to_size: Tuple[int, int]) -> Tuple[int, int]:
    """
    Scale a single point from one coordinate system to another.

    Args:
        point: (x, y) coordinates in source system
        from_size: (width, height) of source coordinate system
        to_size: (width, height) of target coordinate system

    Returns:
        Scaled (x, y) coordinates as integers
    """
    x, y = point
    from_w, from_h = from_size
    to_w, to_h = to_size

    # Calculate scaling factors
    scale_x = to_w / from_w
    scale_y = to_h / from_h

    # Scale and clamp to bounds
    new_x = int(x * scale_x)
    new_y = int(y * scale_y)

    # Clamp to valid bounds
    new_x = max(0, min(new_x, to_w - 1))
    new_y = max(0, min(new_y, to_h - 1))

    return (new_x, new_y)


def scale_polygon(polygon: List[List[float]], from_size: Tuple[int, int], to_size: Tuple[int, int]) -> List[List[int]]:
    """
    Scale a polygon (list of points) from one coordinate system to another.

    Args:
        polygon: List of [x, y] coordinates in source system
        from_size: (width, height) of source coordinate system
        to_size: (width, height) of target coordinate system

    Returns:
        List of [x, y] coordinates scaled to target system
    """
    scaled_points = []
    for point in polygon:
        if len(point) >= 2:
            x, y = point[0], point[1]
            scaled_x, scaled_y = scale_point((x, y), from_size, to_size)
            scaled_points.append([scaled_x, scaled_y])

    return scaled_points


def scale_line(line: List[List[float]], from_size: Tuple[int, int], to_size: Tuple[int, int]) -> List[List[int]]:
    """
    Scale a line (two points) from one coordinate system to another.

    Args:
        line: List of two [x, y] coordinates
        from_size: (width, height) of source coordinate system
        to_size: (width, height) of target coordinate system

    Returns:
        List of two [x, y] coordinates scaled to target system
    """
    if len(line) < 2:
        return line

    return scale_polygon(line[:2], from_size, to_size)


def scale_polygons(
    camera_config: Dict[str, Any],
    screenshot_size: Tuple[int, int],
    frame_size: Tuple[int, int]
) -> Dict[str, Any]:
    """
    Scale all polygons in a camera configuration from screenshot to frame coordinates.

    Args:
        camera_config: Camera configuration dict with geometry definitions
        screenshot_size: (width, height) of screenshot used to draw polygons
        frame_size: (width, height) of actual RTSP frame

    Returns:
        Dict with scaled geometry (zones, shelves, queue, entrance)
    """
    geometry = camera_config.get("geometry", {})
    scaled_geometry = {}

    # Scale zones (dict of zone_id -> polygon)
    if "zones" in geometry:
        scaled_geometry["zones"] = {}
        for zone_id, polygon in geometry["zones"].items():
            scaled_geometry["zones"][zone_id] = scale_polygon(polygon, screenshot_size, frame_size)

    # Scale shelves (dict of shelf_id -> polygon)
    if "shelves" in geometry:
        scaled_geometry["shelves"] = {}
        for shelf_id, polygon in geometry["shelves"].items():
            scaled_geometry["shelves"][shelf_id] = scale_polygon(polygon, screenshot_size, frame_size)

    # Scale queue areas (dict of queue_id -> polygon)
    if "queue" in geometry:
        scaled_geometry["queue"] = {}
        for queue_id, polygon in geometry["queue"].items():
            scaled_geometry["queue"][queue_id] = scale_polygon(polygon, screenshot_size, frame_size)

    # Scale entrance line (list of two points)
    if "entrance" in geometry:
        entrance = geometry["entrance"]
        if isinstance(entrance, list) and len(entrance) >= 2:
            scaled_geometry["entrance"] = scale_line(entrance, screenshot_size, frame_size)

    return scaled_geometry


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.

    Args:
        point: (x, y) coordinates to test
        polygon: List of [x, y] coordinates defining the polygon

    Returns:
        True if point is inside polygon, False otherwise
    """
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


def point_distance_to_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> float:
    """
    Calculate minimum distance from point to polygon edge.

    Args:
        point: (x, y) coordinates
        polygon: List of [x, y] coordinates defining the polygon

    Returns:
        Minimum distance to polygon edge in pixels
    """
    px, py = point
    min_dist = float('inf')

    n = len(polygon)
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]

        # Distance from point to line segment
        dist = point_to_segment_distance(point, (p1[0], p1[1]), (p2[0], p2[1]))
        min_dist = min(min_dist, dist)

    return min_dist


def point_to_segment_distance(point: Tuple[float, float], seg_start: Tuple[float, float], seg_end: Tuple[float, float]) -> float:
    """
    Calculate distance from point to line segment.

    Args:
        point: (x, y) coordinates of point
        seg_start: (x, y) coordinates of segment start
        seg_end: (x, y) coordinates of segment end

    Returns:
        Distance in pixels
    """
    px, py = point
    x1, y1 = seg_start
    x2, y2 = seg_end

    # Vector from start to end
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        # Segment is a point
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    # Parameter t of closest point on line
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

    # Closest point on segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    # Distance to closest point
    return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)


def get_polygon_centroid(polygon: List[List[float]]) -> Tuple[float, float]:
    """
    Calculate centroid of a polygon.

    Args:
        polygon: List of [x, y] coordinates

    Returns:
        (x, y) centroid coordinates
    """
    if not polygon:
        return (0, 0)

    x_sum = sum(p[0] for p in polygon)
    y_sum = sum(p[1] for p in polygon)
    n = len(polygon)

    return (x_sum / n, y_sum / n)


def get_polygon_bbox(polygon: List[List[float]]) -> Tuple[int, int, int, int]:
    """
    Get bounding box of a polygon.

    Args:
        polygon: List of [x, y] coordinates

    Returns:
        (x_min, y_min, x_max, y_max) bounding box
    """
    if not polygon:
        return (0, 0, 0, 0)

    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]

    return (
        int(min(x_coords)),
        int(min(y_coords)),
        int(max(x_coords)),
        int(max(y_coords))
    )
