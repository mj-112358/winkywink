"""
Geometry utilities for polygon scaling and point-in-polygon checks.
"""

from typing import List, Tuple
import numpy as np


def scale_polygons(
    polygons: dict,
    screenshot_size: Tuple[int, int],
    frame_size: Tuple[int, int]
) -> dict:
    """
    Scale polygons from screenshot coordinates to actual frame coordinates.

    Args:
        polygons: Dict of polygon definitions (zones, shelves, entrance_line, queue)
        screenshot_size: (width, height) of reference screenshot
        frame_size: (width, height) of actual video frame

    Returns:
        Scaled polygons dict
    """
    screenshot_w, screenshot_h = screenshot_size
    frame_w, frame_h = frame_size

    scale_x = frame_w / screenshot_w
    scale_y = frame_h / screenshot_h

    scaled = {}

    # Scale zones
    if "zones" in polygons:
        scaled["zones"] = {}
        for zone_id, polygon in polygons["zones"].items():
            scaled["zones"][zone_id] = [
                (int(x * scale_x), int(y * scale_y))
                for x, y in polygon
            ]

    # Scale shelves
    if "shelves" in polygons:
        scaled["shelves"] = {}
        for shelf_id, polygon in polygons["shelves"].items():
            scaled["shelves"][shelf_id] = [
                (int(x * scale_x), int(y * scale_y))
                for x, y in polygon
            ]

    # Scale queue
    if "queue" in polygons and polygons["queue"]:
        scaled["queue"] = [
            (int(x * scale_x), int(y * scale_y))
            for x, y in polygons["queue"]
        ]

    # Scale entrance line
    if "entrance_line" in polygons and polygons["entrance_line"]:
        scaled["entrance_line"] = [
            (int(x * scale_x), int(y * scale_y))
            for x, y in polygons["entrance_line"]
        ]

    return scaled


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[int, int]]) -> bool:
    """
    Ray casting algorithm to check if point is inside polygon.

    Args:
        point: (x, y) coordinates
        polygon: List of (x, y) vertices

    Returns:
        True if point is inside polygon
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


def line_intersection(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float]
) -> bool:
    """
    Check if line segment p1-p2 intersects with line segment p3-p4.

    Args:
        p1, p2: First line segment endpoints
        p3, p4: Second line segment endpoints

    Returns:
        True if lines intersect
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if abs(denom) < 1e-10:
        return False

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    return 0 <= t <= 1 and 0 <= u <= 1


def get_centroid(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """
    Calculate centroid (knee-height point) for a bounding box.

    Args:
        bbox: (x1, y1, x2, y2) bounding box

    Returns:
        (x, y) centroid at knee height
    """
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    # Knee height = 3/4 down from top
    cy = y2 - (y2 - y1) / 4
    return (cx, cy)
