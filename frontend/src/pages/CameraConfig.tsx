import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Camera as CameraIcon, Plus, Edit, Trash2, Save, X } from 'lucide-react';
import Card from '../components/ui/Card';
import { config } from '../config';

interface Zone {
  zone_id: string;
  name: string;
  type: 'line' | 'polygon';
  coordinates: number[][];
  direction?: string;
  shelf_category?: string;
}

interface Camera {
  camera_id: string;
  store_id: string;
  name: string;
  is_entrance: boolean;
  rtsp_url: string | null;
  capabilities: string[];
  zones: Zone[];
  is_active: boolean;
}

interface CameraFormData {
  name: string;
  rtsp_url: string;
  is_entrance: boolean;
  capabilities: string[];
  zones: Zone[];
}

const AVAILABLE_FEATURES = [
  { id: 'footfall', label: 'Footfall Tracking', description: 'Count people entering/exiting' },
  { id: 'queue', label: 'Queue Detection', description: 'Monitor queue length and wait times' },
  { id: 'shelf_interaction', label: 'Shelf Interaction', description: 'Track product interactions' },
  { id: 'dwell', label: 'Dwell Time', description: 'Measure time spent in areas' },
  { id: 'heatmap', label: 'Heat Mapping', description: 'Visualize customer movement' },
];

