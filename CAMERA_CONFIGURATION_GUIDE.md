# Camera Configuration Guide

This guide explains how to configure cameras and detection zones in the Wink retail analytics system.

## Overview

The Wink system supports **up to 3 cameras per store**, each with customizable features and detection zones. Store managers can configure cameras through the web interface or locally on edge devices.

## Features

### Available Camera Capabilities

1. **Footfall Tracking** - Count people entering/exiting through line zones
2. **Queue Detection** - Monitor queue length and wait times
3. **Shelf Interaction** - Track customer interactions with products
4. **Dwell Time** - Measure time customers spend in specific areas
5. **Heat Mapping** - Visualize customer movement patterns

### Zone Types

#### Line Zones
- **Purpose**: Footfall counting, entrance/exit tracking
- **Configuration**: Define with 2 points (start and end)
- **Direction**: Specify "in" or "out" for entry/exit
- **Example Use Cases**:
  - Store entrance/exit counting
  - Department boundary crossing
  - Aisle traffic measurement

#### Polygon Zones
- **Purpose**: Area-based analytics (dwell, shelf interaction, heatmap)
- **Configuration**: Define with 3+ points forming a closed polygon
- **Properties**: Can assign shelf category or area name
- **Example Use Cases**:
  - Product shelf monitoring
  - Queue area detection
  - High-interest zone tracking

## Web-Based Configuration

### Accessing Camera Setup

1. Log in to the Wink dashboard at `http://localhost:5173` (or your deployed URL)
2. Click **"Camera Setup"** in the sidebar navigation
3. You'll see existing cameras and an "Add Camera" button (if under 3 cameras)

### Adding a New Camera

1. Click **"Add Camera"** button
2. Fill in the camera details:
   - **Camera Name**: Descriptive name (e.g., "Main Entrance", "Aisle 3")
   - **RTSP URL**: Camera stream URL (format: `rtsp://IP:PORT/stream`)
   - **Is Entrance Camera**: Check if this is an entrance camera
   - **Features**: Select which analytics to enable

3. **Select Features**: Choose from available capabilities:
   ```
   ☐ Footfall Tracking - Count people entering/exiting
   ☐ Queue Detection - Monitor queue length and wait times
   ☐ Shelf Interaction - Track product interactions
   ☐ Dwell Time - Measure time spent in areas
   ☐ Heat Mapping - Visualize customer movement
   ```

4. **Configure Zones**:

   **For Line Zones (Footfall)**:
   - Click "Add Line Zone"
   - Enter zone name (e.g., "Entrance In")
   - Specify direction ("in" or "out")
   - Click 2 points on the canvas to draw the line
   - Zone automatically saves after 2 points

   **For Polygon Zones (Shelf/Queue/Dwell)**:
   - Click "Add Polygon Zone"
   - Enter zone name (e.g., "Snacks Shelf")
   - Optionally enter shelf category
   - Click multiple points on canvas to outline the area
   - Click "Finish Polygon" when done (minimum 3 points)

5. Click **"Create Camera"** to save

### Editing an Existing Camera

1. Find the camera in the list
2. Click the **Edit** icon (pencil)
3. Modify any fields:
   - Change camera name
   - Update RTSP URL
   - Add/remove features
   - Add/remove/modify zones
4. Click **"Update Camera"** to save changes

### Deleting a Camera

1. Find the camera in the list
2. Click the **Delete** icon (trash)
3. Confirm deletion
4. All associated zones and historical data will be preserved but camera will stop processing

## Edge Device Configuration (Alternative Method)

For advanced users or edge deployments without web access, cameras can be configured locally via YAML files.

### Configuration File Location

```
edge/config.yaml
```

### Example Configuration

```yaml
api_url: "https://api.winkai.in"  # Your API endpoint
edge_key: "edge_7821e931_secret_key"  # Your edge device key

cameras:
  - camera_id: "cam_entrance_001"
    name: "Main Entrance Camera"
    rtsp_url: "rtsp://192.168.1.101:554/stream"
    capabilities: ["footfall", "queue"]
    zones:
      # Line zone for entrance counting
      - zone_id: "zone_entrance_in"
        type: "line"
        name: "Entrance Line In"
        coordinates: [[100, 200], [500, 200]]
        direction: "in"

      - zone_id: "zone_entrance_out"
        type: "line"
        name: "Entrance Line Out"
        coordinates: [[100, 250], [500, 250]]
        direction: "out"

  - camera_id: "cam_aisle_001"
    name: "Aisle 1 Camera"
    rtsp_url: "rtsp://192.168.1.102:554/stream"
    capabilities: ["shelf_interaction", "dwell", "heatmap"]
    zones:
      # Polygon zone for shelf monitoring
      - zone_id: "zone_shelf_snacks"
        type: "polygon"
        name: "Snacks Shelf"
        coordinates: [[150, 100], [400, 100], [400, 300], [150, 300]]
        shelf_category: "snacks"

      - zone_id: "zone_shelf_beverages"
        type: "polygon"
        name: "Beverages Shelf"
        coordinates: [[450, 100], [700, 100], [700, 300], [450, 300]]
        shelf_category: "beverages"

  - camera_id: "cam_checkout_001"
    name: "Checkout Area Camera"
    rtsp_url: "rtsp://192.168.1.103:554/stream"
    capabilities: ["queue", "dwell"]
    zones:
      - zone_id: "zone_checkout_queue"
        type: "polygon"
        name: "Checkout Queue Area"
        coordinates: [[200, 200], [600, 200], [600, 500], [200, 500]]
```

### Coordinate System