const CameraConfig: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [formData, setFormData] = useState<CameraFormData>({
    name: '',
    rtsp_url: '',
    is_entrance: false,
    capabilities: [],
    zones: []
  });
  const [currentZone, setCurrentZone] = useState<Partial<Zone> | null>(null);
  const [drawingMode, setDrawingMode] = useState<'line' | 'polygon' | null>(null);
  const [points, setPoints] = useState<number[][]>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${config.apiBaseUrl}/api/cameras/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setCameras(data);
    } catch (error) {
      console.error('Error loading cameras:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const token = localStorage.getItem('auth_token');
      const url = editingCamera
        ? `${config.apiBaseUrl}/api/cameras/${editingCamera.camera_id}`
        : `${config.apiBaseUrl}/api/cameras/`;

      const method = editingCamera ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        await loadCameras();
        setShowForm(false);
        setEditingCamera(null);
        resetForm();
      } else {
        const error = await res.json();
        alert(error.detail || 'Failed to save camera');
      }
    } catch (error) {
      console.error('Error saving camera:', error);
      alert('Failed to save camera');
    }
  };

  const handleDelete = async (cameraId: string) => {
    if (!confirm('Are you sure you want to delete this camera?')) return;

    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${config.apiBaseUrl}/api/cameras/${cameraId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        await loadCameras();
      }
    } catch (error) {
      console.error('Error deleting camera:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      rtsp_url: '',
      is_entrance: false,
      capabilities: [],
      zones: []
    });
    setPoints([]);
    setDrawingMode(null);
    setCurrentZone(null);
  };

  const handleEdit = (camera: Camera) => {
    setEditingCamera(camera);
    setFormData({
      name: camera.name,
      rtsp_url: camera.rtsp_url || '',
      is_entrance: camera.is_entrance,
      capabilities: camera.capabilities || [],
      zones: camera.zones || []
    });
    setShowForm(true);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!drawingMode) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);

    const newPoints = [...points, [x, y]];
    setPoints(newPoints);

    // Draw point
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = drawingMode === 'line' ? 'blue' : 'green';
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, 2 * Math.PI);
      ctx.fill();

      // Draw lines between points
      if (newPoints.length > 1) {
        ctx.strokeStyle = drawingMode === 'line' ? 'blue' : 'green';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(newPoints[0][0], newPoints[0][1]);
        for (let i = 1; i < newPoints.length; i++) {
          ctx.lineTo(newPoints[i][0], newPoints[i][1]);
        }
        ctx.stroke();
      }
    }

    // Auto-complete for line zones (2 points)
    if (drawingMode === 'line' && newPoints.length === 2) {
      finishZone(newPoints);
    }
  };

  const finishZone = (finalPoints: number[][]) => {
    if (!currentZone || !currentZone.name) {
      alert('Please provide a zone name first');
      return;
    }

    const zone: Zone = {
      zone_id: `zone_${Date.now()}`,
      name: currentZone.name,
      type: drawingMode!,
      coordinates: finalPoints,
      direction: currentZone.direction,
      shelf_category: currentZone.shelf_category
    };

    setFormData({
      ...formData,
      zones: [...formData.zones, zone]
    });

    // Reset drawing
    setPoints([]);
    setDrawingMode(null);
    setCurrentZone(null);

    // Clear canvas
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
  };

  const startDrawing = (type: 'line' | 'polygon') => {
    const zoneName = prompt(`Enter ${type} zone name:`);
    if (!zoneName) return;

    const zone: Partial<Zone> = {
      name: zoneName,
      type
    };

    if (type === 'line') {
      const direction = prompt('Enter direction (in/out):');
      zone.direction = direction || 'in';
    } else {
      const category = prompt('Enter shelf category (optional):');
      zone.shelf_category = category || undefined;
    }

    setCurrentZone(zone);
    setDrawingMode(type);
    setPoints([]);
  };

  const removeZone = (index: number) => {
    setFormData({
      ...formData,
      zones: formData.zones.filter((_, i) => i !== index)
    });
  };

  const toggleCapability = (capability: string) => {
    const capabilities = formData.capabilities.includes(capability)
      ? formData.capabilities.filter(c => c !== capability)
      : [...formData.capabilities, capability];

    setFormData({ ...formData, capabilities });
  };

  return (
    <div className="min-h-full bg-bg-subtle">
      <div className="gradient-header px-6 py-8">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold text-text mb-2">Camera Configuration</h1>
          <p className="text-muted">Manage cameras and detection zones (Max 3 cameras per store)</p>
        </motion.div>
      </div>

      <div className="px-6 pb-6 -mt-4">
        {!showForm ? (
          <Card
            title="Cameras"
            subtitle={`${cameras.length}/3 cameras configured`}
            action={
              cameras.length < 3 ? (
                <button
                  onClick={() => setShowForm(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4" />
                  Add Camera
                </button>
              ) : undefined
            }
          >
            {loading ? (
              <div className="p-8 text-center">Loading...</div>
            ) : cameras.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No cameras configured. Click "Add Camera" to get started.
              </div>
            ) : (
              <div className="space-y-4">
                {cameras.map((cam) => (
                  <div key={cam.camera_id} className="p-6 border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-4">
                          <CameraIcon className="h-8 w-8 text-blue-600" />
                          <div>
                            <h3 className="font-semibold text-lg">{cam.name}</h3>
                            <p className="text-sm text-gray-500">{cam.camera_id}</p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                          <div>
                            <span className="text-gray-600">RTSP URL:</span>
                            <p className="font-mono text-xs break-all">{cam.rtsp_url || 'Not set'}</p>
                          </div>
                          <div>
                            <span className="text-gray-600">Type:</span>
                            <p>{cam.is_entrance ? 'Entrance Camera' : 'Interior Camera'}</p>
                          </div>
                          <div>
                            <span className="text-gray-600">Status:</span>
                            <p className={cam.is_active ? 'text-green-600' : 'text-gray-400'}>
                              {cam.is_active ? 'Active' : 'Inactive'}
                            </p>
                          </div>
                          <div>
                            <span className="text-gray-600">Zones:</span>
                            <p>{cam.zones.length} configured</p>
                          </div>
                        </div>

                        <div>
                          <span className="text-gray-600 text-sm">Capabilities:</span>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {cam.capabilities.map(cap => (
                              <span key={cap} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                                {cap}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(cam)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                        >
                          <Edit className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(cam.camera_id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        ) : (
          <Card
            title={editingCamera ? 'Edit Camera' : 'Add New Camera'}
            action={
              <button
                onClick={() => {
                  setShowForm(false);
                  setEditingCamera(null);
                  resetForm();
                }}
                className="p-2 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            }
          >
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Camera Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">RTSP URL *</label>
                  <input
                    type="text"
                    value={formData.rtsp_url}
                    onChange={(e) => setFormData({ ...formData, rtsp_url: e.target.value })}
                    placeholder="rtsp://192.168.1.100:554/stream"
                    className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_entrance}
                    onChange={(e) => setFormData({ ...formData, is_entrance: e.target.checked })}
                  />
                  <span className="text-sm font-medium">This is an entrance camera</span>
                </label>
              </div>

              {/* Features Selection */}
              <div>
                <label className="block text-sm font-medium mb-3">Select Features *</label>
                <div className="grid grid-cols-2 gap-3">
                  {AVAILABLE_FEATURES.map((feature) => (
                    <label
                      key={feature.id}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                        formData.capabilities.includes(feature.id)
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={formData.capabilities.includes(feature.id)}
                        onChange={() => toggleCapability(feature.id)}
                        className="mr-3"
                      />
                      <div className="inline-block">
                        <div className="font-medium">{feature.label}</div>
                        <div className="text-sm text-gray-600">{feature.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Zone Configuration */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium">Detection Zones</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => startDrawing('line')}
                      disabled={!!drawingMode}
                      className="px-3 py-1 bg-blue-600 text-white rounded text-sm disabled:bg-gray-300"
                    >
                      Add Line Zone
                    </button>
                    <button
                      type="button"
                      onClick={() => startDrawing('polygon')}
                      disabled={!!drawingMode}
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm disabled:bg-gray-300"
                    >
                      Add Polygon Zone
                    </button>
                  </div>
                </div>

                {/* Drawing Canvas */}
                <div className="border rounded-lg p-4 bg-gray-50 mb-4">
                  <canvas
                    ref={canvasRef}
                    width={800}
                    height={450}
                    onClick={handleCanvasClick}
                    className="border bg-white cursor-crosshair w-full"
                    style={{ maxWidth: '100%', height: 'auto' }}
                  />
                  {drawingMode && (
                    <div className="mt-2 text-sm text-gray-600">
                      {drawingMode === 'line'
                        ? `Click 2 points to draw a line. Points: ${points.length}/2`
                        : `Click to add points. Current: ${points.length} points`}
                      {drawingMode === 'polygon' && points.length >= 3 && (
                        <button
                          type="button"
                          onClick={() => finishZone(points)}
                          className="ml-4 px-3 py-1 bg-green-600 text-white rounded"
                        >
                          Finish Polygon
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Zone List */}
                {formData.zones.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm text-gray-600">{formData.zones.length} zones configured:</p>
                    {formData.zones.map((zone, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <div className="flex-1">
                          <span className="font-medium">{zone.name}</span>
                          <span className="ml-3 text-sm text-gray-600">
                            {zone.type} ({zone.coordinates.length} points)
                          </span>
                          {zone.direction && (
                            <span className="ml-2 text-sm text-blue-600">→ {zone.direction}</span>
                          )}
                          {zone.shelf_category && (
                            <span className="ml-2 text-sm text-green-600">📦 {zone.shelf_category}</span>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => removeZone(index)}
                          className="text-red-600 hover:bg-red-50 p-2 rounded"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Submit */}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setEditingCamera(null);
                    resetForm();
                  }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Save className="h-4 w-4" />
                  {editingCamera ? 'Update Camera' : 'Create Camera'}
                </button>
              </div>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
};

export default CameraConfig;