- **Origin**: Top-left corner of the camera frame (0, 0)
- **X-axis**: Increases from left to right
- **Y-axis**: Increases from top to bottom
- **Units**: Pixels in the video frame
- **Frame Size**: Typically 1920x1080 (Full HD) or 1280x720 (HD)

### Finding Coordinates

1. **Using VLC or similar player**:
   - Open the RTSP stream in VLC
   - Pause at a frame
   - Take a screenshot
   - Use an image editor with pixel coordinates display
   - Note the coordinates of your desired zone boundaries

2. **Using the Web Interface** (Recommended):
   - The canvas in Camera Setup automatically captures coordinates
   - Click points on the preview to define zones visually
   - Coordinates are automatically calculated

## API Endpoints

For programmatic access, the following REST API endpoints are available:

### List Cameras
```http
GET /api/cameras/
Authorization: Bearer <JWT_TOKEN>
```

### Get Camera
```http
GET /api/cameras/{camera_id}
Authorization: Bearer <JWT_TOKEN>
```

### Create Camera
```http
POST /api/cameras/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "name": "Camera Name",
  "rtsp_url": "rtsp://192.168.1.100:554/stream",
  "is_entrance": false,
  "capabilities": ["footfall", "queue"],
  "zones": [
    {
      "zone_id": "zone_1",
      "name": "Zone Name",
      "type": "line",
      "coordinates": [[100, 200], [500, 200]],
      "direction": "in"
    }
  ]
}
```

### Update Camera
```http
PUT /api/cameras/{camera_id}
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "name": "Updated Name",
  "zones": [...]
}
```

### Delete Camera
```http
DELETE /api/cameras/{camera_id}
Authorization: Bearer <JWT_TOKEN>
```

## Best Practices

### Camera Placement

1. **Entrance Cameras**:
   - Mount overhead at 2.5-3m height
   - Angle downward at 30-45 degrees
   - Ensure line zones perpendicular to traffic flow
   - Avoid backlighting from windows/doors

2. **Shelf Cameras**:
   - Position to capture full shelf width
   - Minimize occlusions (pillars, hanging signs)
   - Cover high-value or promotional products
   - Consider lighting conditions

3. **Queue Cameras**:
   - Wide-angle view of entire queue area
   - Include checkout counter in frame
   - Ensure good overhead lighting

### Zone Configuration

1. **Line Zones**:
   - Draw perpendicular to expected movement
   - Place away from edges where people might exit/enter frame
   - Use pairs (in/out) for accurate net counts
   - Avoid areas with complex traffic patterns

2. **Polygon Zones**:
   - Keep zones simple (4-6 points typically sufficient)
   - Avoid overlapping zones for clarity
   - Match physical shelf/display boundaries
   - Account for customer reach distance from shelf

### Naming Conventions

- Use descriptive, hierarchical names:
  - `Main_Entrance_In`
  - `Aisle3_SnacksShelf`
  - `Checkout_Queue1`
- Avoid special characters except underscores
- Include location and purpose in name

## Troubleshooting

### Camera Not Appearing

1. Check RTSP URL is correct and accessible
2. Verify network connectivity between edge device and camera
3. Ensure camera credentials are included in RTSP URL if required
4. Check camera limit (max 3 per store)

### Inaccurate Detection

1. **Line zones not detecting crossings**:
   - Verify line is perpendicular to movement
   - Check camera angle isn't too steep
   - Ensure adequate lighting
   - Verify zone coordinates are within frame boundaries

2. **Polygon zones missing interactions**:
   - Confirm zone covers intended area
   - Check for occlusions blocking view
   - Verify camera resolution is adequate (720p minimum)
   - Review zone coordinates for errors

### Performance Issues

1. Reduce number of zones per camera
2. Disable unused capabilities
3. Lower camera resolution if bandwidth-limited
4. Ensure edge device meets minimum specs (see DEPLOYMENT.md)

## System Limits

- **Maximum cameras per store**: 3
- **Maximum zones per camera**: 10 (recommended)
- **Supported video formats**: H.264, H.265
- **Minimum resolution**: 1280x720 (720p)
- **Recommended resolution**: 1920x1080 (1080p)
- **Frame rate**: 15-30 FPS

## Support

For additional help:
- Review `DEPLOYMENT.md` for edge device setup
- Check `COMPLETE_SYSTEM_GUIDE.md` for full system architecture
- Review logs in `edge/logs/` for edge device issues
- Check backend logs for API errors

## Example Workflows

### Setting Up a New Store

1. Install edge device at store location
2. Connect cameras to local network
3. Log in to web dashboard
4. Add first camera (entrance)
   - Select "Footfall Tracking" capability
   - Draw entrance line zones (in/out)
5. Add second camera (main aisle)
   - Select "Shelf Interaction" + "Dwell Time"
   - Draw polygon zones around key shelves
6. Add third camera (checkout)
   - Select "Queue Detection"
   - Draw polygon zone around queue area
7. Verify cameras are active in Live view
8. Monitor Dashboard for incoming data

### Updating Zone Configuration

1. Navigate to Camera Setup
2. Click Edit on target camera
3. Remove old zones (trash icon)
4. Add new zones using canvas
5. Click Update Camera
6. Edge device automatically syncs new configuration
7. New zone data appears within 1-2 minutes

### Troubleshooting Low Footfall Counts

1. Review Live view - are people being detected?
2. Check Camera Setup - verify line zone coordinates
3. Ensure line is perpendicular to movement
4. Verify camera view isn't obstructed
5. Check lighting conditions (minimum 300 lux recommended)
6. Review edge device logs for detection errors
